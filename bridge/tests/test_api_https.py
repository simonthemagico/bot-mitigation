import requests
import time

# API Configuration
API_BASE_URL = "https://api.bridge.lobstr.io"
TOKEN = "77f6bc041b99accf93093ebdc67a45ef472a4496"  # Replace with your actual token

# Headers
HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# Task Request Payload
task_data = {
    "url": "https://www.google.fr/search?q=pizza",
    "proxy_pool": "http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004",
    "bypass_method": "google_search",
    "headless": False
}

# 1️⃣ Create a new task
print("[*] Sending request to create a new task...")
response = requests.post(f"{API_BASE_URL}/task", json=task_data, headers=HEADERS)

if response.status_code != 200:
    print(f"[!] Failed to create task: {response.json()}")
    exit()

task_id = response.json()["id"]
print(f"[+] Task created with ID: {task_id}")

# 2️⃣ Poll for task status
print("[*] Polling task status...")
while True:
    task_status_response = requests.get(f"{API_BASE_URL}/task/{task_id}", headers=HEADERS)
    
    if task_status_response.status_code != 200:
        print(f"[!] Error fetching task status: {task_status_response.json()}")
        break

    task_info = task_status_response.json()
    status = task_info["status"]

    print(f"[-] Current Status: {status}")

    if status in ["done", "error", "timeout"]:
        break  # Stop polling when task is completed or failed

    time.sleep(5)  # Wait before checking again

# 3️⃣ Display final result
print("[+] Final Task Result:")
print(task_info)
