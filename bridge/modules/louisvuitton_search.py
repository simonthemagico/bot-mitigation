import time
import pychrome
import os
from functools import wraps
from .base import BaseBypass

def retry(ExceptionToCheck, tries=4, delay=3, backoff=2):
    """
    A simple retry decorator.
    """
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    print(f"{e}, Retrying in {mdelay} seconds...")
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry
    return deco_retry

class LouisVuittonSearchByPass(BaseBypass):
    def __init__(
            self, 
            proxy_pool: str, 
            url: str, 
            task_id: str, 
            headless: bool = True
        ):
        super().__init__(
            proxy_pool,
            url,
            task_id,
            headless,
            user_data_dir=f"andrew_{task_id}", 
            disable_http2=True, 
            disable_images=False
        )
        self.initialize()

    @retry(Exception, tries=4, delay=3, backoff=2)
    def get_outer_html(self, tab):
        """
        Evaluates the page’s outerHTML. If not available, raises an Exception
        so that the retry mechanism can try again.
        """
        result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
        if "result" not in result or "value" not in result["result"]:
            raise Exception("outerHTML not available yet")
        return result["result"]["value"]

    def bypass(self):
        try:
            print("Starting Proxy Server...")
            self.proxy_server.start_proxy_server()

            print("Starting Chrome Browser...")
            self.chrome.create_chrome()
            
            time.sleep(1)

            # Connect to Chrome DevTools
            assert self.chrome_port
            browser = pychrome.Browser(url=f"http://localhost:{self.chrome_port}")
            print("Connected to Chrome Remote Debugger.")

            version_info = browser.version()
            print("Browser Version:", version_info['Browser'])

            # Grab or create a new tab
            tab = browser.list_tab()[0] if browser.list_tab() else browser.new_tab()
            tab.start()
            print("Tab started.")

            # Enable necessary domains
            tab.Network.enable()
            tab.Page.enable()

            captured_headers = {}

            def request_intercept(request, **kwargs):

                request_url = request.get("url", "")

                if request_url == self.url: 
                    headers = request.get("headers", {})
                    captured_headers.update(headers)

                    print('Complete Request')
                    # print(json.dumps(request, indent=4))

            def extra_info_intercept(**params):

                headers = params.get("headers", {})

                authority = headers.get(":authority", "")
                path = headers.get(":path", "")
                scheme = headers.get(":scheme", "")

                if authority and path and scheme:
                    full_url = f"{scheme}://{authority}{path}"
                    # print(f"Reconstructed Full URL: {full_url}")
                
                if full_url == self.url:  
                    captured_headers.update(headers)
                    
                    print('Complete Params')
                    # print(json.dumps(params, indent=4))

            tab.Network.requestWillBeSent = request_intercept
            tab.Network.requestWillBeSentExtraInfo = extra_info_intercept

            print(f"Navigating to URL: https://api.ipify.org")
            tab.Page.navigate(url="https://api.ipify.org")
            time.sleep(5)

            input("?")

            print(f"Navigating to URL: {self.url}")
            tab.Page.navigate(url=self.url)

            print('Waiting 5 seconds')
            time.sleep(5)

            # Wait loop to check for Akamai challenge
            max_checks = 5
            for attempt in range(max_checks):
                page_content = self.get_outer_html(tab)
                print(f"Attempt {attempt+1}: Page content length is {len(page_content)}")
                if "var chlgeId" not in page_content:
                    print(f"Akamai challenge seems passed (Attempt {attempt + 1}).")
                    break
                print(f"[Attempt {attempt + 1}] Challenge detected; waiting 3 seconds before retrying.")
                time.sleep(3)

            print("Waiting an extra 5 seconds to ensure full page load...")
            time.sleep(5)

            # Retrieve final HTML using our retry helper
            content = self.get_outer_html(tab)
            print("Final HTML retrieved; length:", len(content))

            # Save final HTML to file if needed
            filepath = self.save_page_content(content=content, prefix="bypass")
            print("Page content saved to:", filepath)

            # Retrieve cookies from the network
            raw_cookies = tab.Network.getCookies()['cookies']
            print(f"Raw cookies: {raw_cookies}")
            cookie_dict = {c['name']: c['value'] for c in raw_cookies}
            print("Cookies retrieved:", bool(cookie_dict))

            # Generate a cURL command with cookies and headers
            cookies_curl = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            headers_list = [f"-H '{k}: {v}'" for k, v in captured_headers.items()]
            headers_curl = " ".join(headers_list)
            curl_command = (
                f"curl -x {self.proxy_pool} '{self.url}' --cookie '{cookies_curl}' "
                f"{headers_curl} --compressed -o ~/louisvuitton_test.html"
            )
            print("\nGenerated cURL Command:")
            print(curl_command)

            assert all([content, cookie_dict, curl_command])
            return content, cookie_dict, captured_headers, curl_command

        except Exception as e:
            print(f"Error during operation: {e}")
            raise e

        finally:
            print("Cleaning up...")
            self.cleanup()