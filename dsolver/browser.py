import time
import requests
import pychrome
from urllib.parse import urlparse
from typing import Tuple

from config import API_PORT

def get_new_tab(browser):
    tab = browser.new_tab()
    tab.start()
    tab.call_method("Network.enable")
    tab.call_method("Page.enable")
    tab.call_method("Network.clearBrowserCookies")
    return tab

def create_browser_tab(url: str, cid: str, port: int) -> Tuple[pychrome.Tab, pychrome.Browser]:
    url_obj = urlparse(url)
    for _ in range(3):
        try:
            requests.get(f"http://127.0.0.1:{port}/json")
            break
        except Exception as e:
            print(e)
            time.sleep(1)
    browser = pychrome.Browser(url=f"http://127.0.0.1:{port}")
    
    if 'captcha-delivery' not in url_obj.hostname:
        tab = get_new_tab(browser)
        render_url = f'http://localhost:{API_PORT}/render?hash={cid}'
        tab.call_method("Page.navigate", url=render_url, _timeout=5)
        tab.wait(2)
        tab.stop()
        browser.close_tab(tab)
        
    tab = get_new_tab(browser)
    tab.call_method("Network.setCookie", name='datadome', value=cid, 
                   domain=url_obj.hostname.replace('www', ''), path='/', secure=True)
    tab.call_method("Page.navigate", url=url, _timeout=15)
    tab.call_method("Runtime.evaluate", expression=f"localStorage.setItem('hash', '{cid}')")
    tab.wait(5)
    return tab, browser
