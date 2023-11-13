from __future__ import unicode_literals

from matrix.modules.leboncoin_matrix.alchemy.annonces.tables import Result
from monseigneur.core.browser.pages import HTMLPage, JsonPage
from monseigneur.core.capabilities.base import Currency as BaseCurrency
from monseigneur.core.browser.filters.standard import CleanText, CleanDecimal, Field
from monseigneur.core.browser.filters.json import Dict
from monseigneur.core.capabilities.base import NotAvailable
from monseigneur.core.exceptions import BrowserBanned
from monseigneur.core.browser.elements import method, ListElement, ItemElement

from datetime import datetime
from pytz import timezone
import math
import re
import json

class GeoCaptchaPage(HTMLPage):

    def is_blocked(self):
        return len(re.findall("challenge: '(.*?)',", self.text)) == 0

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
