import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import uuid

from modules.google_search import GoogleSearchBypass
import time

def test_google_bypass():
    print("=== Testing Google Search Bypass ===")
    task_id = f"sasha_{uuid.uuid4().hex}"
    print(task_id)
    # input('??')
    
    bypass = GoogleSearchBypass(
        # proxy_pool="http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004",
        # proxy_pool="brd.superproxy.io:33335:brd-customer-hl_f9eb8d89-zone-zone19-ip-209.20.171.245:r32rfqmvys39",
        # proxy_pool="brd-customer-hl_f9eb8d89-zone-zone19-ip-185.255.164.144:r32rfqmvys39@brd.superproxy.io:33335",
        proxy_pool="http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.decodo.com:19120",
        url='https://www.google.fr/search?q=pizza',
        # task_id="sasha",
        task_id=task_id,
        headless=False 
    )
    
    try:
        print("\n1. Starting bypass process...")
        content, cookies, curl = bypass.bypass()
        
        print("\n2. Results:")
        print(f"\nCookies received:")
        for k, v in cookies.items():
            print(f"  {k}: {v}")
            
        print(f"\nCurl command:")
        print(curl)
        
        print("\nContent saved to test.html")
        
    except Exception as e:
        print(f"\nError during test: {e}")

if __name__ == "__main__":
    while True: 
        test_google_bypass()
        time.sleep(2)
