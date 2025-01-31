import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.base import BaseBypass
import time
import pychrome

class TestBypass(BaseBypass):
    """Test implementation of BaseBypass with real browser test"""
    def bypass(self):
        try:
            # Start components
            self.proxy_server.start_proxy_server()
            time.sleep(2)  # Wait for proxy to start
            
            self.chrome.create_chrome()
            time.sleep(2)  # Wait for Chrome
            
            # Connect to Chrome
            browser = pychrome.Browser(url=f"http://localhost:{self.chrome_port}")
            tab = browser.list_tab()[0] if browser.list_tab() else browser.new_tab()
            tab.start()
            
            # Enable required domains
            tab.Network.enable()
            tab.Page.enable()
            
            # Visit ipify
            print("\nVisiting api.ipify.org...")
            tab.Page.navigate(url="https://api.ipify.org")
            time.sleep(5)  # Wait for page load
            
            # Get IP address
            result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
            content = result.get("result", {}).get("value", "")
            print(f"Proxy IP: {content.strip()}")
            
            # Get cookies
            cookies = tab.Network.getCookies()
            
            return content, cookies['cookies'], "test_curl"
            
        except Exception as e:
            print(f"Error during bypass: {e}")
            raise

def test_base():
    print("=== Testing BaseBypass ===")
    
    bypass = TestBypass(
        proxy_pool="http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004",
        url="https://api.ipify.org",
        headless=False
    )
    
    try:
        print("\n1. Testing port generation...")
        proxy_port, chrome_port = bypass.generate_unique_ports()
        print(f"Generated ports - Proxy: {proxy_port}, Chrome: {chrome_port}")
        
        print("\n2. Testing initialization...")
        bypass.initialize()
        print("Managers initialized successfully")
        
        print("\n3. Testing actual bypass...")
        content, cookies, curl = bypass.bypass()
        print(f"Content received: {content}")
        print(f"Cookies: {cookies}")
        
        print("\nTest running. Press Enter to cleanup...")
        input()
        
    finally:
        print("\n4. Cleaning up...")
        bypass.cleanup()
        print("Cleanup complete")

if __name__ == "__main__":
    test_base()