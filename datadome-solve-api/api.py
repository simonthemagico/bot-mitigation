from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Response
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

CHROME_PATH = os.getenv("CHROME_PATH")
EXTENSION_PATH = os.getenv("EXTENSION_PATH")
EXTENSION_ID = os.getenv("EXTENSION_ID")

# ~/Downloads/gologin_{EXTENSION_ID}.zip
PROFILE_DIR = os.getenv('HOME') + f"/Downloads/gologin_{EXTENSION_ID}.zip"

RESPONSES_PATH = os.getenv("RESPONSES_PATH")
PREFERENCES_PATH = os.getenv("PREFERENCES_PATH")
USE_DISPLAY = os.getenv("USE_DISPLAY", "false").lower() == "true"
API_PORT = int(os.getenv("API_PORT", 8000))

class CreateTaskRequest(BaseModel):
    captchaUrl: str
    host: str
    port: int
    cookies: Optional[str] = None
    username: Optional[str] = "user-sp0e9f6467-sessionduration-30"
    password: Optional[str] = "EWXv1a50bXfxc3vnsw"
    userAgent: Optional[str] = None

TIMEOUT_IN_MINUTES = 1
PROCESSING_URLS = set()
RESPONSES = {}
HASHES = {}
COOKIES = {}
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

def write_preferences(profile_dir: str, start_url: str, create_task_request: CreateTaskRequest, user_agent: str = None):
    preferences_path = f"{profile_dir}/Default/Preferences"
    # copy this preferences file to a temp directory
    # shutil.copy(preferences_path, os.path.join(os.path.dirname(__file__), PREFERENCES_PATH))
    with open(preferences_path, "r", encoding="utf-8") as f:
        preferences = json.load(f)
        preferences["gologin"]["startupUrl"] = start_url
        preferences["gologin"]["startup_urls"] = [start_url]
        preferences['extensions']['settings']['enhdnjlcnmhiplinedcodcalnmpkejej']['location'] = 8

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
        if 'geo.captcha-delivery.com' in captcha_url:
            raise HTTPException(status_code=400, detail="Cannot solve geo.captcha-delivery.com captchas")
        # Convert the captcha URL using the hashCode function
        hash_code = sha256_hash(captcha_url + str(time.time()))
        HASHES[hash_code] = captcha_url
        COOKIES[hash_code] = createTaskRequest.cookies
        # Copy directory to a temp directory
        subprocess.run(["unzip", PROFILE_DIR, '-d', f"/tmp/{hash_code}"])
        TEMP_PROFILE_DIR = f"/tmp/{hash_code}"

        # Get a random fingerprint json file from `fingerprints`

        new_url = f'http://localhost:{API_PORT}/v1/redirect?hash_code={hash_code}&extensionId=enhdnjlcnmhiplinedcodcalnmpkejej'

        # Write captcha url as start url
        write_preferences(TEMP_PROFILE_DIR, start_url=new_url, user_agent=user_agent, create_task_request=createTaskRequest)

        # Launch the browser with the provided command
        command = [
            CHROME_PATH,
            f"--user-data-dir={TEMP_PROFILE_DIR}",
            f"--proxy-server=http://{proxy_host}:{proxy_port}",
            f"--host-resolver-rules=MAP * 0.0.0.0 , EXCLUDE {proxy_host}",
            "--disable-encryption",
            "--donut-pie=undefined",
            "--font-masking-mode=2",
            '--disable-application-cache',
            '--disable-offline-load-stale-cache',
            '--disable-gpu-program-cache',
            '--disable-gpu-shader-disk-cache',
            # disable disk-cache
            "--disk-cache-dir=/dev/null",
            "--aggresive-cache-discard",
        ]
        print(*command)
        async def process():
            p = subprocess.Popen(command, start_new_session=True)
            PROCESSING_URLS.add(captcha_url)

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

@app.get("/v1/redirect")
async def redirect(hash_code: str, extensionId: str):
    # Get the original URL from the hash code
    original_url = HASHES.get(hash_code)
    cookies = COOKIES.get(hash_code) or ''
    if cookies:
        cookies = '; '.join([f"{k}={v}" for k, v in json.loads(cookies).items()])
    if cookies:
        cookies = 'document.cookie = "' + cookies + '";'
    # render the HTML that will save the hash into localstorage,
    # add cookies to the browser for the original URL and redirect
    html = f"""
    <html>
        <head>
            <script>
            function Redirect() {{
                // save hash to sessionStorage
                chrome.runtime.sendMessage("{extensionId}", {{
                    message: "storeHash",
                    hash: "{hash_code}",
                    url: "{original_url}",
                    apiPort: {API_PORT}
                }});
                {cookies}
            }}
            setTimeout(Redirect, 1000);
            </script>
        </head>
        <body onload="Redirect()">
            Redirecting...
            <div>
                <a href="{original_url}">Click here if you are not redirected</a>
            </div>
        </body>
    </html>
    """
    return Response(content=html, media_type="text/html")


def sha256_hash(s):
    return hashlib.sha256(s.encode()).hexdigest()

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
