import time
import pychrome
from .base import BaseBypass

class LouisVuittonSearchByPass(BaseBypass):
    def __init__(self, proxy_pool: str, url: str, task_id: str, headless: bool = True):
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
            # Start your local proxy server that manages the proxies
            self.proxy_server.start_proxy_server()

            print("Starting Chrome Browser...")
            # Launch Chrome via your self.chrome instance (defined in BaseBypass).
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

            # We’ll capture request headers from the main document request
            captured_headers = {}
            def request_intercept(request, **kwargs):
                # This fires whenever a request is about to be sent
                # For "Playwright-like" logic, we only really care if it's the main document.
                # But you could store all if you want, filtering by request['type'] or URL.
                # Check request.get("type") or request["request"]["url"] as needed.
                hdrs = request.get("request", {}).get("headers", {})
                # We might store them globally
                for k, v in hdrs.items():
                    captured_headers[k] = v

            tab.Network.requestWillBeSent = request_intercept

            print(f"Navigating first to a quick IP check or blank page if needed.")
            tab.Page.navigate(url="about:blank")
            time.sleep(2)

            print(f"Navigating to URL: {self.url}")
            tab.Page.navigate(url=self.url)

            # Now replicate the "Akamai challenge wait loop"
            max_checks = 5
            for attempt in range(max_checks):
                # Evaluate the DOM
                result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
                page_content = result.get("result", {}).get("value", "")

                # If no 'var chlgeId', we assume challenge is passed
                if "var chlgeId" not in page_content:
                    print(f"Akamai challenge seems passed (Attempt {attempt + 1}).")
                    break

                print(f"[Attempt {attempt + 1}] Challenge present; waiting 3s to reload.")
                time.sleep(3)

            # By now, either we passed or gave up after max checks
            # We'll retrieve final HTML again
            final_html_eval = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
            final_html = final_html_eval.get("result", {}).get("value", "")

            # Grab cookies
            raw_cookies = tab.Network.getCookies().get('cookies', [])
            cookie_dict = {c['name']: c['value'] for c in raw_cookies}

            # Filter or keep them all. 
            # If you only want certain cookies like in your Playwright script, you can do:
            # valid_names = ['bm_ss', '_abck', ...]
            # cookie_dict = {n: v for n, v in cookie_dict.items() if n in valid_names}

            # Filter out 'cookie' from captured_headers if you want
            filtered_headers = {
                k: v for k, v in captured_headers.items()
                if k.lower() not in ['cookie']
            }

            # Done. Return final HTML, cookies, and captured headers
            print("Cookies:", cookie_dict)
            print("Captured Headers:", filtered_headers)

            return final_html, cookie_dict, filtered_headers

        except Exception as e:
            print(f"Error during operation: {e}")
            raise e

        finally:
            print("Cleaning up...")
            self.cleanup()