import os
import re
from urllib.parse import quote_plus, unquote

from monseigneur.core.browser.curl import PyCurlBrowser
from monseigneur.core.browser.exceptions import ClientError
from monseigneur.core.browser import URL
from monseigneur.core.tools.decorators import retry

from pages import DatadomeSdkPage, GeoCaptchaCheckPage, GeoCaptchaPage, LeboncoinApiPage
from solver import Speech2Text
from exceptions import IpBlockedError

from functools import wraps
import json

import js2py
from urllib.parse import quote
from json.decoder import JSONDecodeError

class DatadomeSolver(PyCurlBrowser):
    BASEURL = 'https://geo.captcha-delivery.com'

    leboncoin_api_page = URL(r'https://api.leboncoin.fr', LeboncoinApiPage)
    geo_captcha_check_page = URL(r'/captcha/check', GeoCaptchaCheckPage)
    geo_captcha_page = URL(r'/captcha/', GeoCaptchaPage)
    datadome_sdk_page = URL(r'https://api-sdk.datadome.co/sdk/', DatadomeSdkPage)
    dd_leboncoin_page = URL(r'https://dd.leboncoin.fr/js/', DatadomeSdkPage)

    def with_bypass(f):
        @wraps(f)
        def wrapped(self, *args, **kwargs):
            try:
                return f(self, *args, **kwargs)
            except ClientError as e:
                if e.response.status_code != 403:
                    raise ClientError(e.response.status_code) from e
                try:
                    url = json.loads(e.response.text).get('url')
                except JSONDecodeError:
                    match = re.findall(r"'cid':'(?P<initialCid>.+?)','hsh':'(?P<hash>[0-9A-Z]+)','t':'(?P<te>[a-z]+)','s':(?P<s>\d+)", e.response.text)
                    if match:
                        cid = self.session.cookies.get_dict().get('datadome')
                        initialCid, _hash, t, s  = match[0]
                        url = 'https://geo.captcha-delivery.com/captcha/?initialCid={initialCid}&hash={hash}&cid={cid}&t={t}&referer={referer}&s={s}' \
                                    .format(
                                        initialCid=initialCid,
                                        cid=cid,
                                        hash=_hash,
                                        t=t,
                                        s=s,
                                        referer=quote(e.response.url)
                                    )
                        self.logger.warning("captcha: " + url)
                    else:
                        raise Exception("NoMatchError")
                assert url
                self.bypass_page(url)
                raise e
        return wrapped

    def bypass_page(self, link):
        self.session.cookies.clear()

        self.location(link)
        assert self.geo_captcha_page.is_here()

        icid = re.findall(r'initialCid=(.+?)&', link)[0]
        cid = re.findall(r'cid=(.+?)&', link)[0]
        referer = unquote(re.findall(r'referer=(.+?)&', link)[0])
        hash = re.findall(r'hash=(.+?)&', link)[0]
        s = re.findall(r's=(.+?)$', link)[0]

        self.params = {
            'cid': cid,
            'icid': icid,
            'ccid': 'null',
            # ('geetest-response-challenge', '4d38e776c64553d728b08362d2236003jd'),
            # ('geetest-response-validate', '0111ce6f2cd4f7f81d9db999d4d8bf66'),
            # ('geetest-response-seccode', '0111ce6f2cd4f7f81d9db999d4d8bf66|jordan'),
            'hash': hash,
            # ('ua', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36'),
            'referer': referer,
            'parent_url': link,
            'x-forwarded-for': '',
            's': s,
        }

        self.params['captchaChallenge'] = self.get_id()
        self.solve()

    def get_id(self):
        script = """
        function getCaptchaID(t,r){function e(t,r,e){this.seed=t,this.currentNumber=t%r,this.offsetParameter=r,this.multiplier=e,this.currentNumber<=0&&(this.currentNumber+=r)}e.prototype.getNext=function(){return this.currentNumber=this.multiplier*this.currentNumber%this.offsetParameter,this.currentNumber};for(var n=[function(t,r){var e=0;if(s="VEc5dmEybHVaeUJtYjNJZ1lTQnFiMkkvSUVOdmJuUmhZM1FnZFhNZ1lYUWdZWEJ3YkhsQVpHRjBZV1J2YldVdVkyOGdkMmwwYUNCMGFHVWdabTlzYkc5M2FXNW5JR052WkdVNklERTJOMlJ6YUdSb01ITnVhSE0",navigator.userAgent){for(var n=0;n<s.length;n+=1%Math.ceil(1+3.1425172/navigator.userAgent.length))e+=s.charCodeAt(n).toString(2)|26157^r;return e}return s^r},function(t,r){for(var e=(navigator.userAgent.length<<Math.max(t,3)).toString(2),n=-42,a=0;a<e.length;a++)n+=e.charCodeAt(a)^r<<a%3;return n},function(t,r){for(var e=0,n=(navigator.language?navigator.language.substr(0,2):void 0!==navigator.languages?navigator.languages[0].substr(0,2):"default").toLocaleLowerCase()+r,a=0;a<n.length;a++)e=((e=((e+=n.charCodeAt(a)<<Math.min((a+r)%(1+t),2))<<3)-e+n.charCodeAt(a))&e)>>a;return e}],a=new e(function(t){for(var r=126^t.charCodeAt(0),e=1;e<t.length;e++)r+=(t.charCodeAt(e)*e^t.charCodeAt(e-1))>>e%2;return r}(t),1723,7532),u=a.seed,i=0;i<r;i++)u^=(0,n[a.getNext()%n.length])(i,a.seed);return u}
        getCaptchaID("thisisgoingtobecid", 10)
        """ \
           .replace("navigator.userAgent", "'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'") \
           .replace("thisisgoingtobecid", self.params.get("cid")) \
           .replace("navigator.languages", "['en-GB', 'en-US', 'en']") \
           .replace("navigator.language", "'en-GB'")

        captchaID = js2py.eval_js(script)
        print(len(str(captchaID)))
        # assert len(str(captchaID)) == 9
        return captchaID

    def solve(self):
        blocked = self.page.is_blocked()
        if blocked:
            raise IpBlockedError

        challenge = self.page.get_challenge()
        gt = self.page.get_gt()

        s2t = Speech2Text(gt=gt, challenge=challenge, apikey="fJpBTCWBnvcBJ551_qXAcnnr9gH9XYKOKI9EXMXb6VyC")
        solved_response = s2t.run()

        self.params.update(solved_response)
        self.params['ua'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'

        self.location('https://geo.captcha-delivery.com/captcha/check', params=self.params)
        assert self.geo_captcha_check_page.is_here()

        name, value = self.page.get_cookies()
        self.session.cookies.set(name=name, value=value, domain=".leboncoin.fr")
        self.validate_cookies_website()

    def validate_cookies_website(self):
        headers = {
            'authority': 'dd.leboncoin.fr',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36',
            'content-type': 'application/x-www-form-urlencoded',
            'accept': '*/*',
            'sec-gpc': '1',
            'origin': 'https://www.leboncoin.fr',
            'referer': 'https://www.leboncoin.fr/',
            'accept-language': 'en-GB,en;q=0.9',
        }

        data = {
            'jsData': '{"ttst":29.300000071525574,"ifov":false,"wdifts":false,"wdifrm":false,"wdif":false,"br_h":726,"br_w":571,"br_oh":805,"br_ow":1440,"nddc":1,"rs_h":900,"rs_w":1440,"rs_cd":30,"phe":false,"nm":false,"jsf":false,"ua":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36","lg":"en-GB","pr":2,"hc":8,"ars_h":806,"ars_w":1440,"tz":-330,"str_ss":true,"str_ls":true,"str_idb":true,"str_odb":true,"plgod":false,"plg":5,"plgne":"NA","plgre":"NA","plgof":"NA","plggt":"NA","pltod":false,"hcovdr":false,"plovdr":false,"ftsovdr":false,"lb":false,"eva":33,"lo":false,"ts_mtp":0,"ts_tec":false,"ts_tsa":false,"vnd":"Google Inc.","bid":"NA","mmt":"application/pdf,text/pdf","plu":"PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF","hdn":false,"awe":false,"geb":false,"dat":false,"med":"defined","aco":"probably","acots":false,"acmp":"probably","acmpts":true,"acw":"probably","acwts":false,"acma":"maybe","acmats":false,"acaa":"probably","acaats":true,"ac3":"","ac3ts":false,"acf":"probably","acfts":false,"acmp4":"maybe","acmp4ts":false,"acmp3":"probably","acmp3ts":false,"acwm":"maybe","acwmts":false,"ocpt":false,"vco":"probably","vcots":false,"vch":"probably","vchts":true,"vcw":"probably","vcwts":true,"vc3":"maybe","vc3ts":false,"vcmp":"","vcmpts":false,"vcq":"","vcqts":false,"vc1":"probably","vc1ts":false,"dvm":8,"sqt":false,"so":"landscape-primary","wbd":false,"wbdm":true,"wdw":true,"cokys":"bG9hZFRpbWVzY3NpYXBwcnVudGltZQ==L=","ecpc":false,"lgs":true,"lgsod":false,"bcda":true,"idn":true,"capi":false,"svde":false,"vpbq":true,"xr":true,"bgav":true,"rri":true,"idfr":true,"ancs":true,"inlc":true,"cgca":true,"inlf":true,"tecd":true,"sbct":true,"aflt":true,"rgp":true,"bint":true,"spwn":false,"emt":false,"bfr":false,"dbov":false,"glvd":"Apple","glrd":"Apple M1","tagpu":18.600000023841858,"prm":true,"tzp":"Europe/Paris","cvs":true,"usb":"defined"}',
            'events': '[]',
            'eventCounters': '[]',
            'jsType': 'ch',
            'cid': self.session.cookies.get('datadome'),
            'ddk': '05B30BD9055986BD2EE8F5A199D973',
            'Referer': quote_plus(self.url) if 'https://www.leboncoin.fr' in self.url else 'https%3A%2F%2Fwww.leboncoin.fr%2F',
            'request': quote_plus(self.url.replace('https://www.leboncoin.fr', '')) if 'https://www.leboncoin.fr' in self.url else '%2F',
            'responsePage': 'origin',
            'ddv': '4.1.66'
        }
        self.location('https://dd.leboncoin.fr/js/', method='POST', headers=headers, data=data)
        assert self.dd_leboncoin_page.is_here()

        name, value = self.page.get_cookies()
        self.session.cookies.set(name=name, value=value, domain=".leboncoin.fr")

    def validate_cookies(self):
        data = {
            'cid': self.session.cookies.get('datadome', ''),
            'ddv': '1.6.5',
            'ddvc': '5.38.0',
            'ddk': '05B30BD9055986BD2EE8F5A199D973',
            'request': 'https://api.leboncoin.fr/appsdata/config/android/5.38.0',
            'os': 'Android',
            'osr': '11',
            'osn': 'R',
            'osv': '30',
            'ua': 'LBC;Android;11;M2102J20SI;phone;f43b016eabccf179;wifi;5.38.0;538000;0',
            'screen_x': '1080',
            'screen_y': '2265',
            'screen_d': '440',
            'events': '[{"id":1,"message":"response validation", "source":"sdk","date":1634555948075}]',
            'camera': '''{"auth":"false", "info":"{}"}''',
            'mdl': 'M2102J20SI',
            'prd': 'bhima_global',
            'mnf': 'Xiaomi',
            'dev': 'bhima',
            'hrd': 'qcom',
            'fgp': 'POCO/vayu_global/vayu:11/RKQ1.200826.002/V12.5.4.0.RJUMIXM:user/release-keys',
            'tgs': 'release-keys'
        }
        headers = {
            'Host': 'api-sdk.datadome.co',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'okhttp/4.9.0',
            'Connection': 'close',
        }
        self.location('https://api-sdk.datadome.co/sdk/', headers=headers, data=data, method='POST')
        assert self.datadome_sdk_page.is_here()

        name, value = self.page.get_cookies()
        self.session.cookies.set(name=name, value=value, domain=".leboncoin.fr")

    @retry(ClientError, tries=2, delay=2, backoff=0)
    @with_bypass
    def test_finder_search(self):
        self.session.PROXIES = {
            "host": "fr.smartproxy.com",
            "port": 47820,
            "username": "user-tytytyty-sessionduration-30",
            "password": "altius2010"
        }
        r = self.location("https://ipecho.net/plain")
        print("IP:", r.text)

        self.session.headers.update({
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36'
        })

        self.location('https://www.leboncoin.fr')
        self.validate_cookies_website()

        data = {"owner_type":"all","limit":35,"limit_alu":3,"sort_by":"relevance","sort_order":"desc","filters":{"enums":{"ad_type":["offer"]}},"offset":0}
        self.location('https://api.leboncoin.fr/finder/search', method='POST', json=data)

        data = {
            "app_id": "leboncoin_web_utils",
            "key": "54bb0281238b45a03f0ee695f73e704f",
            "list_id": "2030643854",
            "text": "1"
        }

        self.session.headers.update({
            "content-type": "application/x-www-form-urlencoded",
            'referer': 'https://www.leboncoin.fr/'
        })

        self.location('https://api.leboncoin.fr/api/utils/phonenumber.json', data=data, method='POST')

if __name__ == "__main__":
    if os.path.exists("test"):
        os.system("rm -rf test")
    
    b = DatadomeSolver(responses_dirname='test')
    # b.go_page('https://geo.captcha-delivery.com/captcha/?initialCid=AHrlqAAAAAMAt1hnSzlWsHsALU2VKg==&cid=PkKPAE75S5Dam6-yBgKcyL8RQOjrudmJ_wBL.B7uEOsZZc~TBYwpFM6c4HJ_Nl4EZD92nkKjygVWYonRqslnQfJVSMBPSY_kwx3U_MBmjO&referer=https%3A%2F%2Fapi.leboncoin.fr%2Ffinder%2Fsearch&hash=05B30BD9055986BD2EE8F5A199D973&t=fe&s=7501')
    # b.solve()
    b.test_finder_search()
