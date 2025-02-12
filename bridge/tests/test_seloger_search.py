import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.seloger_search import SeLogerSearchBypass
import time

def test_seloger_bypass():
    print("=== Testing Google Search Bypass ===")
    
    bypass = SeLogerSearchBypass(
        proxy_pool="http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004",
        url="https://www.seloger.com/list.htm?projects=1&types=1&places=[{%22inseeCodes%22:[350238]}]&mandatorycommodities=0&enterprise=0&qsVersion=1.0&m=search_refine-redirection-search_results",
        task_id="selogertest123",
        headless=False 
    )
    
    try:
        print("\n1. Starting bypass process...")
        content, cookies, curl = bypass.bypass()
        input('mm')
        
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
    test_seloger_bypass()