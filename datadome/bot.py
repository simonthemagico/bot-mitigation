import os
import re
from urllib.parse import unquote
from monseigneur.core.browser.curl import PyCurlBrowser
from monseigneur.core.browser.exceptions import ClientError
from monseigneur.core.browser import URL
from monseigneur.core.tools.decorators import retry

from pages import GeoCaptchaCheckPage, GeoCaptchaPage, LeboncoinApiPage
from solver import solve_geecaptcha
from exceptions import IpBlockedError

from functools import wraps
import json

import js2py

class DatadomeSolver(PyCurlBrowser):
    BASEURL = 'https://geo.captcha-delivery.com'

    leboncoin_api_page = URL(r'https://api.leboncoin.fr', LeboncoinApiPage)
    geo_captcha_check_page = URL(r'/captcha/check', GeoCaptchaCheckPage)
    geo_captcha_page = URL(r'/captcha/', GeoCaptchaPage)

    def with_bypass(f):
        @wraps(f)
        def wrapped(self, *args, **kwargs):
            try:
                return f(self, *args, **kwargs)
            except ClientError as e:
                url = json.loads(e.response.text).get('url')
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

        captcha_answer = solve_geecaptcha(gt, challenge, self.url)

        self.params.update({
            'geetest-response-challenge': captcha_answer['geetest_challenge'],
            'geetest-response-validate': captcha_answer['geetest_validate'],
            'geetest-response-seccode': captcha_answer['geetest_seccode']
        })
        self.params['ua'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'

        self.location('https://geo.captcha-delivery.com/captcha/check', params=self.params)
        assert self.geo_captcha_check_page.is_here()

        name, value = self.page.get_cookies()
        self.session.cookies.set(name=name, value=value)

    @retry(ClientError, tries=2, delay=2, backoff=0)
    @with_bypass
    def test_finder_search(self):
        self.session.PROXIES = {
            "host": "45.77.149.42",
            "port": 22222,
            "username": "user-uuid-7860342afef5499895c14de9cf41479c",
            "password": "f5126f25316b"
        }
        r = self.location("https://ipecho.net/plain")
        print("IP:", r.text)
        self.location('https://api.leboncoin.fr/finder/search')

if __name__ == "__main__":
    if os.path.exists("test"):
        os.system("rm -rf test")
    
    b = DatadomeSolver(responses_dirname='test')
    # b.go_page('https://geo.captcha-delivery.com/captcha/?initialCid=AHrlqAAAAAMAt1hnSzlWsHsALU2VKg==&cid=PkKPAE75S5Dam6-yBgKcyL8RQOjrudmJ_wBL.B7uEOsZZc~TBYwpFM6c4HJ_Nl4EZD92nkKjygVWYonRqslnQfJVSMBPSY_kwx3U_MBmjO&referer=https%3A%2F%2Fapi.leboncoin.fr%2Ffinder%2Fsearch&hash=05B30BD9055986BD2EE8F5A199D973&t=fe&s=7501')
    # b.solve()
    b.test_finder_search()
