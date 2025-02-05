import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Any
import asyncio

# API Configuration
BASE_URL = "http://localhost:8000"
TOKEN = "77f6bc041b99accf93093ebdc67a45ef472a4496"

HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

def format_timestamp():
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]

def monitor_task(task_id: str, query: str) -> Dict:
    """Monitor a single task until completion"""
    while True:
        try:
            response = requests.get(f"{BASE_URL}/task/{task_id}", headers=HEADERS)
            result = response.json()
            status = result["status"]
            print(f"[{format_timestamp()}] {query} - Status: {status}")
            
            if status in ["done", "error", "timeout"]:
                print(f"[{format_timestamp()}] Task {task_id} ({query}) completed with status: {status}")
                if status == "done":
                    print(f"[{format_timestamp()}] Cookies received for {query}")
                return result
                
            time.sleep(1)  # Poll every second
        except Exception as e:
            print(f"[{format_timestamp()}] Error monitoring {query}: {e}")
            time.sleep(1)

def run_task(config: Dict[str, Any]) -> Dict:
    query = config["query"]
    proxy = config["proxy"]
    
    print(f"[{format_timestamp()}] Starting task for query: {query} using proxy: {proxy[-5:]}")
    
    data = {
        "url": f"https://www.google.com/search?q={query}",
        "proxy_pool": proxy,
        "bypass_method": "google_search",
        "headless": False
    }
    
    try:
        # Create task
        print(f"[{format_timestamp()}] Creating task for {query}...")
        response = requests.post(f"{BASE_URL}/task", headers=HEADERS, json=data)
        response.raise_for_status()
        
        task_data = response.json()
        task_id = task_data["id"]
        print(f"[{format_timestamp()}] Task created for {query}: {task_id}")
        
        # Monitor task until completion
        return monitor_task(task_id, query)
        
    except Exception as e:
        print(f"[{format_timestamp()}] Error creating task for {query}: {e}")
        return {"error": str(e)}

def test_concurrent_tasks():
    print(f"[{format_timestamp()}] Starting concurrent tasks test...\n")
    
    with ThreadPoolExecutor(max_workers=len(TEST_CASES)) as executor:
        futures = {
            executor.submit(run_task, config): config["query"] 
            for config in TEST_CASES
        }
        
        results = []
        for future in as_completed(futures):
            query = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"[{format_timestamp()}] Task for {query} failed: {e}")
    
    print(f"\n[{format_timestamp()}] All tasks completed!")

if __name__ == "__main__":
    TEST_CASES = [
        {
            "query": "pizza",
            "proxy": "http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004"
        },
        {
            "query": "crab",
            "proxy": "http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20005"
        }
    ]
    
    test_concurrent_tasks()