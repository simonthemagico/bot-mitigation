from .base import BaseBypass
import time
import pychrome
from urllib.parse import urlparse
import re

JS_SUCCESS = r"""
(() => {
    const hasRRP = !!document.querySelector('script[data-id="react-root-props"]');
    const hasReactRoot = !!document.querySelector('yelp-react-root');
    const hasApollo = !!document.querySelector('script[data-apollo-state]');
    const hasHeaderSearch = !!document.querySelector('form\#header_find_form[role="search"]');
    const hasOgUrl = !!document.querySelector('meta[property="og:url"][content*="yelp.com"]');
    const score = [hasRRP, hasReactRoot, hasApollo, hasHeaderSearch, hasOgUrl].filter(Boolean).length;
    return score >= 3;
})()
"""

JS_ERROR = r"""
(() => {
    if (document.querySelector('iframe[src*="captcha-delivery.com"]')) return true;
    if (document.querySelector('script[src*="ct.captcha-delivery.com"]')) return true;
    if (document.querySelector('iframe[title*="DataDome"]')) return true;
    // script inline var dd={...}
    const dd = Array.from(document.scripts).some(s => s.textContent && s.textContent.includes("var dd="));
    return dd;
})()
"""

class YelpSearchBypass(BaseBypass):
    def __init__(self, proxy_pool: str, url: str, task_id: str, headless: bool = True):
        super().__init__(
            proxy_pool, 
            url, 
            task_id, 
            headless, 
            user_data_dir=f"yelp_{task_id}",
            extension_path="extensions/capsolver", 
            disable_images=False
        )
        self.initialize()

    def _host(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return ""
        
    def _eval_bool(self, tab, js: str) -> bool:
        try:
            r = tab.Runtime.evaluate(expression=js)
            return bool(r.get("result", {}).get("value", False))
        except Exception:
            return False

    def _get_html(self, tab) -> str:
        try:
            return tab.Runtime.evaluate(
                expression="document.documentElement.outerHTML"
            ).get("result", {}).get("value", "") or ""
        except Exception:
            return "" 

    def bypass(self):
        browser = None
        tab = None

        captured_headers = {}

        try:
            print("Starting Proxy Server...")
            self.proxy_server.start_proxy_server()
            print("Starting Chrome Browser...")
            self.chrome.create_chrome()
            time.sleep(1)

            browser = pychrome.Browser(url=f"http://localhost:{self.chrome_port}")
            print("Connected to Chrome Remote Debugger.")

            version_info = browser.version()
            print("Browser Version:", version_info['Browser'])

            # Tab management
            tab = browser.list_tab(timeout=5)[0] if browser.list_tab(timeout=5) else browser.new_tab()
            tab.start()
            print("Tab started.")

            tab.Network.enable()
            tab.Page.enable()

            def request_intercept(request, **kwargs):
                request_url = request.get("url", "")
                if request_url == self.url: 
                    headers = request.get("headers", {})
                    captured_headers.update(headers)
                    # print('Complete Request')
                    # print(json.dumps(request, indent=4))

            def extra_info_intercept(**params):
                headers = params.get("headers", {})
                authority = headers.get(":authority", "")
                path = headers.get(":path", "")
                scheme = headers.get(":scheme", "")
                full_url = ""
                if authority and path and scheme:
                    full_url = f"{scheme}://{authority}{path}"
                    # print(f"Reconstructed Full URL: {full_url}")
                if full_url == self.url:  
                    captured_headers.update(headers)
                    # print('Complete Params')
                    # print(json.dumps(params, indent=4))

            tab.Network.requestWillBeSent = request_intercept
            tab.Network.requestWillBeSentExtraInfo = extra_info_intercept
            
            tab.Network.requestWillBeSent = request_intercept
            tab.Network.requestWillBeSentExtraInfo = extra_info_intercept

            print(f"Navigating to URL: https://api.ipify.org")
            tab.Page.navigate(url="https://api.ipify.org")
            time.sleep(5)

            print(f"Navigating to URL: {self.url}")
            tab.Page.navigate(url=self.url, _timeout=10)
            
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                tab.wait(1)
                if self._eval_bool(tab, JS_ERROR):
                    input('error?')
                    raise RuntimeError("DataDome detected (captcha/interstitial)")
                if self._eval_bool(tab, JS_SUCCESS):
                    input('success?')
                    break

            else: 
                raise TimeoutError("No 200 OK main Yelp document within 30s")
            
            target_host = self._host(self.url)
            cookies_list = tab.Network.getCookies()['cookies']

            def _cookie_matches_host(cookie_domain: str, host: str) -> bool:
                if not cookie_domain or not host:
                    return False
                cd = cookie_domain.lstrip('.').lower()
                h = host.lower()
                return h == cd or h.endswith('.' + cd)
            
            cookie_dict = {
                c['name']: c['value'] 
                for c in cookies_list
                if _cookie_matches_host(c.get('domain', ''), target_host)
            }

            # Récupération du HTML
            html = self._get_html(tab)
            filepath = self.save_page_content(html, prefix="yelp_bypass")

            # Format CURL
            cookies_curl = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            curl_command = f"curl -x {self.proxy_pool} '{self.url}' --cookie '{cookies_curl}' -o ~/yelp_test.html"

            input('?')

            return html, cookie_dict, {}, curl_command

        except Exception as e:
            print(f"Error during operation: {e}")
            raise e

        finally:
            print("Cleaning up...")
            self.cleanup()
            
