import requests
import json
import time

# API Configuration
BASE_URL = "http://localhost:8000"
TOKEN = "77f6bc041b99accf93093ebdc67a45ef472a4496"

HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

def test_flow():
    # 1. Check health
    print("1. Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health", headers=HEADERS)
    print(f"Health status: {response.json()}")

    # 2. Create bypass task
    print("\n2. Creating bypass task...")
    task_data = {
        "url": "https://www.google.com/search?q=crabcrab",
        "proxy_pool": "http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004",
        "bypass_method": "google_search",
        "headless": False,  # Set to False to see the browser
        "use_proxy": False
    }

    response = requests.post(
        f"{BASE_URL}/task", 
        headers=HEADERS,
        json=task_data
    )
    print(response.json())
    task_id = response.json()["id"]
    print(f"Task created with ID: {task_id}")

    # 3. Poll for results
    print("\n3. Polling for results...")
    max_attempts = 15
    for i in range(max_attempts):
        response = requests.get(
            f"{BASE_URL}/task/{task_id}",
            headers=HEADERS
        )
        result = response.json()
        status = result["status"]
        print(f"Status: {status}")
        
        if status in ["done", "error", "timeout"]:
            break
            
        time.sleep(2)

    # 4. Show final results
    print("\n4. Final Results:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_flow()