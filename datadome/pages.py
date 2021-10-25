from monseigneur.core.browser.pages import HTMLPage, JsonPage
from monseigneur.core.browser.filters.json import Dict

import re
import json

class LeboncoinApiPage(JsonPage):
    pass

class GeoCaptchaPage(HTMLPage):
    
    def is_blocked(self):
        return len(self.doc.xpath('//div[contains(text(),"You have been blocked.")]')) > 0

    def get_challenge(self):
        return re.findall("challenge: '(.*?)',", self.text)[0]

    def get_gt(self):
        return re.findall("gt: '(.*?)',", self.text)[0]

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