import sys
import os
import time
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.yelp_search import YelpSearchBypass

def test_yelp_bypass():
    print("=== Testing Yelp Search Bypass ===")
    task_id = f"yelp_{uuid.uuid4().hex}"
    print("Task ID:", task_id)
    
    bypass = YelpSearchBypass(
        proxy_pool="http://sp0e9f6467:EWXv1a50bXfxc3vnsw@gate.decodo.com:10001",  # residential proxy
        url='https://www.yelp.com/search?find_desc=Corporate+Event+Planners&find_loc=San+Mateo%2C+CA',
        task_id=task_id,
        headless=False 
    )
    
    try:
        print("\n1. Starting bypass process...")
        content, cookies, headers, curl = bypass.bypass()
        
        print("\n2. Results:")
        print("\nCookies received:")
        for k, v in cookies.items():
            print(f"  {k}: {v}")
            
        print("\nCurl command:")
        print(curl)
        
        print("\nContent saved to test.html")
        
    except Exception as e:
        print(f"\nError during test: {e}")

if __name__ == "__main__":
    while True: 
        test_yelp_bypass()
        input('?')
