from fastapi import FastAPI, HTTPException
import subprocess
import os
import asyncio
import json
import hashlib
import os
from pydantic import BaseModel
import time

app = FastAPI()

class CreateTaskRequest(BaseModel):
    captchaUrl: str
    host: str
    port: int

# "/Users/administrator/.gologin/browser/orbita-browser-118/Orbita-Browser.app/Contents/MacOS/Orbita --user-data-dir=/tmp/gologin_b3aca92c79/profiles/655208c87e736c4718ccde8e --disable-encryption --donut-pie=undefined --font-masking-mode=2 --load-extension=/Users/administrator/.gologin/extensions/cookies-ext/655208c87e736c4718ccde8e,/Users/administrator/.gologin/extensions/passwords-ext/655208c87e736c4718ccde8e --proxy-server=http://fr.smartproxy.com:40001 --host-resolver-rules=MAP * 0.0.0.0 , EXCLUDE fr.smartproxy.com --lang=en-US"
CHROME_PATH = "/Users/administrator/.gologin/browser/orbita-browser-118/Orbita-Browser.app/Contents/MacOS/Orbita"
PROFILE_DIR = "/Users/administrator/Downloads/655208c87e736c4718ccde8e"
EXTENSION_PATH = "/Users/administrator/Downloads/Projects/xhr-response-saver"
RESPONSES_PATH = "/Users/administrator/Downloads/Responses/"
TIMEOUT_IN_MINUTES = 1

def write_start_url(start_url: str, profile_dir: str):
    preferences_path = f"{profile_dir}/Default/Preferences"

    with open(os.path.join(os.path.dirname(__file__), "files/Preferences"), "r", encoding="utf-8") as f:
        preferences = json.load(f)
        preferences["gologin"]["startupUrl"] = start_url
        preferences["gologin"]["startup_urls"] = [start_url]

    # Write this in preferences_path
    with open(preferences_path, "w", encoding="utf-8") as f:
        json.dump(preferences, f)

@app.post("/v1/createTask")
async def create_task(createTaskRequest: CreateTaskRequest):
    # proxy host, port
    proxy_host = createTaskRequest.host
    proxy_port = createTaskRequest.port

    captcha_url = createTaskRequest.captchaUrl
    # Convert the captcha URL using the hashCode function
    hash_code = sha256_hash(captcha_url)
    # Write captcha url as start url
    write_start_url(captcha_url, PROFILE_DIR)
    
    # Launch the browser with the provided command
    command = [
        CHROME_PATH,
        f"--user-data-dir={PROFILE_DIR}",
        "--disable-encryption",
        "--donut-pie=undefined",
        "--font-masking-mode=2",
        f"--load-extension=/Users/administrator/.gologin/extensions/cookies-ext/655208c87e736c4718ccde8e,/Users/administrator/.gologin/extensions/passwords-ext/655208c87e736c4718ccde8e,{EXTENSION_PATH}",
        f"--proxy-server=http://{proxy_host}:{proxy_port}"
        "--host-resolver-rules=MAP * 0.0.0.0 , EXCLUDE fr.smartproxy.com",
        "--lang=en-US"
    ]
    p = subprocess.Popen(command, start_new_session=True)

    # Wait for the response file
    response_file = RESPONSES_PATH + "response_" + hash_code + ".json"
    # Check time
    start_time = time.time()
    while not os.path.exists(response_file):
        print(f"Waiting: {hash_code}")
        await asyncio.sleep(1)  # Check for file every second
        if time.time() - start_time > TIMEOUT_IN_MINUTES * 60:
            p.terminate()
            raise HTTPException(status_code=408, detail="Timeout")

    print(f"Found: {hash_code}")

    # Read and return the JSON response
    with open(response_file, 'r') as file:
        response_data = json.load(file)

    # Close the browser
    p.terminate()

    return response_data

def sha256_hash(s):
    return hashlib.sha256(s.encode()).hexdigest()

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)