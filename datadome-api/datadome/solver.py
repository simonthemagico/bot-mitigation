from json.decoder import JSONDecodeError
from matrix.modules.leboncoin_matrix.module.exceptions import Speech2TextException
import requests
import time
import json
import re
from urllib.parse import urljoin
from monseigneur.core.tools.decorators import retry
from requests.exceptions import ProxyError, SSLError
from simplejson.errors import JSONDecodeError
import js2py

API_KEY = "132069aefa859713ab15d5cd78e112a4"

class CaptchaNotSolvedException(Exception):
    pass

class Speech2Text:

    def __init__(self, gt, challenge, proxies: dict, apikey, user_agent, url="https://api.eu-de.speech-to-text.watson.cloud.ibm.com/instances/b4c70dc7-d197-4d86-b901-e3d2e7a824a1"):
        assert apikey
        assert url
        assert proxies

        self.gt = gt
        self.challenge = challenge
        self.url = url
        self.apikey = apikey

        self.s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=20)
        self.s.mount('http://', adapter)
        self.s.mount('https://', adapter)

        self.s.headers.update({
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'sec-ch-ua': '"Chromium";v="94", "Google Chrome";v="94", ";Not A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        })
        self.s.proxies.update(proxies)

    def run(self):
        self.trigger_ajax()
        audio_url = self.get_audio_url()
        audio_content = self.download_file(audio_url)
        solved = self.to_text(audio_content)
        return self.validate(solved)

    def get_callback_id(self):
        self.callback_id = js2py.eval_js(
            "parseInt(Math.random() * 10000) + (new Date()).valueOf()")
        return self.callback_id
        # return str(int(time.time() * 1000))

    def to_json(self, r):
        try:
            return json.loads(r.text.split('(')[1].strip(')'))
        except:
            raise Exception({
                "error": "Problem decoding json",
                "response": r.text
            })

    @retry(ProxyError, tries=10, delay=0, backoff=1)
    @retry(SSLError, tries=4, delay=0, backoff=0)
    def validate(self, answer):
        time.sleep(3)
        url = "https://api-na.geetest.com/ajax.php?gt=%s&challenge=%s&a=%s&lang=en-gb&callback=geetest_%s" % \
            (self.gt, self.challenge, answer, self.get_callback_id())
        r = self.s.get(url, verify=False)
        r_json = self.to_json(r)
        validate = r_json.get("data", {}).get("validate")
        if not validate:
            raise Speech2TextException({
                "error": "No validate",
                "response": r_json,
                "url": url
            })
        return {
            "geetest-response-challenge": self.challenge,
            "geetest-response-validate": validate,
            "geetest-response-seccode": "%s|jordan" % (validate)
        }

    @retry(ProxyError, tries=10, delay=0, backoff=0)
    @retry(SSLError, tries=4, delay=0, backoff=0)
    def trigger_ajax(self):
        url = "https://api-na.geetest.com/ajax.php?gt=%s&challenge=%s&lang=en-gb&pt=0&client_type=web&callback=geetest_%s" % (
            self.gt, self.challenge, self.get_callback_id())
        r = self.s.get(url, verify=False)
        text = r.text.split('(')[1].strip(')')
        z = json.loads(text)
        if z["status"] != "success":
            raise Speech2TextException({
                "error": "Solver: Ajax trigger failed",
                "response": r.text,
                "url": url
            })

    @retry(ProxyError, tries=10, delay=0, backoff=0)
    @retry(SSLError, tries=4, delay=0, backoff=0)
    def get_audio_url(self):
        audio_request_url = "https://api-na.geetest.com/get.php?gt=%s&challenge=%s&type=voice&lang=en-gb&callback=geetest_%s" % (
            self.gt, self.challenge, self.get_callback_id())
        r = self.s.get(audio_request_url, verify=False)
        print(r.text)
        voice_path = re.findall(r'"voice_path": "(.+?)"', r.text)
        if not voice_path:
            raise Speech2TextException({
                "error": "Solver: Voice path not found",
                "response": r.text,
                "url": audio_request_url
            })
        voice_path = voice_path[0]
        full_audio_url = urljoin("https://static.geetest.com/", voice_path)
        return full_audio_url

    @retry(ProxyError, tries=10, delay=0, backoff=0)
    @retry(SSLError, tries=4, delay=0, backoff=0)
    def download_file(self, url: str):
        r = self.s.get(url, verify=False)
        return r.content

    def to_text(self, data):
        headers = {
            'Content-Type': 'audio/mp3',
        }

        response = requests.post(
            '%s/v1/recognize' % self.url, headers=headers, data=data, auth=('apikey', self.apikey))
        print(response.content)
        try:
            transcript = response.json(
            )['results'][0]['alternatives'][0]['transcript']
            transcript = transcript.lower()
            letters = ['one', 'two', 'three', 'four', 'five',
                       'six', 'seven', 'eight', 'nine', 'zero']
            numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
            for lt, nm in zip(letters, numbers):
                transcript = transcript.replace(lt, nm)
            code = re.sub("\D", "", transcript)
            return code
        except KeyError:
            raise Speech2TextException({
                'reason': 'failed key error',
                'response': response.text
            })
        except (IndexError, AttributeError, JSONDecodeError) as e:
            print('Solve: Failed')
            print('Renew: API Key')
            raise Speech2TextException(e)
