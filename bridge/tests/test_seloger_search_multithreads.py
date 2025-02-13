import sys
import os
import time
import concurrent.futures
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.seloger_search import SeLogerSearchBypass

# Ensure the project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# List of proxies (replace with actual proxy credentials)
PROXY_LIST = [
    "http://sp0e9f6467:EWXv1a50bXfxc3vnsw@fr.smartproxy.com:40001",
    "http://sp0e9f6467:EWXv1a50bXfxc3vnsw@fr.smartproxy.com:40002",
    "http://sp0e9f6467:EWXv1a50bXfxc3vnsw@fr.smartproxy.com:40003",
]

# Number of threads to run in parallel
NUM_THREADS = 2

# Test URL
TEST_URL = "https://www.seloger.com/list.htm?projects=1&types=1&places=[{%22inseeCodes%22:[350238]}]&mandatorycommodities=0&enterprise=0&qsVersion=1.0&m=search_refine-redirection-search_results"

def test_seloger_bypass(proxy, task_id):
    print(f"=== Testing SeLoger Bypass with {proxy} ===")
    
    bypass = SeLogerSearchBypass(
        proxy_pool=proxy,
        url=TEST_URL,
        task_id=task_id,
        headless=False
    )
    
    try:
        print(f"\n1. Starting bypass process for {task_id}...")
        content, cookies, curl = bypass.bypass()
        
        print(f"\n2. Results for {task_id}:")
        print(f"\nCookies received:")
        for k, v in cookies.items():
            print(f"  {k}: {v}")
            
        print(f"\nCurl command:")
        print(curl)
        
        print(f"\nContent saved for {task_id}\n")
    except Exception as e:
        print(f"\nError during test {task_id}: {e}")

if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = []
        
        for i, proxy in enumerate(PROXY_LIST):
            task_id = f"selogertest_{i+1}"
            futures.append(executor.submit(test_seloger_bypass, proxy, task_id))
        
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # Wait for the thread to finish
            except Exception as e:
                print(f"Thread failed: {e}")
