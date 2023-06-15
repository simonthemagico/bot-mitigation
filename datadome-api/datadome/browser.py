import json
import math
import os
import time
import secrets
import base64
import uuid
from matrix.core.tasks_done_reasons import InvalidUrl
from matrix.core.exceptions import MatrixException

from .solver import Speech2Text
from matrix.modules.leboncoin_matrix.module.exceptions import IpBlockedError, NoMatchError
from matrix.modules.leboncoin_matrix.module.exceptions import Speech2TextException, CookiesDecodeError

from monseigneur.core.tools.decorators import retry
from monseigneur.core.browser import URL
from monseigneur.core.browser.curl import PyCurlBrowser
from monseigneur.core.browser.exceptions import ServerError, PyCurlRewindError, PycurlStreamError, Http2Error, ProxyError, EmptyReplyError, ReadTimeoutError, SelfSignedError
from monseigneur.core.browser.exceptions import ClientError, PycurlStreamError, PyCurlRewindError, Http2Error, ReadTimeoutError, ServerError, EmptyReplyError, SelfSignedError, ProxyResolveError

from monseigneur.core.exceptions import BrowserSSLError, ConnectionResetByPeer

from matrix.modules.leboncoin_matrix.module.exceptions import IpBlockedError, NoMatchError
from matrix.modules.leboncoin_matrix.module.mouse import MouseMoveEvents
from matrix.modules.leboncoin_matrix.module.fingerprints import FINGERPRINTS
from simplejson.errors import JSONDecodeError as SimpleJSONDecodeError

import random
from datetime import datetime
import re
from urllib.parse import quote, quote_plus, unquote, urlparse
import js2py
from functools import wraps

from monseigneur.core.browser.pages import HTMLPage, JsonPage
from monseigneur.core.browser.filters.json import Dict
import tldextract

MAX_REQUESTS = 20

def with_bypass(f):
    @wraps(f)
    def wrapped(self, *args, **kwargs):
        try:
            if self.request_count > MAX_REQUESTS:
                self.set_random_proxy()
                self.request_count = 0
            k = f(self, *args, **kwargs)
            return k
        except (ClientError, ServerError) as e:
            if e.response.status_code == 429:
                self.set_random_proxy()
                raise e
            if e.response.status_code != 403:
                raise e
            if e.response.status_code == 403 and '<title>403</title>403 Forbidden' in e.response.text:
                raise MatrixException(InvalidUrl)
            cid = self.session.cookies.get("datadome", domain=self.domain)
            self.datadome_done = True
            match = re.findall(r"'cid':'(?P<initialCid>.+?)','hsh':'(?P<hash>[0-9A-Z]+)','t':'(?P<te>[a-z]+)','s':(?P<s>\d+),'e':'(?P<e>[0-9a-z]+)'", e.response.text) or \
                re.findall(r"'cid':'(?P<initialCid>.+?)','hsh':'(?P<hash>[0-9A-Z]+)','t':'(?P<te>[a-z]+)','r':'b','s':(?P<s>\d+),'e':'(?P<e>[0-9a-z]+)'", e.response.text) or \
                re.findall(r'"url":"(?P<url>.+?)"', e.response.text)
            if match and isinstance(match[0], str):
                url = match[0]
            elif match and isinstance(match[0], tuple):
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
            else:
                raise NoMatchError
            self.logger.warning("captcha: " + url)
            assert url
            self.bypass_page(url)
            raise e
    return wrapped


