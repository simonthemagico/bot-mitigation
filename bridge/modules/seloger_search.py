from .base import BaseBypass
import time
import pychrome
import json

class SeLogerSearchBypass(BaseBypass):
    def __init__(self, proxy_pool: str, url: str, task_id: str, headless: bool = True):
        super().__init__(
            proxy_pool,
            url,
            task_id,
            headless,
            user_data_dir=f"sasha_{task_id}",
            extension_path="extensions/capsolver"
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

            captured_headers = {}
            
            def request_intercept(request, **kwargs):
                """Callback function to capture headers safely."""
                headers = request.get("headers", {})
                captured_headers.update(headers)
            
            tab.Network.requestWillBeSent = request_intercept

            print(f"Navigating to URL: {self.url}")
            tab.Page.navigate(url=self.url)
            time.sleep(15)

            input('next1?')

            # Scroll down to the pagination section
            print(f"Starting scrolling...")
            pagination_exists = tab.Runtime.evaluate(expression="document.querySelector('[data-testid=\"gsl.uilib.Paging\"]') !== null")
            if pagination_exists.get('result', {}).get('value', False):
                tab.Runtime.evaluate(expression="document.querySelector('[data-testid=\"gsl.uilib.Paging\"]').scrollIntoView({behavior: 'smooth', block: 'center'})")
                time.sleep(3)

            input('next2?')

            # Check if the next page button exists and click it
            next_page_button = tab.Runtime.evaluate(expression="document.querySelector('[data-testid=\"gsl.uilib.Paging.nextButton\"]') !== null")
            if next_page_button.get("result", {}).get("value", False):
                print("Clicking next page...")
                tab.Runtime.evaluate(expression="document.querySelector('[data-testid=\"gsl.uilib.Paging.nextButton\"]').click()")
                time.sleep(5)

            input('next3?')
            
            print("Fetching cookies...")
            cookies_list = tab.Network.getCookies()["cookies"]
            cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies_list}

            print("Fetching headers...")
            headers_dict = {k: v for k, v in captured_headers.items() if k.lower() not in ['cookie']}

            print("Fetching page content...")
            result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
            page_content = result.get("result", {}).get("value", "")

            # Save content
            self.save_page_content(page_content, prefix="seloger")

            # Format cURL command
            cookies_curl = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            headers_curl = " ".join([f"-H '{k}: {v}'" for k, v in captured_headers.items() if k.lower() not in ['cookie']])
            curl_command = f"curl -x {self.proxy_pool} '{self.url}' --cookie '{cookies_curl}' {headers_curl} -o ~/seloger.html"

            print("\nGenerated cURL Command:")
            print(curl_command)

            return page_content, cookie_dict, headers_dict, curl_command
        
        except Exception as e:
            print(f"Error during operation: {e}")
            raise e

        finally:
            print("Cleaning up...")
            self.cleanup()
