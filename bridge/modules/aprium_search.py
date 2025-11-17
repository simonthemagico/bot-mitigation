import time
import json
import pychrome
from urllib.parse import urlparse, unquote

from .base import BaseBypass
from utils import pychrome_safe  # noqa: F401  (ensures monkeypatch is applied)


class ApriumSearchByPass(BaseBypass):
    def __init__(self, proxy_pool: str, url: str, task_id: str, headless: bool = True):
        if not proxy_pool.startswith(("http://", "https://")):
            proxy_pool = "http://" + proxy_pool
        super().__init__(proxy_pool, url, task_id, headless, user_data_dir=f"andrew_{task_id}")
        self.initialize()

    def bypass(self):
        tab = None
        self.error_404 = False

        try:
            print("Starting Proxy Server...")
            self.proxy_server.start_proxy_server()

            print("Starting Chrome Browser...")
            self.chrome.create_chrome()
            time.sleep(5)

            browser = pychrome.Browser(url=f"http://localhost:{self.chrome_port}")
            print("Connected to Chrome Remote Debugger.")

            tab = browser.new_tab()
            tab.start()
            tab.Network.enable()
            tab.Page.enable()

            self.requests = []

            def capture_request(**kwargs):
                req = kwargs.get("request")
                if req:
                    self.requests.append(req)

            def capture_response(**kwargs):
                resp = kwargs.get("response")
                url = resp.get("url", "")
                if url.rstrip("/").endswith("/404"):
                    self.error_404 = True

            tab.Network.requestWillBeSent = capture_request
            tab.Network.responseReceived = capture_response

            print("Navigating to about:blank…")
            tab.Page.navigate(url="about:blank")
            time.sleep(2)

            print(f"Navigating to target URL: {self.url}")
            tab.Page.navigate(url=self.url)

            start, timeout = time.time(), 60
            xpath = (
                "document.evaluate(\"//div[@class='product-container']\","
                " document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue != null"
            )

            while time.time() - start < timeout:
                if self.error_404:
                    raise Exception("error 404 page")
                if tab.Runtime.evaluate(expression=xpath)["result"]["value"]:
                    print("✅ Element found!")
                    break
                time.sleep(1)
            else:
                raise Exception("Timeout waiting for product-container")

            # Filter last matching request
            parsed_target = urlparse(self.url)
            matches = [
                r for r in self.requests
                if urlparse(r.get("url","")).netloc == parsed_target.netloc
                and unquote(urlparse(r.get("url","")).path) == unquote(parsed_target.path)
            ]
            if not matches:
                raise Exception("No matching request captured")
            last_req = matches[-1]

            if last_req.get("url","").rstrip("/").endswith("/404"):
                raise Exception("error 404 page")

            self.captured_headers = last_req.get("headers", {})
            content = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")["result"]["value"]
            raw_cookies = tab.Network.getCookies()['cookies']
            cookies = {c['name']: c['value'] for c in raw_cookies}

            headers_curl = " ".join(f"-H '{k}: {v}'" for k,v in self.captured_headers.items())
            cookies_curl = "; ".join(f"{k}={v}" for k,v in cookies.items())
            curl = (
                f"curl -x {self.proxy_pool} '{self.url}' --cookie '{cookies_curl}' "
                f"{headers_curl} --compressed -o ~/louisvuitton_test.html"
            )
            print("\nGenerated cURL Command:\n", curl)

            return content, cookies, self.captured_headers, curl

        except Exception as e:
            print("Error during operation:", e)
            raise

        finally:
            print("Cleaning up…")
            if tab:
                try:
                    tab.stop()
                    browser.close_tab(tab)
                except Exception:
                    pass
            self.cleanup()