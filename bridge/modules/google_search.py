from .base import BaseBypass

import time, os, base64, tempfile, json, requests
from pathlib import Path
from openai import OpenAI
import pychrome
import json
import os
import base64

from utils import pychrome_safe  # noqa: F401  (ensures monkeypatch is applied)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")


def ocr_json_bytes(img_bytes: bytes, model: str = "gpt-4o-mini") -> str:
    client_ocr = OpenAI(api_key=OPENAI_KEY)
    """OCR via OpenAI Vision → renvoie le texte."""
    b64 = base64.b64encode(img_bytes).decode()
    r = client_ocr.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text",
                 "text": "Lis exactement le texte de l'image et réponds uniquement "
                         "par un JSON {\"value\":\"<texte>\"}"},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}}
            ]
        }],
        response_format={"type": "json_object"},
        max_tokens=16,
    )
    return json.loads(r.choices[0].message.content)["value"]


class GoogleSearchBypass(BaseBypass):

    def __init__(self, proxy_pool: str, url: str, task_id: str, headless: bool = True):
        super().__init__(
            proxy_pool,
            url,
            task_id,
            headless,
            user_data_dir=f"google_search_{task_id}",
            # Important: point directly to the unpacked Capsolver extension root
            # (the version directory which contains manifest.json).
            extension_path="extensions/pgojnojmmhpofjgdmaebadhbocahppod/1.17.0_0",
            disable_images=False
        )
        self.initialize()

    JS_DETECT = """
        (function(){
            if (document.querySelector('.g-recaptcha, iframe[src*="recaptcha"]'))
                return 'recaptcha';
            if (document.querySelector('img[src*="/sorry/image"]'))
                return 'image';
            return 'none';
        })();
    """

    def bypass(self):
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

        captured_headers = {}

        def request_intercept(request, **kwargs):

            request_url = request.get("url", "")

            if request_url == self.url:
                headers = request.get("headers", {})
                captured_headers.update(headers)

                print('Complete Request')
                # print(json.dumps(request, indent=4))

        def extra_info_intercept(**params):

            headers = params.get("headers", {})

            authority = headers.get(":authority", "")
            path = headers.get(":path", "")
            scheme = headers.get(":scheme", "")

            if authority and path and scheme:
                full_url = f"{scheme}://{authority}{path}"
                # print(f"Reconstructed Full URL: {full_url}")

            if full_url == self.url:
                captured_headers.update(headers)

                print('Complete Params')
                # print(json.dumps(params, indent=4))

        tab.Network.requestWillBeSent = request_intercept
        tab.Network.requestWillBeSentExtraInfo = extra_info_intercept

        def accept_fullpage_consent_if_present():
            """
            Detect the new full-page consent screen (consent.google.com) and click the
            “Accept” button automatically. Returns True if consent flow was detected
            and completed, False otherwise.
            """
            check_script = """
                (function() {
                    const response = { detected: false, clicked: false };
                    if (!/consent\\.google\\./i.test(window.location.hostname)) {
                        return JSON.stringify(response);
                    }
                    response.detected = true;

                    const forms = Array.from(document.querySelectorAll('form[action*="consent.google.com/save"]'));
                    const isAcceptForm = (form) => {
                        const inputs = Array.from(form.querySelectorAll('input[type="hidden"]'));
                        const hasSC = inputs.some(input => input.name === "set_sc" && input.value === "true");
                        const hasAPS = inputs.some(input => input.name === "set_aps" && input.value === "true");
                        if (hasSC || hasAPS) return true;
                        const submit = form.querySelector('input[type="submit"],button[type="submit"],button');
                        if (!submit) return false;
                        const text = (submit.value || submit.innerText || submit.textContent || "").toLowerCase();
                        return /accept|accepter|aceptar|akzeptieren|accetta/.test(text);
                    };

                    const acceptForm = forms.find(isAcceptForm);
                    if (!acceptForm) {
                        return JSON.stringify(response);
                    }

                    const submit = acceptForm.querySelector('input[type="submit"],button[type="submit"],button');
                    if (submit) {
                        submit.click();
                    } else {
                        acceptForm.submit();
                    }
                    response.clicked = true;
                    return JSON.stringify(response);
                })();
            """

            start = time.time()
            while time.time() - start < 30:
                result = tab.Runtime.evaluate(expression=check_script)["result"]["value"]
                if not result:
                    return False
                state = json.loads(result)
                if not state.get("detected"):
                    return False  # Not on consent page
                if state.get("clicked"):
                    print("Clicked full-page consent accept button. Waiting for redirect...")
                    redirect_start = time.time()
                    while time.time() - redirect_start < 20:
                        host = tab.Runtime.evaluate(expression="window.location.hostname")["result"]["value"]
                        if host and "consent.google" not in host.lower():
                            print("Full-page consent cleared.")
                            return True
                        time.sleep(1)
                    # still on consent page; retry once more
                    time.sleep(1)
                else:
                    # consent detected but accept button not found
                    return False
            return False

        # print(f"Navigating to URL: https://api.ipify.org")
        # tab.Page.navigate(url="https://api.ipify.org")
        # time.sleep(5)

        print(f"Navigating to URL: {self.url}")
        tab.Page.navigate(url=self.url, _timeout=10)

        print('Waiting 5 seconds')
        time.sleep(5)

        if accept_fullpage_consent_if_present():
            time.sleep(3)

        # Click "Accept all" button if cookie consent popup appears
        print('Checking for cookie consent popup...')
        accept_button_clicked = tab.Runtime.evaluate(expression="""
            (function() {
                const btn = document.getElementById('L2AGLb');
                if (btn && btn.offsetParent !== null) {
                    btn.click();
                    return true;
                }
                return false;
            })();
        """)["result"]["value"]
        if accept_button_clicked:
            print('✓ Clicked "Accept all" cookie consent button')
            time.sleep(2)
        else:
            print('✓ No cookie consent popup detected')

        # Check for captcha presence on the page
        print('Checking for captcha...')
        start = time.time()
        captcha_timeout = 180

        while True:
            time.sleep(3)
            ctype = tab.Runtime.evaluate(expression=self.JS_DETECT)["result"]["value"]

            if ctype == "none":
                print("✔️  No captcha → going on")
                break

            if ctype == "recaptcha":
                print("⏳ reCAPTCHA identified, wait for Capsolver extension")
                if time.time() - start > captcha_timeout:
                    raise RuntimeError("reCAPTCHATimeOutError")
                time.sleep(1)
                continue

            if ctype == "image":
                print("🖼️  Captcha image identified, OpenAI resolution...")
                img_b64 = tab.Runtime.evaluate(expression="""
                    (function () {
                        const img = document.querySelector('img[src*="/sorry/image"]');
                        if (!img) return null;
                        const c = document.createElement('canvas');
                        c.width = img.naturalWidth; c.height = img.naturalHeight;
                        c.getContext('2d').drawImage(img, 0, 0);
                        return c.toDataURL('image/png').split(',')[1];
                    })();
                """)["result"]["value"]

                if not img_b64:
                    raise RuntimeError("Not possible to capture captcha image")

                img_bytes = base64.b64decode(img_b64)
                code = ocr_json_bytes(img_bytes)
                print(f"OCR → {code}")

                tab.Runtime.evaluate(expression=f"""
                    document.querySelector('input[name="captcha"]').value = "{code}";
                    document.getElementById('captcha-form').submit();
                """)
                time.sleep(3)
                continue

        print('Waiting done')
        # Waiting after Captcha solved
        time.sleep(5)

        # Fetch the cookies
        cookies_list = tab.Network.getCookies()['cookies']
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies_list}
        print("Cookies Retrieved:", cookie_dict)

        # Fetch and deduplicate headers (HTTP/2 pseudo headers or case variants may repeat)
        headers_dict = {}
        for header_name, header_value in captured_headers.items():
            if not header_name:
                continue

            normalized_name = header_name.strip()
            if normalized_name.startswith(':'):
                continue

            lower_name = normalized_name.lower()
            if lower_name in ('cookie', 'accept-encoding'):
                continue

            if lower_name in headers_dict:
                continue  # Already recorded (case-insensitive)

            canonical_name = "-".join(part.capitalize() for part in lower_name.split('-'))
            headers_dict[lower_name] = (canonical_name, header_value)

        headers_dict = {canonical: value for canonical, value in headers_dict.values()}

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

        print("Cleaning up...")
        self.cleanup()

        return page_content, cookie_dict, headers_dict, curl_command
