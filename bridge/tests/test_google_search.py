import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.google_search import GoogleSearchBypass
import time

def test_google_bypass():
    print("=== Testing Google Search Bypass ===")
    
    bypass = GoogleSearchBypass(
        proxy_pool="http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004",
        url="https://www.google.com/search?q=pizza",
        task_id="tk_test123",
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
    test_google_bypass()