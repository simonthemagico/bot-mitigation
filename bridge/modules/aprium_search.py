import time
import json
import websocket
import pychrome
from urllib.parse import urlparse, unquote
from pychrome.tab import Tab
from .base import BaseBypass

# SILENCE pychrome’s background errors
_orig_recv = Tab._recv_loop

def _safe_recv_loop(self):
    try:
        _orig_recv(self)
    except (websocket._exceptions.WebSocketConnectionClosedException,
            json.decoder.JSONDecodeError):
        return

Tab._recv_loop = _safe_recv_loop


class ApriumSearchByPass(BaseBypass):
    def __init__(self, proxy_pool: str, url: str, task_id: str, headless: bool = True):
        if not proxy_pool.startswith(("http://", "https://")):
            proxy_pool = "http://" + proxy_pool
        super().__init__(proxy_pool, url, task_id, headless, user_data_dir=f"andrew_{task_id}")
        self.initialize()

    def bypass(self):
        tab = None
        try:
            print("Starting Proxy Server...")
            self.proxy_server.start_proxy_server()

            print("Starting Chrome Browser...")
            self.chrome.create_chrome()
            time.sleep(5)

            browser = pychrome.Browser(url=f"http://localhost:{self.chrome_port}")
            print("Connected to Chrome Remote Debugger.")

            # Create & start fresh tab
            tab = browser.new_tab()
            tab.start()
            tab.Network.enable()
            tab.Page.enable()

            self.requests = []
            def capture_request(**kwargs):
                req = kwargs.get("request")
                if req:
                    self.requests.append(req)
            tab.Network.requestWillBeSent = capture_request

            print("Navigating to about:blank…")
            tab.Page.navigate(url="about:blank")
            time.sleep(2)

            print(f"Navigating to target URL: {self.url}")
            tab.Page.navigate(url=self.url)
            time.sleep(5)

            print("Waiting for product-container…")
            start, timeout = time.time(), 60
            xpath = (
                "document.evaluate(\"//div[@class='product-container']\"," +
                " document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue != null"
            )
            while time.time() - start < timeout:
                if tab.Runtime.evaluate(expression=xpath)["result"]["value"]:
                    print("✅ Element found!")
                    break
                time.sleep(1)
            else:
                raise Exception("Timeout waiting for product-container")

            # Pick last request matching domain+path (decoded)
            parsed_target = urlparse(self.url)
            target_netloc = parsed_target.netloc
            target_path = unquote(parsed_target.path)

            matches = []
            for req in self.requests:
                parsed = urlparse(req.get("url", ""))
                if parsed.netloc == target_netloc and unquote(parsed.path) == target_path:
                    matches.append(req)

            if not matches:
                raise Exception("No matching request captured")

            last_req = matches[-1]
            self.captured_headers = last_req.get("headers", {})

            content = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")["result"]["value"]
            filepath = self.save_page_content(content=content, prefix="bypass")
            raw_cookies = tab.Network.getCookies()['cookies']
            cookies = {c['name']: c['value'] for c in raw_cookies}

            headers_curl = " ".join(f"-H '{k}: {v}'" for k, v in self.captured_headers.items())
            cookies_curl = "; ".join(f"{k}={v}" for k, v in cookies.items())
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
