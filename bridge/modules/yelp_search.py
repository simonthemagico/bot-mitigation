from .base import BaseBypass
import time
import pychrome

class YelpSearchBypass(BaseBypass):
    def __init__(self, proxy_pool: str, url: str, task_id: str, headless: bool = True):
        super().__init__(
            proxy_pool, 
            url, 
            task_id, 
            headless, 
            user_data_dir=f"yelp_{task_id}",
            extension_path="extensions/capsolver",  # ou ton extension spéciale Yelp
            disable_images=False
        )
        self.initialize()

    def bypass(self):
        try:
            print("Starting Proxy Server...")
            self.proxy_server.start_proxy_server()

            print("Starting Chrome Browser...")
            self.chrome.create_chrome()

            time.sleep(1)

            browser = pychrome.Browser(url=f"http://localhost:{self.chrome_port}")
            tab = browser.new_tab()
            tab.start()
            tab.Network.enable()
            tab.Page.enable()

            print(f"Navigating to URL: {self.url}")
            tab.Page.navigate(url=self.url)
            
            # Attente + détection DataDome
            time.sleep(3)
            start_time = time.time()
            while time.time() - start_time < 100:
                result = tab.Runtime.evaluate(expression="""
                    (() => {
                        const text = document.body.innerText || "";
                        return text.includes("Please verify you are a human") || text.includes("DataDome");
                    })();
                """)
                if not result.get("result", {}).get("value", False):
                    break
                print("Captcha/DataDome detected, waiting...")
                time.sleep(2)

            print("No captcha detected or solved. Fetching cookies...")
            cookies_list = tab.Network.getCookies()['cookies']
            cookie_dict = {c['name']: c['value'] for c in cookies_list}

            # Récupération du HTML
            html = tab.Runtime.evaluate(expression="document.documentElement.outerHTML").get("result", {}).get("value", "")
            filepath = self.save_page_content(html, prefix="yelp_bypass")

            # Format CURL
            cookies_curl = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            curl_command = f"curl -x {self.proxy_pool} '{self.url}' --cookie '{cookies_curl}' -o ~/yelp_test.html"

            return html, cookie_dict, {}, curl_command

        except Exception as e:
            print(f"Error during operation: {e}")
            raise e

        finally:
            print("Cleaning up...")
            self.cleanup()
            