def with_retries(f):
    @wraps(f)
    @retry(ClientError, tries=10, delay=5, backoff=0)
    @retry(ServerError, tries=15, delay=5, backoff=0)
    @retry(PyCurlRewindError, tries=3, delay=2, backoff=0)
    @retry(Http2Error, tries=3, delay=10, backoff=0)
    @retry(PycurlStreamError, tries=30, delay=5, backoff=0)
    @retry(BrowserSSLError, tries=10, delay=2, backoff=1)
    @retry(ConnectionResetByPeer, tries=20, delay=2, backoff=0)
    @retry(IpBlockedError, tries=3, delay=2, backoff=0)
    @retry(SimpleJSONDecodeError, tries=3, delay=10, backoff=0)
    @retry(Speech2TextException, tries=6, delay=30, backoff=0)
    @retry(ProxyError, tries=3, delay=5, backoff=0)
    @retry(EmptyReplyError, tries=3, delay=5, backoff=0)
    @retry(ReadTimeoutError, tries=30, delay=2, backoff=0)
    @retry(AssertionError, tries=5, delay=2, backoff=0)
    @retry(NoMatchError, tries=10, delay=10, backoff=0)
    @retry(SelfSignedError, tries=30, delay=0, backoff=0)
    @retry(ProxyResolveError, tries=20, delay=5, backoff=1)
    def wrapped(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except IpBlockedError as e:
            self.logger.critical("ip blocked, changing proxy")
            self.session.cookies.clear()
            self.set_random_proxy()
            raise e
        except (ReadTimeoutError, ProxyError, Speech2TextException, BrowserSSLError) as e:
            self.set_random_proxy()
            raise e
    return wrapped

class GeoCaptchaPage(HTMLPage):

    def is_blocked(self):
        return len(re.findall("captchaAudioChallenge: '(.*?)'", self.text)) == 0

    def get_sitekey(self):
        return re.findall("'sitekey' : '(.*?)',", self.text)[0]

    def get_cid(self):
        return re.findall(r"cid =  '(.*?)'", self.text)[0]

    def get_ccid(self):
        return re.findall(r"ccid=' \+ encodeURIComponent\( '(.*?)'", self.text)[0]

    def get_ua(self):
        return re.findall(r"ua=' \+ encodeURIComponent\( '(.*?)'", self.text)[0]

    def get_s(self):
        return re.findall(r"s:\s+'(\d+)'", self.text)[0]

    def get_user_env(self):
        return re.findall(r'name="user_env" value="(.*?)"', self.text)[0]

    def get_dd_captcha_seed(self):
        return re.findall(r"captchaChallengeSeed: '(.*?)'", self.text)[0]

    def get_dd_audio_challenge(self):
        return re.findall(r"captchaAudioChallenge: '(.*?)'", self.text)[0]

    def get_dd_audio_challenge_path(self):
        return re.findall(r"captchaAudioChallengePath: '(.*?)'", self.text)[0]

    def get_dd_captcha_env(self):
        return re.findall(r"'&ddCaptchaEnv=' \+ encodeURIComponent\( '(.*?)' \)", self.text)[0]

    def get_offset(self):
        return re.findall(r"offset: (.*?),", self.text)[0]


class GeoCaptchaCheckPage(JsonPage):

    def build_doc(self, text):
        return super().build_doc(text)

    def get_cookies(self):
        cookie = Dict("cookie")(self.doc)
        return cookie.split(';')[0].split('=')


class DatadomeSdkPage(JsonPage):

    def get_cookies(self):
        cookie = Dict("cookie")(self.doc)
        return cookie.split(';')[0].split('=')

class DatadomeSolver(PyCurlBrowser):

    TIMEOUT = 5
    # HTTP2 = True
    BASEURL = "https://geo.captcha-delivery.com"
    PRESERVE_HEADERS = False
    UA_TYPE = "desktop" # "desktop" or "app" or "webview"

    geo_captcha_check_page = URL(r'https://geo.captcha-delivery.com/captcha/check', GeoCaptchaCheckPage)
    geo_captcha_page = URL(r'https://geo.captcha-delivery.com/captcha/', GeoCaptchaPage)
    dd_leboncoin_page = URL(
        r'https://dd.leboncoin.fr/js/',
        r'https://api-js.datadome.co/js/',
        r'https://api-sdk.datadome.co/sdk/',
        DatadomeSdkPage)

    def __init__(self, *args, **kwargs):
        super(DatadomeSolver, self).__init__(*args, **kwargs)
        self.domain = kwargs.pop("domain", ".leboncoin.fr")
        self.origin = kwargs.pop("origin", "https://www.leboncoin.fr")
        self.dd_endpoint = kwargs.pop("dd_endpoint", "api-js.datadome.co")
        self.proxy_pool = kwargs.get('proxy_pool')
        self.proxy_string = kwargs.get('proxy_string')
        self.request_count = 0
        # GPU or WEBGL vender
        self.glvd = 'NA'
        # GPU or WEBGL renderer
        self.glrd = 'NA'
        self.referer = self.BASEURL
        self.ip = ''

        self.set_user_agent()
        if not self.PRESERVE_HEADERS:
            self.session.headers = {}
        
        self.user_agent = self.web_user_agent
        self.session.headers.update({'User-Agent': self.user_agent})

        os.environ["CURL_IMPERSONATE"] = "chrome101"
        self.set_random_proxy()

    def set_user_agent(self):
        self.web_user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'

    def set_random_proxy(self):
        proxy = self.get_random_proxy()
        self.session.PROXIES = self.get_curl_proxy(proxy)

    def get_curl_proxy(self, proxy_string):
        username, password_and_host, port = proxy_string.strip().split(':')
        password, host = password_and_host.split('@')
        proxy = {'host': host, 'port': int(port), 'username': username, 'password': password}
        return proxy

    def get_random_proxy(self):
        if self.proxy_string:
            value_list = [value.strip() for value in self.proxy_string.split(":")]
            proxy_string = "{}:{}@{}:{}".format(value_list[2], value_list[3], value_list[0], value_list[1])
        elif self.proxy_pool:
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../proxies/{}.txt".format(self.proxy_pool))
            with open(file_path) as f:
                proxy_string = random.choice(f.read().splitlines())
                value_list = [value.strip() for value in proxy_string.split(":")]
                proxy_string = "{}:{}@{}:{}".format(value_list[2], value_list[3], value_list[0], value_list[1])
        self.logger.critical("proxy: {}".format(proxy_string))
        return proxy_string

    def get_new_params(self, code: str):
        def c(t):
            if not t or len(t) == 0:
                return None
            e = 0
            for o in range(len(t)):
                e += t[o]
            return e / len(t)

        def a(t):
            if not t or len(t) == 0:
                return None
            e = c(t)
            o = 0
            for n in range(len(t)):
                a = e - t[n]
                o += math.pow(a, 2)
            i = o / len(t)
            return math.sqrt(i)

        e = []
        o = []
        i = []
        M = []
        u = None
        d = None
        g = {}
        W = []
        s = set()

        # generate key events
        def generate_key_events():
            start = 1500
            range_min = 200
            range_max = 300
            keyEvents = []
            for c in code:
                keydown_ts = random.uniform(start, start+random.uniform(range_min, range_max))
                keyup_ts = random.uniform(keydown_ts, keydown_ts+random.uniform(range_min, range_max))
                keydown = {"ts": keydown_ts, "key": c, "type":"keydown"}
                keyup = {"ts": keyup_ts, "key": c, "type":"keyup"}
                keyEvents.append(keydown)
                keyEvents.append(keyup)
                start = keyup_ts

            return keyEvents

        keyEvents = generate_key_events()

        for N in range(len(keyEvents)):
            D = keyEvents[N]
            if D["type"] == "keydown":
                g[D["key"]] = D
                if u:
                    o.append(D["ts"] - u["ts"])
                u = D
            elif D["type"] == "keyup":
                if D["key"] in g:
                    I = g[D["key"]]
                    g[D["key"]] = None
                    e.append(D["ts"] - I["ts"])
                if d:
                    i.append(D["ts"] - d["ts"])
                d = D

            if N not in s:
                for l in range(N+1, len(keyEvents)):
                    k = keyEvents[l]
                    if D["key"] == k["key"]:
                        W.append([D, k])
                        s.add(N)
                        s.add(l)
                        break

        for j in range(len(W)):
            h, A = W[j]
            M.append(A["ts"] - h["ts"])

        t = {}
        t["k_hA"] = c(e)
        t["k_hSD"] = a(e)
        t["k_pA"] = c(o)
        t["k_pSD"] = a(o)
        t["k_rA"] = c(i)
        t["k_rSD"] = a(i)
        t["k_ikA"] = c(M)
        t["k_ikSD"] = a(M)

        return t

    def get_stcfp(self, url):
        # last 41 chars of the url as variable
        stcfp = url[-41:]
        full_stcfp = """%s:455:30752)
    at %s:56:29"""%(stcfp, url)
        # encode base64
        full_stcfp = base64.b64encode(full_stcfp.encode('utf-8')).decode('utf-8')
        return full_stcfp

    def get_pcso_params(self, pcso):
        r = math.floor(random.random() * 2) + 7
        d = 0
        for M in range(len(pcso)): d += ord(pcso[M])
        return {'pcsoNumShapes':r, 'pcsoSeed':d % 10}

    def get_challenge_response(self, solvedResponse, captchaChallengeSeed, challengeOffset):
        solvedCode = solvedResponse
        jst3a = random.randint(20000, 39999)
        pcso = secrets.token_hex(16)
        h = "17b88df8b525ad9e5cb4ddd7621e9c1a30cc9be2b361d8072d6fbef4b9370c77"

        computerInfoJson: dict = json.loads('''{{"pcso":"{pcso}","chksm":"e032f6b214c13f792cb3a1a5d60617bd","v":"1.2.0","h":"{h}","tagpu":24.464481108672263,"plgod":false,"plg":5,"plgne":true,"plgre":true,"plgof":false,"plggt":false,"pltod":false,"psn":true,"edp":true,"addt":true,"wsdc":true,"ccsr":true,"nuad":true,"bcda":true,"idn":true,"capi":false,"svde":false,"vpbq":true,"dvm":8,"vco":"probably","vcots":false,"vch":"probably","vchts":true,"vcw":"probably","vcwts":true,"vc3":"maybe","vc3ts":false,"vcmp":"","vcmpts":false,"vcq":"","vcqts":false,"vc1":"probably","vc1ts":true,"aco":"probably","acots":false,"acmp":"probably","acmpts":true,"acw":"probably","acwts":false,"acma":"maybe","acmats":false,"acaa":"probably","acaats":true,"ac3":"","ac3ts":false,"acf":"probably","acfts":false,"acmp4":"maybe","acmp4ts":false,"acmp3":"probably","acmp3ts":false,"acwm":"maybe","acwmts":false,"ocpt":false,"lg":"en-GB","npmtm":false,"phe":false,"nm":false,"awe":false,"geb":false,"dat":false,"sqt":false,"ucdv":false,"tzp":"Asia/Calcutta","tz":-330,"rs_w":1440,"rs_h":900,"isb":false,"plu":"PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF","mmt":"application/pdf,text/pdf","hcovdr":false,"plovdr":false,"ftsovdr":false,"hcovdr2":false,"plovdr2":false,"ftsovdr2":false,"glvd":"Google Inc. (Apple)","glrd":"ANGLE (Apple, Apple M1, OpenGL 4.1)","hc":8,"br_oh":803,"br_ow":1440,"ua":"{ua}","wbd":false,"ts_mtp":0,"pcsoNumShapes":7,"pcsoSeed":-2,"wwl":false,"k_hA":81.38000001907349,"k_hSD":14.212726749379476,"k_pA":199.7800000190735,"k_pSD":19.366507011554326,"k_rA":196.44999992847443,"k_rSD":23.102651260773683,"k_ikA":121.44999992847443,"k_ikSD":17.34423519046969,"bAudio":true,"xUser":0,"code":"{code}","jst3a":{jst3a},"jstsoc":-1}}'''.format(
            pcso=pcso,
            ua=self.user_agent,
            glvd=self.glvd,
            glrd=self.glrd,
            code=solvedCode,
            jst3a=jst3a,
            h=h
        ))
        newParams = self.get_new_params(solvedCode)
        computerInfoJson.update(newParams)

        pcsoParams = self.get_pcso_params(pcso)
        computerInfoJson.update(pcsoParams)

        computerInfo = json.dumps(computerInfoJson)

        def shuffle_characters(cArray: list, seed):
            index = len(seed) - 1
            a5 = math.floor(float(challengeOffset) / len(seed))
            for index in range(0, len(seed) - 2): a5 += ord(seed[index + 1]) % 370
            a9 = str(a5).split(".")[0]
            aa = -3
            for index in range(0, len(a9)): aa += int(a9[index]) % len(seed)
            def cK(cArr, ac):
                ag = len(cArr)
                while 0 != ag:
                    af = ((ac) / 3) * 1e4
                    ae = math.floor((af - math.floor(af)) * ag)
                    ad = cArr[ag - 1]
                    cArr[ag - 1] = cArr[ae]
                    cArr[ae] = ad
                    ag -= 1
                    ac += 1
                return cArr
            value = cK(cArray, aa)
            return value

        characters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")
        chArray = shuffle_characters(characters, captchaChallengeSeed)

        def captchaResponse(computerInfo, charArray):
            response = ""
            computerInfo = computerInfo.replace(": ", ":").replace(', "', ',"')
            ag = 0
            while ag < len(computerInfo):
                a8 = ord(computerInfo[ag])
                try:
                    a8p1 = ord(computerInfo[ag+1])
                except IndexError:
                    a8p1 = 0
                try:
                    a8p2 = ord(computerInfo[ag+2])
                except IndexError:
                    a8p2 = 0
                ab = (a8 >> 2)
                ac = (3 & a8) << 4 | (a8p1 >> 4)
                ad = ((15 & a8p1) << 2) | (a8p2 >> 6)
                ae = (63 & a8p2)
                if not a8p1: ad = ae = 64
                elif not a8p2: ae = 64
                response = response + charArray[ab] + charArray[ac] + charArray[ad] + charArray[ae]
                ag += 3
            return response

        response = captchaResponse(computerInfo, chArray)
        return response

    def bypass_page(self, link):
        referer = unquote(re.findall(r'referer=(.+?)&', link)[0])
        self.referer = referer

        self.location(link, headers={
            'Host': 'geo.captcha-delivery.com',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'close',
        })
        assert self.geo_captcha_page.is_here()

        icid = re.findall(r'initialCid=(.+?)&', link)[0]
        icid = unquote(icid)

        cid = re.findall(r'cid=(.+?)&', link)[0]
        hash = re.findall(r'hash=(.+?)&', link)[0]
        s = re.findall(r's=(\d+)', link)[0]

        self.link = link
        self.referer = referer

        cid = self.page.get_cid()
        userEnv = self.page.get_user_env()
        ccid = self.page.get_ccid()
        ua = self.user_agent
        s = self.page.get_s()

        self.params = {
            "cid": cid,
            "icid": icid,
            "ccid": ccid,
            "userEnv": userEnv,
            "ddCaptchaChallenge": "",
            "ddCaptchaResponse": "",
            "ddCaptchaEnv": "",
            "ddCaptchaAudioChallenge": "",
            "hash": hash,
            "ua": ua,
            "referer": referer,
            "parent_url": 'https://' + urlparse(referer).netloc + '/',
            "x-forwarded-for": self.ip,
            "captchaChallenge": "",
            "s": s,
            "ir": ""
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
           .replace("navigator.languages", "['en-US', 'en']") \
           .replace("navigator.language", "'en-US'")

        captchaID = js2py.eval_js(script)
        # assert len(str(captchaID)) == 9
        return captchaID

    @retry(CookiesDecodeError, tries=3, delay=2, backoff=0)
    def solve(self):
        blocked = self.page.is_blocked()
        if blocked:
            self.request_count = 0
            raise IpBlockedError

        self.params['ddCaptchaChallenge'] = self.page.get_dd_captcha_seed()
        self.params['ddCaptchaAudioChallenge'] = self.page.get_dd_audio_challenge()
        self.params['ddCaptchaEnv'] = self.page.get_dd_captcha_env()
        # challengeOffset = self.page.get_offset()
        audioUrl = self.page.get_dd_audio_challenge_path()

        if "/fr/" in audioUrl:
            audioUrl = audioUrl.replace("/fr/", "/en/")
        if "/es/" in audioUrl:
            audioUrl = audioUrl.replace("/es/", "/en/")

        self.logger.warning("audio url: {}".format(audioUrl))

        s2t = Speech2Text()
        solved_response = s2t.transcribe(audioUrl)

        self.logger.warning("solved response: {}".format(solved_response))

        self.params['ddCaptchaResponse'] = self.get_challenge_response(
            solvedResponse=solved_response,
            captchaChallengeSeed=self.params['ddCaptchaChallenge'],
            challengeOffset=5.0
        )

        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            # 'Cookie': 'datadome=7_kB7HsKiYlxOpI-Lygo0_H-sMe1p_G7ouGyH58CNSccsNVQ87EZlAum~krzV5cUb~aqIUmh59FQklTywgtSJi6sBxIEKlpKCkcAv_3T-S7h5hJAIohhXjX-S57VdDFL',
            'Referer': self.link,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': self.user_agent,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }

        self.location('https://geo.captcha-delivery.com/captcha/check', headers=headers, params=self.params)
        assert self.geo_captcha_check_page.is_here()

        name, value = self.page.get_cookies()
        assert name, value
        self.session.cookies.set(name=name, value=value, domain=self.domain)
        if not self.dd_endpoint:
            return

        # self.validate_cookies_le2()

        # self.validate_cookies()

    def validate_cookies_ch2(self):
        headers = {
            'Host': 'api-js.datadome.co',
            # 'Content-Length': '4550',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; M2102J20SI Build/TP1A.221005.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/110.0.5481.154 Mobile Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': '*/*',
            'Origin': 'https://geo.captcha-delivery.com',
            'X-Requested-With': 'fr.leboncoin',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://geo.captcha-delivery.com/',
            # 'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        request_path = self.link.replace("https://{}".format(urlparse(self.referer).netloc), "")

        data = {
            'jsData': '{"ttst":58.39999999990687,"ifov":false,"tagpu":7.49343729859675,"hc":8,"br_oh":824,"br_ow":393,"ua":"Mozilla/5.0 (Linux; Android 13; M2102J20SI Build/TP1A.221005.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/110.0.5481.154 Mobile Safari/537.36","wbd":false,"wdif":false,"wdifrm":false,"npmtm":false,"br_h":824,"br_w":393,"nddc":0,"rs_h":873,"rs_w":393,"rs_cd":24,"phe":false,"nm":false,"jsf":false,"lg":"en-US","pr":2.75,"ars_h":873,"ars_w":393,"tz":-330,"str_ss":true,"str_ls":false,"str_idb":true,"str_odb":true,"plgod":false,"plg":0,"plgne":"NA","plgre":"NA","plgof":"NA","plggt":"NA","pltod":false,"hcovdr":false,"plovdr":false,"ftsovdr":false,"hcovdr2":false,"plovdr2":false,"ftsovdr2":false,"lb":false,"eva":33,"lo":false,"ts_mtp":5,"ts_tec":true,"ts_tsa":true,"vnd":"Google Inc.","bid":"NA","mmt":"empty","plu":"empty","hdn":false,"awe":false,"geb":false,"dat":false,"med":"defined","aco":"probably","acots":false,"acmp":"probably","acmpts":true,"acw":"probably","acwts":false,"acma":"maybe","acmats":false,"acaa":"probably","acaats":true,"ac3":"","ac3ts":false,"acf":"probably","acfts":false,"acmp4":"maybe","acmp4ts":false,"acmp3":"probably","acmp3ts":false,"acwm":"maybe","acwmts":false,"ocpt":false,"vco":"","vcots":false,"vch":"probably","vchts":true,"vcw":"probably","vcwts":true,"vc3":"maybe","vc3ts":false,"vcmp":"","vcmpts":false,"vcq":"","vcqts":false,"vc1":"probably","vc1ts":true,"dvm":4,"sqt":false,"so":"portrait-primary","wdw":false,"ecpc":false,"lgs":true,"lgsod":false,"psn":false,"edp":false,"addt":true,"wsdc":true,"ccsr":true,"nuad":false,"bcda":true,"idn":true,"capi":false,"svde":false,"vpbq":true,"ucdv":false,"spwn":false,"emt":false,"bfr":false,"dbov":false,"jset":1678796974}',
            'eventCounters': '[]',
            'jsType': 'ch',
            'cid': self.session.cookies.get('datadome'),
            'ddk': '05B30BD9055986BD2EE8F5A199D973',
            'Referer': quote_plus(self.link),
            'request': quote_plus(request_path),
            'responsePage': 'captcha',
            'ddv': '4.6.15'
        }
        self.location('https://api-js.datadome.co/js/', method='POST', headers=headers, data=data)
        assert self.dd_leboncoin_page.is_here()

        name, value = self.page.get_cookies()
        self.session.cookies.set(name=name, value=value, domain='.captcha-delivery.com')

    def validate_cookies_le2(self):
        data = 'jsData=%7B%22ttst%22%3A58.39999999990687%2C%22ifov%22%3Afalse%2C%22tagpu%22%3A7.49343729859675%2C%22hc%22%3A8%2C%22br_oh%22%3A824%2C%22br_ow%22%3A393%2C%22ua%22%3A%22Mozilla%2F5.0%20(Linux%3B%20Android%2013%3B%20M2102J20SI%20Build%2FTP1A.221005.003%3B%20wv)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Version%2F4.0%20Chrome%2F110.0.5481.154%20Mobile%20Safari%2F537.36%22%2C%22wbd%22%3Afalse%2C%22wdif%22%3Afalse%2C%22wdifrm%22%3Afalse%2C%22npmtm%22%3Afalse%2C%22br_h%22%3A824%2C%22br_w%22%3A393%2C%22nddc%22%3A0%2C%22rs_h%22%3A873%2C%22rs_w%22%3A393%2C%22rs_cd%22%3A24%2C%22phe%22%3Afalse%2C%22nm%22%3Afalse%2C%22jsf%22%3Afalse%2C%22lg%22%3A%22en-US%22%2C%22pr%22%3A2.75%2C%22ars_h%22%3A873%2C%22ars_w%22%3A393%2C%22tz%22%3A-330%2C%22str_ss%22%3Atrue%2C%22str_ls%22%3Afalse%2C%22str_idb%22%3Atrue%2C%22str_odb%22%3Atrue%2C%22plgod%22%3Afalse%2C%22plg%22%3A0%2C%22plgne%22%3A%22NA%22%2C%22plgre%22%3A%22NA%22%2C%22plgof%22%3A%22NA%22%2C%22plggt%22%3A%22NA%22%2C%22pltod%22%3Afalse%2C%22hcovdr%22%3Afalse%2C%22plovdr%22%3Afalse%2C%22ftsovdr%22%3Afalse%2C%22hcovdr2%22%3Afalse%2C%22plovdr2%22%3Afalse%2C%22ftsovdr2%22%3Afalse%2C%22lb%22%3Afalse%2C%22eva%22%3A33%2C%22lo%22%3Afalse%2C%22ts_mtp%22%3A5%2C%22ts_tec%22%3Atrue%2C%22ts_tsa%22%3Atrue%2C%22vnd%22%3A%22Google%20Inc.%22%2C%22bid%22%3A%22NA%22%2C%22mmt%22%3A%22empty%22%2C%22plu%22%3A%22empty%22%2C%22hdn%22%3Afalse%2C%22awe%22%3Afalse%2C%22geb%22%3Afalse%2C%22dat%22%3Afalse%2C%22med%22%3A%22defined%22%2C%22aco%22%3A%22probably%22%2C%22acots%22%3Afalse%2C%22acmp%22%3A%22probably%22%2C%22acmpts%22%3Atrue%2C%22acw%22%3A%22probably%22%2C%22acwts%22%3Afalse%2C%22acma%22%3A%22maybe%22%2C%22acmats%22%3Afalse%2C%22acaa%22%3A%22probably%22%2C%22acaats%22%3Atrue%2C%22ac3%22%3A%22%22%2C%22ac3ts%22%3Afalse%2C%22acf%22%3A%22probably%22%2C%22acfts%22%3Afalse%2C%22acmp4%22%3A%22maybe%22%2C%22acmp4ts%22%3Afalse%2C%22acmp3%22%3A%22probably%22%2C%22acmp3ts%22%3Afalse%2C%22acwm%22%3A%22maybe%22%2C%22acwmts%22%3Afalse%2C%22ocpt%22%3Afalse%2C%22vco%22%3A%22%22%2C%22vcots%22%3Afalse%2C%22vch%22%3A%22probably%22%2C%22vchts%22%3Atrue%2C%22vcw%22%3A%22probably%22%2C%22vcwts%22%3Atrue%2C%22vc3%22%3A%22maybe%22%2C%22vc3ts%22%3Afalse%2C%22vcmp%22%3A%22%22%2C%22vcmpts%22%3Afalse%2C%22vcq%22%3A%22%22%2C%22vcqts%22%3Afalse%2C%22vc1%22%3A%22probably%22%2C%22vc1ts%22%3Atrue%2C%22dvm%22%3A4%2C%22sqt%22%3Afalse%2C%22so%22%3A%22portrait-primary%22%2C%22wdw%22%3Afalse%2C%22ecpc%22%3Afalse%2C%22lgs%22%3Atrue%2C%22lgsod%22%3Afalse%2C%22psn%22%3Afalse%2C%22edp%22%3Afalse%2C%22addt%22%3Atrue%2C%22wsdc%22%3Atrue%2C%22ccsr%22%3Atrue%2C%22nuad%22%3Afalse%2C%22bcda%22%3Atrue%2C%22idn%22%3Atrue%2C%22capi%22%3Afalse%2C%22svde%22%3Afalse%2C%22vpbq%22%3Atrue%2C%22ucdv%22%3Afalse%2C%22spwn%22%3Afalse%2C%22emt%22%3Afalse%2C%22bfr%22%3Afalse%2C%22dbov%22%3Afalse%2C%22jset%22%3A1678796997%2C%22dcok%22%3A%22.captcha-delivery.com%22%2C%22es_sigmdn%22%3Anull%2C%22es_mumdn%22%3Anull%2C%22es_distmdn%22%3Anull%2C%22es_angsmdn%22%3Anull%2C%22es_angemdn%22%3Anull%7D&eventCounters=%7B%22mousemove%22%3A0%2C%22click%22%3A0%2C%22scroll%22%3A0%2C%22touchstart%22%3A1%2C%22touchend%22%3A1%2C%22touchmove%22%3A48%2C%22keydown%22%3A0%2C%22keyup%22%3A0%7D&jsType=le&cid=0ga8T83XADpI26PGgkOqREqOPoi4ly_7nhLf7oNDURRVzF_8RqVhBKC_9LMOFG8~QegVcCSBFLup~UK~~ibcP4xxvUe1SE3F1Ig65QfV4dOhHSqQikKLW39sMYVE6jTk&ddk=05B30BD9055986BD2EE8F5A199D973&Referer=https%253A%252F%252Fgeo.captcha-delivery.com%252Fcaptcha%252F%253FinitialCid%253DAHrlqAAAAAMAZYvIGEBVV6kALV_fLg%253D%253D%2526cid%253D9EdSjFDTWDiAdxclb-gLE2vBA6fsrlGJcGmZ52WBNvabDyFIUz59GXo0auCZ2DU5nt--fm-NO_mmpUsHesDPevz3rlNqwBHcoKR%7EhiP2c_qPhUkXGXDPvgRaXkyZGHx%2526referer%253Dhttps%25253A%25252F%25252Fauth.leboncoin.fr%25252Fapi%25252Fauthenticator%25252Fv1%25252Fcode%25252F11acb85a-5bfb-42f0-9b83-d5297f5053cc%25252Finfo%25253Fclient_id%25253Dlbc-front-android%2526hash%253D05B30BD9055986BD2EE8F5A199D973%2526t%253Dfe%2526s%253D18203%2526e%253Df3bfffb2cfc73a4d078aa6e7f25f0bf757c165cf92f023487c13d7cde82f907a%2526cid%253D9EdSjFDTWDiAdxclb-gLE2vBA6fsrlGJcGmZ52WBNvabDyFIUz59GXo0auCZ2DU5nt--fm-NO_mmpUsHesDPevz3rlNqwBHcoKR%7EhiP2c_qPhUkXGXDPvgRaXkyZGHx&request=%252Fcaptcha%252F%253FinitialCid%253DAHrlqAAAAAMAZYvIGEBVV6kALV_fLg%253D%253D%2526cid%253D9EdSjFDTWDiAdxclb-gLE2vBA6fsrlGJcGmZ52WBNvabDyFIUz59GXo0auCZ2DU5nt--fm-NO_mmpUsHesDPevz3rlNqwBHcoKR%7EhiP2c_qPhUkXGXDPvgRaXkyZGHx%2526referer%253Dhttps%25253A%25252F%25252Fauth.leboncoin.fr%25252Fapi%25252Fauthenticator%25252Fv1%25252Fcode%25252F11acb85a-5bfb-42f0-9b83-d5297f5053cc%25252Finfo%25253Fclient_id%25253Dlbc-front-android%2526hash%253D05B30BD9055986BD2EE8F5A199D973%2526t%253Dfe%2526s%253D18203%2526e%253Df3bfffb2cfc73a4d078aa6e7f25f0bf757c165cf92f023487c13d7cde82f907a%2526cid%253D9EdSjFDTWDiAdxclb-gLE2vBA6fsrlGJcGmZ52WBNvabDyFIUz59GXo0auCZ2DU5nt--fm-NO_mmpUsHesDPevz3rlNqwBHcoKR%7EhiP2c_qPhUkXGXDPvgRaXkyZGHx&responsePage=captcha&ddv=4.6.15'
        headers = {
            'Host': 'api-js.datadome.co',
            # 'Content-Length': '4550',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; M2102J20SI Build/TP1A.221005.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/110.0.5481.154 Mobile Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': '*/*',
            'Origin': 'https://geo.captcha-delivery.com',
            'X-Requested-With': 'fr.leboncoin',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://geo.captcha-delivery.com/',
            # 'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.location('https://api-js.datadome.co/js/', method='POST', headers=headers, data=data)
        assert self.dd_leboncoin_page.is_here()

    def set_random_token(self):
        user_id = str(uuid.uuid4())
        # base64 encode
        '''
        {"user_id":"18677d9a-2cae-6ed5-ac29-ef451505b896","created":"2023-02-22T06:39:57.253Z","updated":"2023-02-22T06:39:57.253Z","version":null}
        '''
        dd = {}
        dd["user_id"] = user_id
        dd["created"] = datetime.now().isoformat()
        dd["updated"] = datetime.now().isoformat()
        dd["version"] = None

        self.didomi_token = base64.b64encode(json.dumps(dd).replace(" ", "").encode("utf-8")).decode("utf-8")
        self.session.cookies.set(name="didomi_token", value=self.didomi_token, domain=self.domain)

    def validate_cookies(self):
        self.validate_cookies_ch()
        # random sleep between 2 and 4 seconds
        time.sleep(random.randint(200, 400) / 100)
        self.validate_cookies_le()

    def validate_cookies_ch(self):
        headers = {
            'User-Agent': self.user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            # 'Accept-Encoding': 'gzip, deflate, br',
            'Referer': self.referer,
            'Content-type': 'application/x-www-form-urlencoded',
            'Origin': self.origin.strip("/"),
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }

        request_path = self.referer.replace("https://{}".format(urlparse(self.referer).netloc), "")
        ddk = {
            'api-js.datadome.co': 'AC81AADC3279CA4C7B968B717FBB30',
            'dd.leboncoin.fr': '05B30BD9055986BD2EE8F5A199D973'
        }

        data = {
            'jsData': '{{"ttst":{ttst},"ifov":false,"tagpu":{tagpu},"glvd":"{glvd}","glrd":"{glrd}","hc":16,"br_oh":909,"br_ow":1280,"ua":"{ua}","wbd":false,"wdif":false,"wdifrm":false,"npmtm":"NA","br_h":824,"br_w":780,"nddc":1,"rs_h":960,"rs_w":1280,"rs_cd":24,"phe":false,"nm":false,"jsf":false,"lg":"en-US","pr":1,"ars_h":933,"ars_w":1280,"tz":0,"str_ss":true,"str_ls":true,"str_idb":true,"str_odb":false,"plgod":false,"plg":5,"plgne":true,"plgre":true,"plgof":false,"plggt":false,"pltod":false,"hcovdr":false,"plovdr":false,"ftsovdr":false,"hcovdr2":false,"plovdr2":false,"ftsovdr2":false,"lb":false,"eva":37,"lo":false,"ts_mtp":0,"ts_tec":false,"ts_tsa":false,"vnd":"","bid":"20181001000000","mmt":"application/pdf,text/pdf","plu":"PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF","hdn":false,"awe":false,"geb":false,"dat":false,"med":"defined","aco":"probably","acots":false,"acmp":"maybe","acmpts":false,"acw":"probably","acwts":false,"acma":"maybe","acmats":false,"acaa":"maybe","acaats":false,"ac3":"","ac3ts":false,"acf":"maybe","acfts":false,"acmp4":"maybe","acmp4ts":true,"acmp3":"maybe","acmp3ts":false,"acwm":"maybe","acwmts":true,"ocpt":false,"vco":"probably","vcots":false,"vch":"probably","vchts":true,"vcw":"probably","vcwts":true,"vc3":"","vc3ts":false,"vcmp":"","vcmpts":false,"vcq":"maybe","vcqts":false,"vc1":"probably","vc1ts":true,"dvm":4,"sqt":false,"so":"landscape-primary","wdw":true,"ecpc":false,"lgs":true,"lgsod":false,"psn":true,"edp":false,"addt":false,"wsdc":true,"ccsr":true,"nuad":false,"bcda":false,"idn":true,"capi":false,"svde":false,"vpbq":true,"ucdv":false,"spwn":false,"emt":false,"bfr":false,"dbov":false,"cfpfe":"ZnVuY3Rpb24oKXt2YXIgXzB4NGQxZjM3PWRvY3VtZW50WydceDcxXHg3NVx4NjVceDcyXHg3OVx4NTNceDY1XHg2Y1x4NjVceDYzXHg3NFx4NmZceDcyJ10oJ1x4NjJceDcyXHg2Zlx4NzdceDczXHg2NVx4NzJceDY2XHg2Y1x4NmZceDc3XHgyZFx4NjNceDZmXHg2","stcfp":"dGFncy5qczoyOjI0ODQwMwpfMHhhZjc4Y2VAaHR0cHM6Ly9kZC5sZWJvbmNvaW4uZnIvdGFncy5qczoyOjY2NjEzCnRAaHR0cHM6Ly9kZC5sZWJvbmNvaW4uZnIvdGFncy5qczoyOjY3MDQ3CkBodHRwczovL2RkLmxlYm9uY29pbi5mci90YWdzLmpzOjI6NjcwODgK","prm":true,"tzp":"UTC","cvs":true,"usb":"NA","jset":{jset}}}'.format(
                ttst=round(float(self.gen_random_ttst(200, 300))),
                tagpu=self.gen_random_ttst(10, 40),
                ua=self.user_agent,
                glvd=self.glvd,
                glrd=self.glrd,
                jset=int(datetime.now().timestamp())
            ),
            'eventCounters': '[]',
            'jsType': 'ch',
            'cid': self.session.cookies.get('datadome', domain=self.domain),
            'ddk': ddk[self.dd_endpoint],
            'Referer': quote_plus(self.referer),
            'request': quote_plus(request_path),
            'responsePage': 'origin',
            'ddv': '4.6.15'
        }

        self.location('https://{}/js/'.format(self.dd_endpoint), method='POST', headers=headers, data=data)
        assert self.dd_leboncoin_page.is_here()

        name, value = self.page.get_cookies()
        self.session.cookies.set(name=name, value=value, domain=self.domain)

    def validate_cookies_le(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/110.0',
            'Accept': '*/*',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Referer': self.referer,
            'Content-type': 'application/x-www-form-urlencoded',
            'Origin': self.origin.strip('/'),
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }

        request_path = self.referer.replace("https://{}".format(urlparse(self.referer).netloc), "")

        ddk = {
            'api-js.datadome.co': 'AC81AADC3279CA4C7B968B717FBB30',
            'dd.leboncoin.fr': '05B30BD9055986BD2EE8F5A199D973'
        }

        ddJsData = MouseMoveEvents()

        data = {
            'jsData': '{{"mp_cx":893,"mp_cy":395,"mp_tr":true,"mp_mx":5,"mp_my":-2,"mp_sx":893,"mp_sy":499,"cfpfe":"KCk9Pntjb25zdCBlPVhtKCk7Zm9yKGNvbnN0W24saV1vZiBPYmplY3QuZW50cmllcyhPdSkpe2NvbnN0IGE9YCR7bn0tJHtlfWA7aWYoZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoaSkpe0R1KGBkaXYgd2l0aCBpZCAnJHtpfScgYWxyZWFkeSBleGlzdHNgKTtjb250","stcfp":"L3dyYXBwZXIvMDFDRTlIWkNaVlBXOVFCNTIyUU5OUzhNWlEvaHVidmlzb3IuanM6MTo1MDczMDEKICAgIGF0IGFzeW5jIGh0dHBzOi8vY2RuLmh1YnZpc29yLmlvL3dyYXBwZXIvMDFDRTlIWkNaVlBXOVFCNTIyUU5OUzhNWlEvaHVidmlzb3IuanM6MToxNTk4MDg0","ttst":{ttst},"ifov":false,"tagpu":{tagpu},"glvd":"{glvd}","glrd":"{glrd}","hc":16,"br_oh":909,"br_ow":1280,"ua":"{ua}","wbd":false,"wdif":false,"wdifrm":false,"npmtm":"NA","br_h":824,"br_w":780,"nddc":1,"rs_h":960,"rs_w":1280,"rs_cd":24,"phe":false,"nm":false,"jsf":false,"lg":"en-US","pr":1,"ars_h":933,"ars_w":1280,"tz":0,"str_ss":true,"str_ls":true,"str_idb":true,"str_odb":false,"plgod":false,"plg":5,"plgne":true,"plgre":true,"plgof":false,"plggt":false,"pltod":false,"hcovdr":false,"plovdr":false,"ftsovdr":false,"hcovdr2":false,"plovdr2":false,"ftsovdr2":false,"lb":false,"eva":37,"lo":false,"ts_mtp":0,"ts_tec":false,"ts_tsa":false,"vnd":"","bid":"20181001000000","mmt":"application/pdf,text/pdf","plu":"PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF","hdn":false,"awe":false,"geb":false,"dat":false,"med":"defined","aco":"probably","acots":false,"acmp":"maybe","acmpts":false,"acw":"probably","acwts":false,"acma":"maybe","acmats":false,"acaa":"maybe","acaats":false,"ac3":"","ac3ts":false,"acf":"maybe","acfts":false,"acmp4":"maybe","acmp4ts":true,"acmp3":"maybe","acmp3ts":false,"acwm":"maybe","acwmts":true,"ocpt":false,"vco":"probably","vcots":false,"vch":"probably","vchts":true,"vcw":"probably","vcwts":true,"vc3":"","vc3ts":false,"vcmp":"","vcmpts":false,"vcq":"maybe","vcqts":false,"vc1":"probably","vc1ts":true,"dvm":4,"sqt":false,"so":"landscape-primary","wdw":true,"ecpc":false,"lgs":true,"lgsod":false,"psn":true,"edp":false,"addt":false,"wsdc":true,"ccsr":true,"nuad":false,"bcda":false,"idn":true,"capi":false,"svde":false,"vpbq":true,"ucdv":false,"spwn":false,"emt":false,"bfr":false,"dbov":false,"prm":true,"tzp":"UTC","cvs":true,"usb":"NA","jset":{jset},"dcok":".leboncoin.fr","es_sigmdn":{es_sigmdn},"es_mumdn":{es_mumdn},"es_distmdn":{es_distmdn},"es_angsmdn":{es_angsmdn},"es_angemdn":{es_angemdn}}}'.format(
                ttst=self.gen_random_ttst(60, 200),
                tagpu=self.gen_random_ttst(10, 40),
                ua=self.user_agent,
                glvd=self.glvd,
                glrd=self.glrd,
                jset=int(datetime.now().timestamp()),
                es_sigmdn=ddJsData['EsSigmdn'],
                es_mumdn=ddJsData['EsMumdn'],
                es_distmdn=ddJsData['EsDistmdn'],
                es_angsmdn=ddJsData['EsAngsmdn'],
                es_angemdn=ddJsData['EsAngemdn']
            ),
            'eventCounters': '{"mousemove":%d,"mouseclick":0,"scroll":0,"touchstart":0,"touchend":0,"touchmove":0,"keydown":0,"keyup":0}' % (random.randint(10,40)),
            'jsType': 'le',
            'cid': self.session.cookies.get('datadome', domain=self.domain),
            'ddk': ddk[self.dd_endpoint],
            'Referer': quote_plus(self.referer),
            'request': quote_plus(request_path),
            'responsePage': 'origin',
            'ddv': '4.6.15'
        }

        self.location('https://{}/js/'.format(self.dd_endpoint), method='POST', headers=headers, data=data)
        assert self.dd_leboncoin_page.is_here()

        name, value = self.page.get_cookies()
        self.session.cookies.set(name=name, value=value, domain=self.domain)
        self.set_random_token()

    def gen_random_ttst(self, start=15, end=30):
        # 29.300000071525574
        first = str(random.randint(start, end))
        second = str(random.randint(1, 10)) + "00" * random.randint(0, 3) + str(random.randint(10**7, 10**8))
        return first + "." + second

    @with_retries
    @with_bypass
    def go_to(self, link, html_only=False):
        try:
            extracted = tldextract.extract(link)
            self.domain = '.' + '.'.join([extracted.domain, extracted.suffix])
        except Exception as e:
            raise e
        # parse origin from link
        try:
            self.origin = urlparse(link).scheme + "://" + urlparse(link).netloc
        except Exception as e:
            raise e
        self.location(link)
        if html_only:
            return self.response.text
        return {
            "datadome": self.session.cookies.get('datadome')
        }

if __name__ == '__main__':
    b = DatadomeSolver()
    b.test()
