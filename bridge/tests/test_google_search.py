import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.google_search import GoogleSearchBypass
import time

def test_google_bypass():
    print("=== Testing Google Search Bypass ===")
    
    bypass = GoogleSearchBypass(
        # proxy_pool="http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004",
        # proxy_pool="brd.superproxy.io:33335:brd-customer-hl_f9eb8d89-zone-zone19-ip-209.20.171.245:r32rfqmvys39",
        # proxy_pool="brd-customer-hl_f9eb8d89-zone-zone19-ip-185.255.164.144:r32rfqmvys39@brd.superproxy.io:33335",
        proxy_pool="user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:10001",
        url="https://www.google.com/search?q=pizza",
        task_id="sasha",
        headless=False 
    )
    
    try:
        print("\n1. Starting bypass process...")
        content, cookies, curl = bypass.bypass()

        input('mmmm')
        
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
    test_google_bypass()