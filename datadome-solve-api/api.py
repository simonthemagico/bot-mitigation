from typing import Optional
from fastapi import FastAPI, HTTPException, Request
import subprocess
import os
import asyncio
import json
import hashlib
import re
from pydantic import BaseModel
import time
from pyvirtualdisplay import Display
import shutil
import random
from glob import glob
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

PROFILE_DIR = os.getenv("PROFILE_DIR")
CHROME_PATH = os.getenv("CHROME_PATH")
EXTENSION_PATH = os.getenv("EXTENSION_PATH")
RESPONSES_PATH = os.getenv("RESPONSES_PATH")
PREFERENCES_PATH = os.getenv("PREFERENCES_PATH")
USE_DISPLAY = os.getenv("USE_DISPLAY", "false").lower() == "true"
API_PORT = int(os.getenv("API_PORT", 8000))

class CreateTaskRequest(BaseModel):
    captchaUrl: str
    host: str
    port: int
    username: Optional[str] = "user-sp0e9f6467-sessionduration-30"
    password: Optional[str] = "EWXv1a50bXfxc3vnsw"
    userAgent: Optional[str] = None

TIMEOUT_IN_MINUTES = 1
PROCESSING_URLS = set()
RESPONSES = {}
MAX_BROWSERS = 15  # Maximum number of browsers that can be opened at a time
semaphore = asyncio.Semaphore(MAX_BROWSERS)

class MockP(object):
    def terminate(self):
        print("Terminated")

def get_random_fingerprint():
    fingerprints_path = os.path.join(os.path.dirname(__file__), "fingerprints")
    fingerprints = glob(f"{fingerprints_path}/*.json")

    fingerprint = random.choice(fingerprints)
    fingerprint_path = os.path.join(fingerprints_path, fingerprint)

    with open(fingerprint_path, "r", encoding="utf-8") as f:
        fingerprint_data = json.load(f)
        user_agent = fingerprint_data["navigator"]["userAgent"]
        # randomize the user agent chrome version
        major = random.randint(110, 120)
        minor = random.randint(0, 9)
        build = random.randint(0, 600)
        patch = random.randint(0, 200)

        random_version = f"{major}.{minor}.{build}.{patch}"
        user_agent = re.sub(r"Chrome/[\d.]+", f"Chrome/{random_version}", user_agent)
        fingerprint_data["navigator"]["userAgent"] = user_agent
        return fingerprint_data

def write_preferences(profile_dir: str, start_url: str, fingerprint: dict, create_task_request: CreateTaskRequest):
    preferences_path = f"{profile_dir}/Default/Preferences"

    with open(os.path.join(os.path.dirname(__file__), PREFERENCES_PATH), "r", encoding="utf-8") as f:
        preferences = json.load(f)
        preferences["gologin"].update(fingerprint)
        preferences["gologin"]["startupUrl"] = start_url
        preferences["gologin"]["startup_urls"] = [start_url]

        preferences["gologin"]["proxy"]["username"] = create_task_request.username
        preferences["gologin"]["proxy"]["password"] = create_task_request.password

    # Write this in preferences_path
    with open(preferences_path, "w", encoding="utf-8") as f:
        json.dump(preferences, f)

def check_response_exists(hash_code: str):
    return RESPONSES.get(hash_code, False)

@app.post("/v1/createTask")
async def create_task(createTaskRequest: CreateTaskRequest):
    async with semaphore:
        # proxy host, port
        proxy_host = createTaskRequest.host
        proxy_port = createTaskRequest.port
        user_agent = createTaskRequest.userAgent

        captcha_url = createTaskRequest.captchaUrl
        # Convert the captcha URL using the hashCode function
        hash_code = sha256_hash(captcha_url)
        # Copy directory to a temp directory
        subprocess.run(["cp", "-r", PROFILE_DIR, f"/tmp/{hash_code}"])
        TEMP_PROFILE_DIR = f"/tmp/{hash_code}"

        # Get a random fingerprint json file from `fingerprints`
        fingerprint = get_random_fingerprint()
        if user_agent:
            fingerprint['navigator']['userAgent'] = user_agent


        # Write captcha url as start url
        write_preferences(TEMP_PROFILE_DIR, start_url=captcha_url, fingerprint=fingerprint, create_task_request=createTaskRequest)

        EXTENSION_PATH = "/Users/administrator/Downloads/Projects/xhr-response-saver"
        # Launch the browser with the provided command
        command = [
            CHROME_PATH,
            f"--user-data-dir={TEMP_PROFILE_DIR}",
            "--disable-encryption",
            "--donut-pie=undefined",
            "--font-masking-mode=2",
            f"--load-extension=/Users/administrator/.gologin/extensions/cookies-ext/655208c87e736c4718ccde8e,/Users/administrator/.gologin/extensions/passwords-ext/655208c87e736c4718ccde8e,{EXTENSION_PATH}",
            f"--proxy-server=http://{proxy_host}:{proxy_port}",
            f"--host-resolver-rules=MAP * 0.0.0.0 , EXCLUDE {proxy_host}",
            "--lang=en-US"
        ]
        async def process():
            if captcha_url not in PROCESSING_URLS:
                p = subprocess.Popen(command, start_new_session=True)
                PROCESSING_URLS.add(captcha_url)
            else:
                p = MockP()

            try:
                # Check time
                start_time = time.time()
                while check_response_exists(hash_code) is False:
                    print(f"Waiting: {hash_code}")
                    await asyncio.sleep(1)  # Check for file every second
                    # If process is not alive, raise stop
                    if p.poll() is not None:
                        print(f"Process not alive: {createTaskRequest.__dict__}")
                        raise HTTPException(status_code=408, detail="Stopped")
                    if time.time() - start_time > TIMEOUT_IN_MINUTES * 60:
                        print(f"Timeout: {createTaskRequest.__dict__}")
                        p.terminate()
                        raise HTTPException(status_code=408, detail="Timeout")

                print(f"Found: {hash_code}")

                # Read and return the JSON response
                response_data = RESPONSES[hash_code]

                # Close the browser
                p.terminate()

                response_data['navigator'] = fingerprint['navigator']

                return response_data
            finally:
                # Wait for 1 second to close the browser
                await asyncio.sleep(1)
                # Remove the temp directory
                shutil.rmtree(TEMP_PROFILE_DIR)
                # Remove the captcha url from the processing urls
                PROCESSING_URLS.remove(captcha_url)

        if USE_DISPLAY:
            with Display(visible=False):
                return await process()

        return await process()

# Post route to receive the response
@app.post("/v1/response")
async def response(request: Request):
    # Read the response, hash
    response_data = await request.json()
    # Convert the captcha URL using the hashCode function
    hash_code = response_data['hashedUrl']
    # Store the response in the RESPONSES dictionary
    RESPONSES[hash_code] = response_data
    # Return the response
    return response_data

def sha256_hash(s):
    return hashlib.sha256(s.encode()).hexdigest()

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
