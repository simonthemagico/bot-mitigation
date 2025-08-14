from .base import BaseBypass
import time
import pychrome
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import re
import json

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

    def _base_url(self) -> str:
        """Ex: self.url=https://www.yelp.fr/search?... -> https://www.yelp.fr"""
        p = urlparse(self.url)
        return f"https://{p.netloc}"
        
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
        
    def _canon(self, u: str) -> str:
        """https://yelp.com == https://yelp.com/
        >>> True
        """
        if not u:
            return ""
        try:
            p = urlparse(u)
        except Exception:
            return u

        scheme = (p.scheme or "https").lower()
        host = (p.hostname or "").lower()
        port = p.port

        if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
            netloc = f"{host}:{port}"
        else:
            netloc = host

        path = p.path or "/"
        if path != "/":
            path = path.rstrip("/")

        query = urlencode(sorted(parse_qsl(p.query, keep_blank_values=True)))

        return urlunparse((scheme, netloc, path, "", query, ""))

    def bypass(self):
        browser = None
        tab = None

        captured_headers = {}

        source_url = self.url
        target_url = self._base_url()

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
                if self._canon(request_url) == self._canon(target_url): 
                    print(f"Request intercepted: {request_url}")
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
                    
                if self._canon(full_url) == self._canon(target_url):  
                    print(f"Extra info intercepted: {full_url}")
                    captured_headers.update(headers)
                    # print('Complete Params')
                    # print(json.dumps(params, indent=4))

            tab.Network.requestWillBeSent = request_intercept
            tab.Network.requestWillBeSentExtraInfo = extra_info_intercept

            # print(f"Navigating to URL: https://api.ipify.org")
            # tab.Page.navigate(url="https://api.ipify.org")
            # time.sleep(5)

            root_url = self._base_url()
            print(f"Navigating to URL: {root_url} ——— from {self.url}")
            tab.Page.navigate(url=root_url, _timeout=10)
            time.sleep(5)
            
            for attempt in range(30):
                if self._eval_bool(tab, JS_ERROR):
                    # input('error?')
                    raise RuntimeError("DataDome detected (captcha/interstitial)")
                if self._eval_bool(tab, JS_SUCCESS):
                    print('Success 🎉')
                    break

                tab.wait(1)
                if (attempt + 1) % 5 == 0:
                    print(f"Waiting for task {self.task_id} completion... Attempt {attempt + 1}/30")

            else: 
                raise TimeoutError("No 200 OK main Yelp document within 30s")
            
            target_host = self._host(self.url)
            cookies_list = tab.Network.getCookies()['cookies']
            
            cookie_dict = {
                c['name']: c['value'] 
                for c in cookies_list
            }

            headers_dict = {
                k: v for k, v in captured_headers.items() 
                if k.lower() not in ['cookie', 'accept-encoding'] and not k.startswith(':')
            }

            # Récupération du HTML
            html = self._get_html(tab)
            filepath = self.save_page_content(html, prefix="yelp_bypass")

            # Format CURL
            cookies_curl = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            headers_curl = " ".join([f"-H '{k}: {v}'" for k, v in headers_dict.items()])
            curl_command = f"curl -x {self.proxy_pool} '{self.url}' --cookie '{cookies_curl}' {headers_curl} -o ~/yelp_test.html"

            return html, cookie_dict, headers_dict, curl_command

        except Exception as e:
            print(f"Error during operation: {e}")
            raise e

        finally:
            print("Cleaning up...")
            self.cleanup()
            
