import time
import pychrome
import os
from .base import BaseBypass

class ApriumSearchByPass(BaseBypass):
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

            browser = pychrome.Browser(url=f"http://localhost:{self.chrome_port}")
            print("Connected to Chrome Remote Debugger.")
            tab = browser.list_tab()[0] if browser.list_tab() else browser.new_tab()
            tab.start()
            tab.Network.enable()
            tab.Page.enable()


            self.captured_headers = {}
            def capture_request(**kwargs):
                request = kwargs.get("request")
                if request and request.get("url") == self.url:
                    # Store all headers from Chrome’s outgoing request
                    self.captured_headers.update(request.get("headers", {}))

            tab.Network.requestWillBeSent = capture_request
            def handle_response_received(**kwargs):
                response = kwargs.get("response")
                if response is None:
                    raise Exception("No response received")
                status = response.get("status")
                if status >= 400:
                    raise Exception(f"HTTP error: {status}")

            tab.Network.responseReceived = handle_response_received

            print("Navigating first to a blank page...")
            tab.Page.navigate(url="about:blank")
            time.sleep(2)

            print(f"Navigating to URL: {self.url}")
            tab.Page.navigate(url=self.url)

            max_checks = 100
            for attempt in range(max_checks):
                result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
                if "var chlgeId" not in result["result"]["value"]:
                    print(f"Akamai challenge passed (Attempt {attempt + 1}).")
                    break
                print(f"[Attempt {attempt + 1}] Challenge still present; retrying in 3s.")
                time.sleep(3)

            print("Waiting an extra 5 seconds for initial load...")
            time.sleep(5)

            # === NEW: Wait for product-container via XPath ===
            print("Waiting for //div[@class='product-container'] to appear...")
            start = time.time()
            timeout = 60
            xpath_check = (
                "document.evaluate(\"//div[@class='product-container']\", "
                "document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue != null"
            )
            while True:
                found = tab.Runtime.evaluate(expression=xpath_check)["result"]["value"]
                if found:
                    print("✅ Element found!")
                    break
                if time.time() - start > timeout:
                    raise Exception(f"Timeout waiting for //div[@class='product-container']")
                time.sleep(1)

            result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
            content = result["result"]["value"]
            print("Final HTML retrieved; length:", len(content))

            filepath = self.save_page_content(content=content, prefix="bypass")
            print("Page content saved to:", filepath)

            raw_cookies = tab.Network.getCookies()['cookies']
            cookie_dict = {c['name']: c['value'] for c in raw_cookies}
            print("Cookies retrieved:", bool(cookie_dict))
            
            if not self.captured_headers:
                raise Exception("No headers were captured from Chrome")
            
            headers_list = [f"-H '{k}: {v}'" for k, v in self.captured_headers.items()]
            headers_curl = " ".join(headers_list)
            cookies_curl = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])

            curl_command = (
                f"curl -x {self.proxy_pool} '{self.url}' --cookie '{cookies_curl}' "
                f"{headers_curl} --compressed -o ~/louisvuitton_test.html"
            )
            print("\nGenerated cURL Command:")
            print(curl_command)

            assert all([content, cookie_dict, curl_command])
            return content, cookie_dict, self.captured_headers, curl_command

        except Exception as e:
            print(f"Error during operation: {e}")
            raise

        finally:
            print("Cleaning up...")
            self.cleanup()