from .base import BaseBypass

import time
import pychrome
import json
import os

class GoogleSearchBypass(BaseBypass):
    def __init__(self, proxy_pool: str, url: str, task_id: str, headless: bool = True):
        super().__init__(
            proxy_pool, 
            url, 
            task_id, 
            headless, 
            user_data_dir=f"sasha_{task_id}", 
            extension_path="extensions/capsolver", 
            disable_images=False
        )
        self.initialize()

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

            # Tab management
            tab = browser.list_tab()[0] if browser.list_tab() else browser.new_tab()
            tab.start()

            tab.Network.enable()
            tab.Page.enable()

            captured_headers = {}
            def request_intercept(request, **kwargs):
                """Callback function to capture headers safely."""
                headers = request.get("headers", {})
                captured_headers.update(headers)

            tab.Network.requestWillBeSent = request_intercept

            print(f"Navigating to URL: https://api.ipify.org")
            tab.Page.navigate(url="https://api.ipify.org")
            time.sleep(5)

            print(f"Navigating to URL: {self.url}")
            tab.Page.navigate(url=self.url)
            
            print('Waiting 5 seconds')
            time.sleep(5)
            print('Waiting done')

            # Fetch the cookies
            cookies_list = tab.Network.getCookies()['cookies']
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies_list}
            print("Cookies Retrieved:", cookie_dict)

            # Fetch the headers
            headers_dict = {k: v for k, v in captured_headers.items() if k.lower() not in ['cookie']}

            # Get the page content
            result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
            page_content = result.get("result", {}).get("value", "")
            print("Page Content retrieved.")

            # Use base class method to save content
            filepath = self.save_page_content(
                content=page_content,
                prefix="bypass"
            )

            # Format cookies for curl
            cookies_curl = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            headers_curl = " ".join([f"-H '{k}: {v}'" for k, v in captured_headers.items() if k.lower() not in ['cookie']])
            curl_command = f"curl -x {self.proxy_pool} '{self.url}' --cookie '{cookies_curl}' {headers_curl} -o ~/test.html"

            print("\nGenerated cURL Command:")
            print(curl_command)

            assert all([page_content, cookie_dict, curl_command])

            return page_content, cookie_dict, headers_dict, curl_command
        
        except Exception as e:
            print(f"Error during operation: {e}")
            raise e

        finally:
            print("Cleaning up...")
            self.cleanup()