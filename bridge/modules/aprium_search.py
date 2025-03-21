import time
import threading
import pychrome
import os
from .base import BaseBypass

class ApriumSearchByPass(BaseBypass):
    def __init__(self, proxy_pool: str, url: str, task_id: str, headless: bool = True):
        if not proxy_pool.startswith(("http://", "https://")):
            proxy_pool = "http://" + proxy_pool
        super().__init__(proxy_pool, url, task_id, headless, user_data_dir=f"andrew_{task_id}")
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
            tab.Network.setCacheDisabled(cacheDisabled=True)

            # ─── HEADER CAPTURE SETUP ─────────────────────────────────────────
            header_event = threading.Event()
            self.captured_request_headers = {}
            self.captured_response_headers = {}

            def on_request(**kwargs):
                req = kwargs.get("request", {})
                if req.get("url") == self.url:
                    self.captured_request_headers.update(req.get("headers", {}))
                    header_event.set()

            def on_response(**kwargs):
                resp = kwargs.get("response", {})
                if resp.get("url") == self.url:
                    self.captured_response_headers.update(resp.get("headers", {}))
                    status = resp.get("status", 0)
                    if status >= 400:
                        raise Exception(f"HTTP error {status} for {self.url}")
                    header_event.set()

            tab.Network.requestWillBeSent = on_request
            tab.Network.responseReceived = on_response

            # ─── NAVIGATION ────────────────────────────────────────────────────
            print(f"Navigating to URL: {self.url}")
            tab.Page.navigate(url=self.url)

            # ─── WAIT FOR HEADER EVENT (10s timeout) ───────────────────────────
            if not header_event.wait(timeout=10):
                raise Exception(f"No request or response headers captured for {self.url} within 10 seconds")

            self.captured_headers = {**self.captured_request_headers, **self.captured_response_headers}
            if not self.captured_headers:
                raise Exception(f"Captured event but no header data for {self.url}")

            # ─── WAIT FOR PRODUCT-CONTAINER (60s timeout) ──────────────────────
            print("Waiting for //div[@class='product-container'] …")
            start = time.time()
            while time.time() - start < 60:
                found = tab.Runtime.evaluate(
                    expression="!!document.evaluate(\"//div[@class='product-container']\", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue"
                )["result"]["value"]
                if found:
                    break
                time.sleep(1)
            else:
                raise Exception("Timeout waiting for product-container")

            content = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")["result"]["value"]
            print(f"Page content retrieved (length: {len(content)})")

            filepath = self.save_page_content(content=content, prefix="bypass")
            print("Saved page content to:", filepath)

            cookies = {c["name"]: c["value"] for c in tab.Network.getCookies()["cookies"]}
            print("Cookies retrieved:", bool(cookies))

            # ─── BUILD cURL COMMAND ────────────────────────────────────────────
            headers_curl = " ".join([f"-H '{k}: {v}'" for k, v in self.captured_headers.items()])
            cookies_curl = "; ".join([f"{k}={v}" for k, v in cookies.items()])
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
            print("Cleaning up...")
            self.cleanup()