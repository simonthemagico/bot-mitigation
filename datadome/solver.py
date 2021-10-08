import requests
import time
import json

API_KEY = "132069aefa859713ab15d5cd78e112a4"

class CaptchaNotSolvedException(Exception):
    pass

def solve_geecaptcha(gt, challenge, url):
    data = {
        "key": API_KEY,
        "method": "geetest",
        "gt": gt,
        "challenge": challenge,
        "pageurl": url,
        "api_server": "api-na.geetest.com",
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.3"
    }
    captcha_response = requests.post(
        "http://2captcha.com/in.php", json=data).text
    try:
        captcha_id = captcha_response.split('|')[1]
    except IndexError:
        print('[ERROR] Response:', captcha_response)
        raise CaptchaNotSolvedException(captcha_response)
    print('[CAPTCHA] ID : {}'.format(captcha_id))
    # then we parse gresponse from 2captcha response

    params = {
        "key": API_KEY,
        "action": "get",
        "id": captcha_id
    }
    geecaptcha_answer = requests.get(
        "http://2captcha.com/res.php", params=params).text
    print("[CAPTCHA] Status : Solving")
    while 'CAPCHA_NOT_READY' in geecaptcha_answer:
        time.sleep(2)
        geecaptcha_answer = requests.get(
            "http://2captcha.com/res.php", params=params).text
    try:
        geecaptcha_answer = '|'.join(geecaptcha_answer.split('|')[1:])
    except IndexError:
        print("Error: ", geecaptcha_answer)
        raise CaptchaNotSolvedException(geecaptcha_answer)
    print('[CAPTCHA] Answer : {}...'.format(geecaptcha_answer[0:10]))
    print(geecaptcha_answer)
    return json.loads(geecaptcha_answer)
