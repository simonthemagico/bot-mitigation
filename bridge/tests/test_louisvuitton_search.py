import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.louisvuitton_search import LouisVuittonSearchByPass
import time

def test_louisvuitton_bypass():
    print("=== Testing Louis Vuitton Akami Bypass ===")
    
    bypass = LouisVuittonSearchByPass(
        proxy_pool="http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004",
        url="https://fr.louisvuitton.com/fra-fr/homme/portefeuilles-et-petite-maroquinerie/tous-les-portefeuilles-et-petite-maroquinerie/_/N-t1iazbp7",
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
     test_louisvuitton_bypass()