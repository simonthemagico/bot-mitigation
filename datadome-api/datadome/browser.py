from monseigneur.core.browser import URL
from monseigneur.core.browser.curl import PyCurlBrowser
from monseigneur.core.browser.exceptions import ClientError, PycurlStreamError, PyCurlRewindError, Http2Error, ReadTimeoutError, ServerError, EmptyReplyError
from monseigneur.core.exceptions import BrowserSSLError, ConnectionResetByPeer
from requests.exceptions import ProxyError, ChunkedEncodingError
from monseigneur.core.tools.decorators import retry

from .pages import *
import re

import json
from json.decoder import JSONDecodeError
from simplejson.errors import JSONDecodeError as SimpleJSONDecodeError

import js2py
from functools import wraps
from urllib.parse import quote, unquote
from .exceptions import IpBlockedError, NoMatchError, Speech2TextException
from .solver import Speech2Text
from urllib.parse import urlparse

import random
import os

MAX_REQUESTS = 20

def with_retries(f):
    @wraps(f)
    @retry(ClientError, tries=6, delay=10, backoff=0)
    @retry(ServerError, tries=2, delay=10, backoff=0)
    @retry(PyCurlRewindError, tries=3, delay=2, backoff=0)
    @retry(Http2Error, tries=3, delay=10, backoff=0)
    @retry(PycurlStreamError, tries=10, delay=5, backoff=0)
    @retry(BrowserSSLError, tries=4, delay=1, backoff=1)
    @retry(ConnectionResetByPeer, tries=6, delay=20, backoff=0)
    @retry(Speech2TextException, tries=3, delay=2, backoff=0)
    # @retry(IpBlockedError, tries=3, delay=2, backoff=0)
    @retry(SimpleJSONDecodeError, tries=3, delay=10, backoff=0)
    @retry(Speech2TextException, tries=6, delay=30, backoff=0)
    @retry(ProxyError, tries=3, delay=5, backoff=0)
    @retry(EmptyReplyError, tries=3, delay=5, backoff=0)
    @retry(ReadTimeoutError, tries=30, delay=2, backoff=0)
    @retry(ChunkedEncodingError, tries=5, delay=2, backoff=0)
    @retry(AssertionError, tries=5, delay=2, backoff=0)
    def wrapped(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except (ReadTimeoutError, IpBlockedError, ProxyError, Speech2TextException, ConnectionResetByPeer, BrowserSSLError) as e:
            self.set_random_proxy()
            raise(e)

    return wrapped


def with_bypass(f):
    @wraps(f)
    def wrapped(self, *args, **kwargs):
        try:
            k = f(self, *args, **kwargs)
            if self.request_count > MAX_REQUESTS:
                self.set_random_proxy()
                self.request_count = 0
            return k
        except ClientError as e:
            cid = self.session.cookies.get("datadome")
            self.session.cookies.clear()
            if e.response.status_code != 403:
                raise ClientError(e) from e
            self.datadome_done = True
            try:
                url = json.loads(e.response.text).get('url')
            except JSONDecodeError:
                match = re.findall(r"'cid':'(?P<initialCid>.+?)','hsh':'(?P<hash>[0-9A-Z]+)','t':'(?P<te>[a-z]+)','s':(?P<s>\d+),'e':'([0-9a-z]+)'", e.response.text)
                if match:
                    initialCid, _hash, t, s, _e  = match[0]
                    url = 'https://geo.captcha-delivery.com/captcha/?initialCid={initialCid}&hash={hash}&cid={cid}&t={t}&referer={referer}&s={s}&e={e}' \
                                .format(
                                    initialCid=initialCid,
                                    cid=cid,
                                    hash=_hash,
                                    t=t,
                                    s=s,
                                    e=_e,
                                    referer=quote(e.response.url)
                                )
                    self.logger.warning("captcha: " + url)
                else:
                    raise NoMatchError
            assert url
            self.bypass_page(url)
            raise e

    return wrapped


class DatadomeSolver(PyCurlBrowser):

    TIMEOUT = 20

    BASEURL = 'https://data_solver.com'
    HTTP2 = True

    geo_captcha_check_page = URL(r'https://geo.captcha-delivery.com/captcha/check', GeoCaptchaCheckPage)
    geo_captcha_page = URL(r'https://geo.captcha-delivery.com/captcha/', GeoCaptchaPage)

    def __init__(self, *args, **kwargs):
        super(DatadomeSolver, self).__init__(*args, **kwargs)
        self.request_count = 0
        self.set_user_agent()
        self.proxy_pool = kwargs.get('proxy_pool')
        self.set_random_proxy()
        self.domain = None

    def set_user_agent(self):
        user_agents = ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"]
        self.user_agent = random.choice(user_agents)

    @with_retries
    @with_bypass
    def go_to(self, link):
        try:
            self.domain = urlparse(link).netloc
        except Exception as e:
            raise e
        self.location(link)
        return {
            "datadome": self.session.cookies.get('datadome', domain=self.domain)
        }

    def set_random_proxy(self):
        self.session.PROXIES = {
            "host": "164.92.186.222",
            "port": 22223,
            "username": "user-uuid-6ae9801d46e94ad59ac7f057ce261581",
            "password": "4ebe43e321d2"
        }
        if self.proxy_pool == 'smartproxy':
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../proxies/smartproxy.txt")
            with open(file_path) as f:
                proxy_string = random.choice(f.read().splitlines())
                value_list = [value.strip() for value in proxy_string.split(":")]

                self.logger.critical("proxy: {}".format(proxy_string))

                curl_proxies = {
                    "host": value_list[0],
                    "port": int(value_list[1]),
                    "username": value_list[2],
                    "password": value_list[3]
                }

                self.session.PROXIES = curl_proxies
                self.session.cookies.clear()

    def bypass_page(self, link):
        headers = {
            'user-agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }

        self.location(link, headers=headers)
        assert self.geo_captcha_page.is_here()

        icid = re.findall(r'initialCid=(.+?)&', link)[0]
        cid = re.findall(r'cid=(.+?)&', link)[0]
        referer = unquote(re.findall(r'referer=(.+?)&', link)[0])
        hash = re.findall(r'hash=(.+?)&', link)[0]
        s = re.findall(r's=(\d+)', link)[0]
        e = re.findall(r'e=(.+?)$', link)[0]

        self.params = {
            'cid': cid,
            'icid': icid,
            'ccid': 'null',
            'hash': hash,
            'referer': referer,
            'parent_url': link,
            'x-forwarded-for': '',
            's': s,
            'userEnv': e
        }

        self.params['captchaChallenge'] = self.get_id()
        self.solve()

    def get_id(self):
        script = """
        function getCaptchaID(t,r){function e(t,r,e){this.seed=t,this.currentNumber=t%r,this.offsetParameter=r,this.multiplier=e,this.currentNumber<=0&&(this.currentNumber+=r)}e.prototype.getNext=function(){return this.currentNumber=this.multiplier*this.currentNumber%this.offsetParameter,this.currentNumber};for(var n=[function(t,r){var e=0;if(s="VEc5dmEybHVaeUJtYjNJZ1lTQnFiMkkvSUVOdmJuUmhZM1FnZFhNZ1lYUWdZWEJ3YkhsQVpHRjBZV1J2YldVdVkyOGdkMmwwYUNCMGFHVWdabTlzYkc5M2FXNW5JR052WkdVNklERTJOMlJ6YUdSb01ITnVhSE0",navigator.userAgent){for(var n=0;n<s.length;n+=1%Math.ceil(1+3.1425172/navigator.userAgent.length))e+=s.charCodeAt(n).toString(2)|26157^r;return e}return s^r},function(t,r){for(var e=(navigator.userAgent.length<<Math.max(t,3)).toString(2),n=-42,a=0;a<e.length;a++)n+=e.charCodeAt(a)^r<<a%3;return n},function(t,r){for(var e=0,n=(navigator.language?navigator.language.substr(0,2):void 0!==navigator.languages?navigator.languages[0].substr(0,2):"default").toLocaleLowerCase()+r,a=0;a<n.length;a++)e=((e=((e+=n.charCodeAt(a)<<Math.min((a+r)%(1+t),2))<<3)-e+n.charCodeAt(a))&e)>>a;return e}],a=new e(function(t){for(var r=126^t.charCodeAt(0),e=1;e<t.length;e++)r+=(t.charCodeAt(e)*e^t.charCodeAt(e-1))>>e%2;return r}(t),1723,7532),u=a.seed,i=0;i<r;i++)u^=(0,n[a.getNext()%n.length])(i,a.seed);return u}
        getCaptchaID("thisisgoingtobecid", 10)
        """ \
           .replace("navigator.userAgent", "'%s'" % (self.user_agent)) \
           .replace("thisisgoingtobecid", self.params.get("cid")) \
           .replace("navigator.languages", "['en-GB', 'en-US', 'en']") \
           .replace("navigator.language", "'en-GB'")

        captchaID = js2py.eval_js(script)
        return captchaID

    def solve(self):
        blocked = self.page.is_blocked()
        if blocked:
            self.request_count = 0
            raise IpBlockedError

        challenge = self.page.get_challenge()
        gt = self.page.get_gt()

        proxy_string = "{user}:{password}@{host}:{port}".format(
            user=self.session.PROXIES["username"],
            password=self.session.PROXIES["password"],
            host=self.session.PROXIES["host"],
            port=self.session.PROXIES["port"],
        )

        s2t = Speech2Text(proxies={
            'http': 'http://' + proxy_string,
            'https': 'http://' + proxy_string,
        }, gt=gt, challenge=challenge, apikey="fJpBTCWBnvcBJ551_qXAcnnr9gH9XYKOKI9EXMXb6VyC",
        user_agent=self.user_agent)
        solved_response = s2t.run()

        self.params.update(solved_response)
        self.params['ua'] = self.user_agent

        headers = {
            'user-agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }

        self.location('https://geo.captcha-delivery.com/captcha/check', params=self.params, headers=headers)
        assert self.geo_captcha_check_page.is_here()

        name, value = self.page.get_cookies()
        assert name, value
        self.session.cookies.clear()
        self.session.cookies.set(name, value, domain=self.domain)

    def gen_random_ttst(self, start=15, end=30):
        # 29.300000071525574
        first = str(random.randint(start, end))
        second = str(random.randint(1, 10)) + "00" * random.randint(0, 3) + str(random.randint(10**7, 10**8))
        return first + "." + second

    def validate_cookies(self, url: str = None):
        headers = {
            'authority': 'dd.leboncoin.fr',
            'user-agent': self.user_agent,
            'content-type': 'application/x-www-form-urlencoded',
            'accept': '*/*',
            'sec-gpc': '1',
            'origin': 'https://www.leboncoin.fr',
            'referer': url,
            'accept-language': 'en-GB,en;q=0.9',
        }

        if not url:
            url = self.url

        data = {
            'jsData': '{"ttst":%s,"ifov":false,"wdifts":false,"wdifrm":false,"wdif":false,"br_h":726,"br_w":571,"br_oh":805,"br_ow":1440,"nddc":1,"rs_h":900,"rs_w":1440,"rs_cd":30,"phe":false,"nm":false,"jsf":false,"ua":"%s","lg":"en-GB","pr":2,"hc":8,"ars_h":806,"ars_w":1440,"tz":-120,"str_ss":true,"str_ls":true,"str_idb":true,"str_odb":true,"plgod":false,"plg":5,"plgne":"NA","plgre":"NA","plgof":"NA","plggt":"NA","pltod":false,"hcovdr":false,"plovdr":false,"ftsovdr":false,"lb":false,"eva":33,"lo":false,"ts_mtp":0,"ts_tec":false,"ts_tsa":false,"vnd":"Google Inc.","bid":"NA","mmt":"application/pdf,text/pdf","plu":"PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF","hdn":false,"awe":false,"geb":false,"dat":false,"med":"defined","aco":"probably","acots":false,"acmp":"probably","acmpts":true,"acw":"probably","acwts":false,"acma":"maybe","acmats":false,"acaa":"probably","acaats":true,"ac3":"","ac3ts":false,"acf":"probably","acfts":false,"acmp4":"maybe","acmp4ts":false,"acmp3":"probably","acmp3ts":false,"acwm":"maybe","acwmts":false,"ocpt":false,"vco":"probably","vcots":false,"vch":"probably","vchts":true,"vcw":"probably","vcwts":true,"vc3":"maybe","vc3ts":false,"vcmp":"","vcmpts":false,"vcq":"","vcqts":false,"vc1":"probably","vc1ts":false,"dvm":8,"sqt":false,"so":"landscape-primary","wbd":false,"wbdm":true,"wdw":true,"cokys":"bG9hZFRpbWVzY3NpYXBwcnVudGltZQ==L=","ecpc":false,"lgs":true,"lgsod":false,"bcda":true,"idn":true,"capi":false,"svde":false,"vpbq":true,"xr":true,"bgav":true,"rri":true,"idfr":true,"ancs":true,"inlc":true,"cgca":true,"inlf":true,"tecd":true,"sbct":true,"aflt":true,"rgp":true,"bint":true,"spwn":false,"emt":false,"bfr":false,"dbov":false,"glvd":"Apple","glrd":"Apple M1","tagpu":%s,"prm":true,"tzp":"Europe/Paris","cvs":true,"usb":"defined"}' % (
                self.gen_random_ttst(10, 60),
                self.user_agent,
                self.gen_random_ttst(10, 40)
            ),
            'events': '[]',
            'eventCounters': '[]',
            'jsType': 'ch',
            'cid': self.session.cookies.get('datadome', domain=".leboncoin.fr"),
            'ddk': '05B30BD9055986BD2EE8F5A199D973',
            'Referer': quote_plus(url) if 'https://www.leboncoin.fr' in url else 'https%3A%2F%2Fwww.leboncoin.fr%2F',
            'request': quote_plus(url.replace('https://www.leboncoin.fr', '')) if 'https://www.leboncoin.fr' in url else '%2F',
            'responsePage': 'origin',
            'ddv': '4.1.71'
        }

        try:
            self.location('https://dd.leboncoin.fr/js/', method='POST', headers=headers, data=data)
            assert self.dd_leboncoin_page.is_here()
        except SimpleJSONDecodeError:
            raise IpBlockedError

        name, value = self.page.get_cookies()
        self.session.cookies.set(name=name, value=value, domain=".leboncoin.fr")
