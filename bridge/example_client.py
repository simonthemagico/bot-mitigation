#!/usr/bin/env python3
"""
Example client script for bridge API - Google Search Bypass

Usage:
    python3 example_client.py
"""

import requests
import time

# ============================================================================
# Configuration
# ============================================================================

API_URL = "https://bridge.datamonkeyz.com"  # Change to your production URL if needed
API_TOKEN = "77f6bc041b99accf93093ebdc67a45ef472a4496"


# ============================================================================
# API Client Functions
# ============================================================================

def create_task(url, proxy_pool, bypass_method="google_search", headless=True):
    """
    Create a new bypass task

    Args:
        url: URL to bypass
        proxy_pool: Proxy in format "http://user:pass@host:port"
        bypass_method: Type of bypass (google_search, seloger_search, etc.)
        headless: Whether to run Chrome in headless mode

    Returns:
        task_id: ID of the created task, or None if failed
    """
    headers = {
        "Authorization": f"Token {API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "url": url,
        "proxy_pool": proxy_pool,
        "bypass_method": bypass_method,
        "headless": headless
    }

    print(f"Creating task for URL: {url}")

    response = requests.post(
        f"{API_URL}/task",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        task = response.json()
        print(f"✅ Task created: {task['id']}")
        print(f"   Status: {task['status']}")
        print(f"   Method: {task['bypass_method']}")
        return task['id']
    elif response.status_code == 429:
        print("❌ Too many tasks in progress, please retry later")
        return None
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def get_task_status(task_id):
    """
    Get the status of a task

    Args:
        task_id: ID of the task

    Returns:
        dict: Task information, or None if failed
    """
    headers = {
        "Authorization": f"Token {API_TOKEN}"
    }

    response = requests.get(
        f"{API_URL}/task/{task_id}",
        headers=headers
    )

    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        print(f"❌ Task {task_id} not found")
        return None
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return None


def wait_for_task(task_id, timeout=120, poll_interval=5):
    """
    Wait for a task to complete

    Args:
        task_id: ID of the task
        timeout: Maximum time to wait in seconds
        poll_interval: Time between status checks in seconds

    Returns:
        dict: Final task result, or None if timeout/failed
    """
    start_time = time.time()

    print(f"\nWaiting for task {task_id} to complete...")
    print(f"Timeout: {timeout}s | Poll interval: {poll_interval}s\n")

    while time.time() - start_time < timeout:
        task = get_task_status(task_id)

        if not task:
            return None

        status = task['status']
        elapsed = int(time.time() - start_time)
        print(f"[{elapsed}s] Status: {status}")

        if status == "done":
            print("\n✅ Task completed successfully!")
            return task
        elif status == "error":
            print(f"\n❌ Task failed with error:")
            print(f"   {task.get('error')}")
            return task
        elif status == "timeout":
            print(f"\n⏱️  Task timed out:")
            print(f"   {task.get('error')}")
            return task

        time.sleep(poll_interval)

    print(f"\n❌ Wait timeout exceeded ({timeout}s)")
    return None


def check_health():
    """
    Check API health status

    Returns:
        dict: Health information, or None if failed
    """
    headers = {
        "Authorization": f"Token {API_TOKEN}"
    }

    response = requests.get(f"{API_URL}/health", headers=headers)

    if response.status_code == 200:
        health = response.json()
        print("=== API Health ===")
        print(f"Status: {health['status']}")
        print(f"Active tasks: {health['active_tasks']}")
        print(f"Total tasks in store: {health['tasks_in_store']}")
        print(f"Timestamp: {health['timestamp']}")
        return health
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return None


# ============================================================================
# Main Example
# ============================================================================

def main():
    """
    Main example: Create a Google Search bypass task and wait for results
    """
    print("=" * 70)
    print("Bridge API Client - Google Search Bypass Example")
    print("=" * 70)
    print()

    # 1. Check API health
    print("Step 1: Checking API health...")
    health = check_health()
    print()

    if not health or health['status'] != 'healthy':
        print("API is not healthy, aborting.")
        return

    # 2. Create a Google Search bypass task
    print("Step 2: Creating bypass task...")
    task_id = create_task(
        url="https://www.google.fr/search?q=pizza",
        proxy_pool="http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.decodo.com:19120",
        bypass_method="google_search",
        headless=False  # Set to True for headless mode
    )

    if not task_id:
        print("Failed to create task, aborting.")
        return

    print()

    # 3. Wait for task to complete
    print("Step 3: Waiting for task to complete...")
    result = wait_for_task(task_id, timeout=120, poll_interval=5)

    if not result:
        print("Failed to get task result.")
        return

    print()

    # 4. Display results
    if result['status'] == 'done':
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print()

        print("Cookies:")
        for name, value in result.get('cookies', {}).items():
            print(f"  {name}: {value[:50]}..." if len(value) > 50 else f"  {name}: {value}")
        print()

        print("Headers:")
        for name, value in result.get('headers', {}).items():
            print(f"  {name}: {value}")
        print()

        print("cURL Command:")
        print(result.get('curl_command', 'N/A'))
        print()

        print("=" * 70)
        print("✅ SUCCESS - Task completed successfully!")
        print("=" * 70)
    else:
        print("=" * 70)
        print("❌ FAILED - Task did not complete successfully")
        print("=" * 70)


if __name__ == "__main__":
    main()

