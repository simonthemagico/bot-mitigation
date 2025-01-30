import requests
import json
import time
from typing import Dict, Optional
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ERROR = "error"
    TIMEOUT = "timeout"

# API Configuration
BASE_URL = "http://localhost:8000"
API_KEYS = {
    "valid": "bri_live_51IkEHVAFM6jPN0afKwmUtcW1EkQyHGYmLM9QNDtBAWsx0huWaHyFfEDSlFcnzjM1fojdcJrkNeSPneJ3VC1ZvkOP00O8fbReYR",
    "invalid": "lbr_test_invalid_key"
}

def test_create_task(api_key):
    """Test task creation endpoint"""
    print("\n=== Testing Task Creation ===")
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    data = {
        "url": "https://www.google.com/search?q=test",
        "proxy_pool": "http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004",
        "bypass_method": "google-search",
        "headless": False
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/task",
            headers=headers,
            json=data
        )
        
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        
        return response.json().get("task_id") if response.status_code == 200 else None
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def test_get_task(task_id, api_key):
    """Test task retrieval endpoint"""
    print("\n=== Testing Task Retrieval ===")
    
    headers = {
        "X-API-Key": api_key
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/task/{task_id}",
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        
    except Exception as e:
        print(f"Error: {str(e)}")

def test_auth():
    """Test authentication with valid and invalid keys"""
    print("\n=== Testing Authentication ===")
    
    # Test invalid key
    print("\nTesting with invalid API key...")
    task_id = test_create_task(API_KEYS["invalid"])
    
    # Test valid key
    print("\nTesting with valid API key...")
    task_id = test_create_task(API_KEYS["valid"])
    
    if task_id:
        print("\nTesting task retrieval with valid task ID...")
        test_get_task(task_id, API_KEYS["valid"])

def test_health():
    """Test the health check endpoint"""
    print("\n=== Testing Health Check ===")

    headers = {
        "X-API-Key": API_KEYS["valid"]
    }
    
    try:
        response = requests.get(f"{BASE_URL}/health", headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False
    
def test_google_bypass(query: str = "pizza") -> Optional[Dict]:
    """
    Test complete Google search bypass flow
    
    Args:
        query: Search term to test
    """

    headers = {
        "X-API-Key": API_KEYS["valid"]
    }

    print("\n=== Testing Google Search Bypass ===")
    
    # Prepare test data
    data = {
        "url": f"https://www.google.com/search?q={query}",
        "proxy_pool": "http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004",
        "bypass_method": "google-search",
        "headless": True
    }
    
    try:
        # Step 1: Create task
        print("\n1. Creating bypass task...")
        response = requests.post(
            f"{BASE_URL}/task",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"Task created with ID: {task_id}")
        print(json.dumps(task_data, indent=2))
        
        # Step 2: Poll for results
        print("\n2. Polling for task completion...")
        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts:
            response = requests.get(
                f"{BASE_URL}/task/{task_id}",
                headers=headers
            )
            result = response.json()
            
            if result["status"] in [TaskStatus.DONE, TaskStatus.ERROR, TaskStatus.TIMEOUT]:
                break
                
            print(f"Task status: {result['status']}. Waiting...")
            time.sleep(3)
            attempt += 1
        
        # Step 3: Show final results
        print("\n3. Final task status:")
        print(json.dumps(result, indent=2))
        
        if result["status"] == "done":
            print("\nSuccess! Received cookies and curl command")
            return result
        else:
            print(f"\nTask failed with status: {result['status']}")
            if result.get("error"):
                print(f"Error: {result['error']}")
            return None
            
    except Exception as e:
        print(f"Error during test: {str(e)}")
        return None


def main():
    print("Starting Google Bypass Test...")

    headers = {
        "X-API-Key": API_KEYS["valid"],
        "Content-Type": "application/json"
    }
    
    # Test health first
    health_response = requests.get(f"{BASE_URL}/health", headers=headers)
    if health_response.status_code != 200:
        print("Health check failed! Stopping test.")
        return
        
    result = test_google_bypass(query="test query")

    if result:
        print("\n=== Test Completed Successfully! ===")
    else:
        print("\n=== Test Failed! ===")

if __name__ == "__main__":
    main()