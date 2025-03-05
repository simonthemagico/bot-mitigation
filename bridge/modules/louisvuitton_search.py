import time
import pychrome
import json
import os
from .base import BaseBypass

class LouisVuittonSearchByPass(BaseBypass):
    def __init__(self, proxy_pool: str, url: str, task_id: str, headless: bool = True):
        if not proxy_pool.startswith("http://") and not proxy_pool.startswith("https://"):
            proxy_pool = "http://" + proxy_pool

        super().__init__(
            proxy_pool,
            url,
            task_id,
            headless,
            user_data_dir=f"andrew_{task_id}"
        )
        self.initialize()

    def bypass(self):
        try:
            print("Starting Proxy Server...")
            self.proxy_server.start_proxy_server()

            print("Starting Chrome Browser...")
            self.chrome.create_chrome()
            time.sleep(5)

            # Connect to Chrome DevTools
            assert self.chrome_port
            browser = pychrome.Browser(url=f"http://localhost:{self.chrome_port}")
            print("Connected to Chrome Remote Debugger.")

            # Grab or create a new tab
            tab = browser.list_tab()[0] if browser.list_tab() else browser.new_tab()
            tab.start()

            # Enable the domains we need
            tab.Network.enable()
            tab.Page.enable()

            # Capture request headers from the main document request
            captured_headers = {}
            def request_intercept(request, **kwargs):
                # Capture headers from the request
                headers = request.get("headers", {})
                # For simplicity, we update our global dict (overwriting if repeated)
                for k, v in headers.items():
                    captured_headers[k] = v

            tab.Network.requestWillBeSent = request_intercept

            print("Navigating first to a blank page...")
            tab.Page.navigate(url="about:blank")
            time.sleep(2)

            print(f"Navigating to URL: {self.url}")
            tab.Page.navigate(url=self.url)

            # Akamai challenge wait loop: check the DOM for 'var chlgeId'
            max_checks = 5
            for attempt in range(max_checks):
                result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
                page_content = result.get("result", {}).get("value", "")
                if "var chlgeId" not in page_content:
                    print(f"Akamai challenge seems passed (Attempt {attempt + 1}).")
                    break
                print(f"[Attempt {attempt + 1}] Challenge present; waiting 3s to reload.")
                time.sleep(3)
            
            # Optionally, wait a bit longer to ensure the page is fully loaded
            print("Waiting an extra 5 seconds to ensure full page load...")
            time.sleep(5)

            # Retrieve final HTML
            result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
            content = result.get("result", {}).get("value", "")
            print("Final HTML retrieved; length:", len(content))

            # Save final HTML to file if needed
            filepath = self.save_page_content(content=content, prefix="bypass")
            print("Page content saved to:", filepath)

            # Retrieve cookies
            raw_cookies = tab.Network.getCookies().get('cookies', [])
            all_cookies = {c['name']: c['value'] for c in raw_cookies}
            print("Initial Cookies retrieved:", bool(all_cookies))

            raw_cookies = tab.Network.getCookies().get('cookies', [])
            all_cookies = {c['name']: c['value'] for c in raw_cookies}

            # Filter the cookies to only include the valid ones
            cookie_dict = {name: all_cookies[name] for name in all_cookies}
            print("Filtered Cookies:", bool(cookie_dict))

            # Filter out 'cookie' from captured_headers (if present)
            headers_dict = {k: v for k, v in captured_headers.items() if k.lower() != 'cookie'}
            print("Captured Request Headers: ", bool(headers_dict))

            # Generate a cURL command
            cookies_curl = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            headers_curl = " ".join([f"-H '{k}: {v}'" for k, v in headers_dict.items()])
            curl_command = f"curl -x {self.proxy_pool} '{self.url}' --cookie '{cookies_curl}' {headers_curl} -o ~/louisvuitton_test.html"
            print("\nGenerated cURL Command")

            assert all([content, cookie_dict, curl_command])
            return content, cookie_dict, headers_dict, curl_command

        except Exception as e:
            input(f"Error during operation: {e}")
            raise e

        finally:
            print("Cleaning up...")
            self.cleanup()