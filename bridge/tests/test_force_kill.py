import requests
import time
import subprocess
import os

# API Endpoint
BASE_URL = "https://api.bridge.lobstr.io"
TOKEN = "77f6bc041b99accf93093ebdc67a45ef472a4496"  # Replace with your actual token

def test_create_task():
    """Test creating a Google Search bypass task"""
    payload = {
        "url": "https://www.google.com/search?q=pizzax",
        "proxy_pool": "user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:10001",
        "bypass_method": "google_search",
        "headless": False
    }

    headers = {
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json"
    }

    print("🔹 Creating a new task...")
    response = requests.post(f"{BASE_URL}/task", json=payload, headers=headers)

    assert response.status_code == 200, f"Task creation failed: {response.text}"

    data = response.json()
    print("✅ Task created:", data)
    return data["id"]

def test_check_task_status(task_id):
    """Test checking task status until completion"""
    headers = {
        "Authorization": f"Token {TOKEN}"
    }

    print(f"🔹 Checking status for task: {task_id}")

    for _ in range(30):  # Wait up to 30 seconds
        response = requests.get(f"{BASE_URL}/task/{task_id}", headers=headers)
        
        assert response.status_code == 200, f"Failed to check task status: {response.text}"
        data = response.json()

        print(f"⏳ Task Status: {data['status']}")

        if data["status"] in ["done", "error", "timeout"]:
            print("✅ Task completed with status:", data["status"])
            return data

        time.sleep(2)  # Wait before checking again

    assert False, "🚨 Task did not complete in time!"

def get_running_chrome_pids():
    """Get running Chrome processes"""
    result = subprocess.run(["pgrep", "-fl", "chrome"], capture_output=True, text=True)
    return result.stdout.strip().split("\n") if result.stdout else []

def test_chrome_cleanup(before_pids):
    """Check if Chrome processes were cleaned up"""
    after_pids = get_running_chrome_pids()
    remaining_pids = set(after_pids) - set(before_pids)

    if remaining_pids:
        print("❌ Warning: Orphaned Chrome processes found:", remaining_pids)
    else:
        print("✅ Chrome cleanup successful, no orphaned processes.")

def run_tests():
    """Run all tests"""
    print("\n🛠 Running Chrome Bypass Tests...\n")

    # Step 1: Capture existing Chrome PIDs before test
    before_pids = get_running_chrome_pids()
    print("🔍 Chrome processes before test:", before_pids)

    # Step 2: Create a new task
    task_id = test_create_task()

    # Step 3: Wait for task completion
    test_check_task_status(task_id)

    # Step 4: Verify Chrome cleanup
    test_chrome_cleanup(before_pids)

if __name__ == "__main__":
    run_tests()
