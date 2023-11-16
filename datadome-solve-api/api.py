from fastapi import FastAPI, HTTPException, Request
import subprocess
import os
import asyncio
import json
import hashlib
import os
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

class CreateTaskRequest(BaseModel):
    captchaUrl: str
    host: str
    port: int

TIMEOUT_IN_MINUTES = 1
PROCESSING_URLS = set()
RESPONSES = {}

class MockP(object):
    def terminate(self):
        print("Terminated")

def get_random_fingerprint():
    fingerprints_path = os.path.join(os.path.dirname(__file__), "fingerprints")
    fingerprints = glob(f"{fingerprints_path}/*.json")

    fingerprint = random.choice(fingerprints)
    fingerprint_path = os.path.join(fingerprints_path, fingerprint)

    with open(fingerprint_path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_preferences(profile_dir: str, start_url: str, fingerprint: dict):
    preferences_path = f"{profile_dir}/Default/Preferences"

    with open(os.path.join(os.path.dirname(__file__), PREFERENCES_PATH), "r", encoding="utf-8") as f:
        preferences = json.load(f)
        preferences["gologin"].update(fingerprint)
        preferences["gologin"]["startupUrl"] = start_url
        preferences["gologin"]["startup_urls"] = [start_url]

        # Generate random noise
        # gologin/audioContext/noiseValue - 6.213282708857e-8 (random)
        # gologin/canvasNoise - 0-5
        # gologin/getClientRectsNoice - 5-10 (same)
        # gologin/get_client_rects_noise - 5-10 
        # gologin/webglNoiseValue - 80-90

        # preferences["gologin"]["audioContext"]["noiseValue"] = eval(f"{random.randint(0, 10 * 10000) / 10000}e-8")
        # preferences["gologin"]["canvasNoise"] = random.randint(0, 5 * 10000) / 10000
        # preferences["gologin"]["getClientRectsNoise"] = random.randint(5 * 10000, 10 * 10000) / 10000
        # preferences["gologin"]["get_client_rects_noise"] = preferences["gologin"]["getClientRectsNoise"]
        # preferences["gologin"]["webglNoiseValue"] = random.randint(80 * 10000, 90 * 10000) / 10000

    # Write this in preferences_path
    with open(preferences_path, "w", encoding="utf-8") as f:
        json.dump(preferences, f)

def check_response_exists(hash_code: str):
    return RESPONSES.get(hash_code, False)

@app.post("/v1/createTask")
async def create_task(createTaskRequest: CreateTaskRequest):
    # proxy host, port
    proxy_host = createTaskRequest.host
    proxy_port = createTaskRequest.port

    captcha_url = createTaskRequest.captchaUrl
    # Convert the captcha URL using the hashCode function
    hash_code = sha256_hash(captcha_url)
    # Copy directory to a temp directory
    subprocess.run(["cp", "-r", PROFILE_DIR, f"/tmp/{hash_code}"])
    TEMP_PROFILE_DIR = f"/tmp/{hash_code}"

    # Get a random fingerprint json file from `fingerprints`
    fingerprint = get_random_fingerprint()

    # Write captcha url as start url
    write_preferences(TEMP_PROFILE_DIR, start_url=captcha_url, fingerprint=fingerprint)
    
    # Launch the browser with the provided command
    command = [
        CHROME_PATH,
        f"--user-data-dir={TEMP_PROFILE_DIR}",
        "--disable-encryption",
        "--donut-pie=undefined",
        "--font-masking-mode=2",
        f"--load-extension={EXTENSION_PATH}",
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
    uvicorn.run(app, host="0.0.0.0", port=8018)