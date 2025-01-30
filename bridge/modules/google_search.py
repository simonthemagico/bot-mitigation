from .base import BaseBypass
from utils.chrome_manager import ChromeManager
from utils.proxy_manager import ProxyManager

import time
import pychrome
import json

class GoogleSearchBypass(BaseBypass):
    def __init__(self, proxy_pool: str, url: str, headless: bool = True):
        super().__init__(proxy_pool, url, headless)
        self.proxy_port, self.chrome_port = self.generate_unique_ports()
        
        self.proxy_server = ProxyManager(
            proxy_pool=proxy_pool, 
            proxy_port=self.proxy_port
        )
        
        self.chrome = ChromeManager(
            proxy_port=self.proxy_port,
            chrome_port=self.chrome_port,
            headless=headless
        )

    def bypass(self):
        try:
            print("Starting Proxy Server...")
            self.proxy_server.start_proxy_server()

            print("Starting Chrome Browser...")
            self.chrome.create_chrome()

            time.sleep(5)

            browser = pychrome.Browser(url=f"http://localhost:{self.chrome_port}")
            print("Connected to Chrome Remote Debugger.")
            
            version_info = browser.version()
            print("Browser Version:", version_info['Browser'])

            tab_lists = browser.list_tab()
            if len(tab_lists)>0:
                tab = tab_lists[0]
            else:
                tab = browser.new_tab()

            tab.start()
            tab.Network.enable()
            tab.Page.enable()

            global captured_headers
            captured_headers = {}

            def request_intercept(request, **kwargs):
                """Callback function to capture headers safely."""
                headers = request.get("headers", {})
                captured_headers.update(headers)
                # print(f"Captured Headers: {captured_headers}")

            tab.Network.requestWillBeSent = request_intercept

            # print(f"Navigating to URL: https://api.ipify.org")
            # tab.Page.navigate(url="https://api.ipify.org")
            # time.sleep(5)

            print(f"Navigating to URL: {self.url}")
            tab.Page.navigate(url=self.url)
            
            print('Waiting 10 seconds')
            time.sleep(10)
            print('Waiting done')

            # Fetch the cookies
            cookies_list = tab.Network.getCookies()['cookies']
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies_list}
            print("Cookies Retrieved:", cookie_dict)

            input('??')

            # Get the page content
            result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
            page_content = result.get("result", {}).get("value", "")
            print("Page Content Retrieved.")

            # Save page content to a file
            with open("test.html", "w", encoding="utf-8") as f:
                f.write(page_content)
            print("Page content saved to 'test.html'.")

            # Format cookies for curl
            cookies_curl = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])

            # Format headers for curl
            headers_curl = " ".join([f"-H '{k}: {v}'" for k, v in captured_headers.items() if k.lower() not in ['cookie']])

            # Generate curl command
            curl_command = f"curl -x {self.proxy_pool} '{self.url}' --cookie '{cookies_curl}' {headers_curl} -o ~/test.html"
            print("\nGenerated cURL Command:")
            print(curl_command)

            assert all([page_content, cookie_dict, curl_command])

            return page_content, cookie_dict, curl_command
        
        except Exception as e:
            print(f"Error during operation: {e}")
            raise e

        finally:
            print("Stopping Chrome Browser...")
            self.chrome.close_chrome()
            print("Stopping Proxy Server...")
            self.proxy_server.stop_proxy_server()