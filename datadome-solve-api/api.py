from fastapi import FastAPI
import subprocess
import os
import asyncio
import json
import hashlib
import os
import urllib
from pydantic import BaseModel

app = FastAPI()

class CreateTaskRequest(BaseModel):
    captchaUrl: str

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
    captcha_url = createTaskRequest.captchaUrl
    # Convert the captcha URL using the hashCode function
    hash_code = sha256_hash(captcha_url)
    # Write captcha url as start url
    profile_dir = "C:\\Users\\Administrator\\AppData\\Local\\Temp\\GoLogin\\profiles\\test_copy"
    write_start_url(captcha_url, profile_dir)
    
    # Launch the browser with the provided command
    browser_command = [
        "C:\\Users\\Administrator\\.gologin\\browser\\orbita-browser-118\\chrome.exe",
        f"--user-data-dir={profile_dir}",
        "--disable-encryption",
        "--donut-pie=undefined",
        "--font-masking-mode=2",
        "--load-extension=C:\\Users\\Administrator\\.gologin\\extensions\\cookies-ext\\654cc90e5617ed7916d4db05,C:\\Users\\Administrator\\.gologin\\extensions\\passwords-ext\\654cc90e5617ed7916d4db05,C:\\Users\\Administrator\\Documents\\xhr-response-saver",
        "--proxy-server=http://fr.smartproxy.com:40001",
        "--host-resolver-rules=MAP * 0.0.0.0 , EXCLUDE fr.smartproxy.com",
        "--lang=fr-FR"
    ]
    p = subprocess.Popen(browser_command, start_new_session=True)

    # Wait for the response file
    response_file = f"C:\\Users\\Administrator\\Downloads\\response_{hash_code}.json"
    while not os.path.exists(response_file):
        print(f"Waiting: {hash_code}")
        await asyncio.sleep(1)  # Check for file every second

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