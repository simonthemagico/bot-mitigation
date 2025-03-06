import time
import pychrome
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

            print("Navigating first to a blank page...")
            tab.Page.navigate(url="about:blank")
            time.sleep(2)

            print(f"Navigating to URL: {self.url}")
            tab.Page.navigate(url=self.url)

            # Akamai challenge wait loop: check the DOM for 'var chlgeId'
            max_checks = 5
            for attempt in range(max_checks):
                result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
                page_content = result["result"]["value"]
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
            content = result["result"]["value"]
            print("Final HTML retrieved; length:", len(content))

            # Save final HTML to file if needed
            filepath = self.save_page_content(content=content, prefix="bypass")
            print("Page content saved to:", filepath)

            # Retrieve cookies
            raw_cookies = tab.Network.getCookies()['cookies']
            cookie_dict = {c['name']: c['value'] for c in raw_cookies}
            print("Cookies retrieved:", bool(cookie_dict))

            # Use a set of default headers that mimic a working browser request
            default_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            headers_list = [f"-H '{k}: {v}'" for k, v in default_headers.items()]
            headers_curl = " ".join(headers_list)

            # Generate a cURL command with cookies and --compressed flag
            cookies_curl = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            curl_command = (
                f"curl -x {self.proxy_pool} '{self.url}' --cookie '{cookies_curl}' "
                f"{headers_curl} --compressed -o ~/louisvuitton_test.html"
            )
            print("\nGenerated cURL Command:")
            print(curl_command)

            assert all([content, cookie_dict, curl_command])
            return content, cookie_dict, default_headers, curl_command

        except Exception as e:
            print(f"Error during operation: {e}")
            raise e

        finally:
            print("Cleaning up...")
            self.cleanup()