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
            # user_data_dir=f"sasha_{task_id}",
            user_data_dir="sasha",
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

                request_url = request.get("url", "")

                if request_url == self.url: 
                    headers = request.get("headers", {})
                    captured_headers.update(headers)

                    print('Complete Request')
                    print(json.dumps(request, indent=4))

            def extra_info_intercept(**params):

                headers = params.get("headers", {})

                authority = headers.get(":authority", "")
                path = headers.get(":path", "")
                scheme = headers.get(":scheme", "")

                if authority and path and scheme:
                    full_url = f"{scheme}://{authority}{path}"
                    print(f"Reconstructed Full URL: {full_url}")
                
                if full_url == self.url:  
                    captured_headers.update(headers)
                    
                    print('Complete Params')
                    print(json.dumps(params, indent=4))

            tab.Network.requestWillBeSent = request_intercept
            tab.Network.requestWillBeSentExtraInfo = extra_info_intercept

            # print(f"Navigating to URL: https://api.ipify.org")
            # tab.Page.navigate(url="https://api.ipify.org")
            # time.sleep(5)

            print(f"Navigating to URL: {self.url}")
            tab.Page.navigate(url=self.url)
            
            print('Waiting 5 seconds')
            time.sleep(5)

            # Check for captcha presence on the page
            print('Checking for captcha...')
            captcha_check_start = time.time()
            captcha_timeout = 100  # 100 seconds timeout
            
            while time.time() - captcha_check_start < captcha_timeout:
                # Execute JavaScript to check for common captcha elements - simplified to return true/false
                result = tab.Runtime.evaluate(
                    expression="""
                    (function() {
                        // Check for Google reCAPTCHA
                        const recaptcha = document.querySelector('.g-recaptcha') || 
                                         document.querySelector('iframe[src*="recaptcha"]') ||
                                         document.querySelector('iframe[src*="captcha"]');
                        
                        // Check for common captcha text indicators
                        const captchaText = document.body.innerText.toLowerCase().includes('captcha') ||
                                           document.body.innerText.toLowerCase().includes('robot check') ||
                                           document.body.innerText.toLowerCase().includes('security check');
                        
                        // Check for typical captcha input elements
                        const captchaInput = document.querySelector('input[name*="captcha"]') ||
                                            document.querySelector('img[alt*="captcha"]');
                        
                        return !!(recaptcha || captchaText || captchaInput);
                    })();
                    """
                )
                
                has_captcha = result.get("result", {}).get("value", False)
                
                if has_captcha:
                    print("Captcha detected! Waiting...")
                    time.sleep(1)  # Check again in 1 second
                else:
                    print("No captcha detected, proceeding.")
                    break
            
            print('Waiting done')
            # Waiting after Captcha solved
            time.sleep(5)

            # Fetch the cookies
            cookies_list = tab.Network.getCookies()['cookies']
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies_list}
            print("Cookies Retrieved:", cookie_dict)

            # Fetch the headers
            headers_dict = {k: v for k, v in captured_headers.items() if k.lower() not in ['cookie'] and not k.startswith(':')}

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
            headers_curl = " ".join([f"-H '{k}: {v}'" for k, v in headers_dict.items()])
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