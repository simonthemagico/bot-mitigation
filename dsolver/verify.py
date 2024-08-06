import json
import random
import time
import traceback
import urllib
import urllib.parse
import tls_client
import requests
import platform


host_api_url = 'http://localhost:8000'
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
randomLang = "de-DE,de;q=0.9"
if platform.system() == 'Darwin':
    ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'



def get_datadome_flow():
    try:
        session = tls_client.Session(client_identifier='chrome_120', random_tls_extension_order=True)
        proxies = """smartbalance2.com:49990:user-sp0e9f6467-sessionduration-30:EWXv1a50bXfxc3vnsw
smartbalance2.com:49991:user-sp0e9f6467-sessionduration-30:EWXv1a50bXfxc3vnsw
smartbalance2.com:49992:user-sp0e9f6467-sessionduration-30:EWXv1a50bXfxc3vnsw
smartbalance2.com:49993:user-sp0e9f6467-sessionduration-30:EWXv1a50bXfxc3vnsw
smartbalance2.com:49994:user-sp0e9f6467-sessionduration-30:EWXv1a50bXfxc3vnsw
smartbalance2.com:49995:user-sp0e9f6467-sessionduration-30:EWXv1a50bXfxc3vnsw
smartbalance2.com:49996:user-sp0e9f6467-sessionduration-30:EWXv1a50bXfxc3vnsw
smartbalance2.com:49997:user-sp0e9f6467-sessionduration-30:EWXv1a50bXfxc3vnsw
smartbalance2.com:49998:user-sp0e9f6467-sessionduration-30:EWXv1a50bXfxc3vnsw
smartbalance2.com:49999:user-sp0e9f6467-sessionduration-30:EWXv1a50bXfxc3vnsw""".splitlines()
        proxy = random.choice(proxies)
        proxy = proxy.split(':')
        print(proxy)
        session.proxies = {'https': f'http://{proxy[2]}:{proxy[3]}@{proxy[0]}:{proxy[1]}',
                           'http': f'http://{proxy[2]}:{proxy[3]}@{proxy[0]}:{proxy[1]}'}

        main_url = 'https://www.seloger.com'

        url = main_url

        request_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9,ur-PK;q=0.8,ur;q=0.7',
            'cache-control': 'max-age=0',
            'priority': 'u=0, i',
            'sec-ch-device-memory': '8',
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'sec-ch-ua-arch': '"x86"',
            'sec-ch-ua-full-version-list': '"Not/A)Brand";v="8.0.0.0", "Chromium";v="126.0.0.0", "Google Chrome";v="126.0.0.0"',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': ua,
        }
        # check if the dd cookie is not valid on first request
        response = session.get(url, headers=request_headers)

        if response.status_code != 200:
            # print(response.text)
            print(response)
        else:
            print('200 response')
            return

        if 't=bv' in response.text:
            print('proxy ban')
            return

        if response.status_code == 200:
            print('no invalid dd cookie')
        is_slider = False
        if 'https://geo.captcha-delivery.com/captcha/?initial' in response.text:
            response = json.loads(response.text)
            redirect = response['url']
            old_cookie = session.cookies.get('datadome')
            is_slider = True
        else:
            """ This part is building the interstitial url which is needed to 
                request to get the interstitial html
            """
            old_cookie = session.cookies.get('datadome')
            redirect, is_slider = build_url(response.text, old_cookie, main_url)
            print(redirect)
        """ This part is getting the interstitial payload
        """
        if '/captcha' in redirect:
            redirect = main_url
        start_time = time.time()
        payload = get_datadome_payload(redirect, old_cookie, f'{proxy[2]}:{proxy[3]}@{proxy[0]}:{proxy[1]}')
        end_time = time.time()
        headers = {
            "Host": "geo.captcha-delivery.com",
            "User-Agent": ua,
            "Accept": "*/*",
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            "Origin": "https://geo.captcha-delivery.com",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        print(payload)
        if isinstance(payload, dict):
            if 'blocked' in payload:
                print('blocked')
                raise Exception('Blocked')
            if payload.get('payload'):
                print("Interstital Payload")
                payload['referer'] = main_url
                payload['dm'] = 'cd'
                url = 'https://geo.captcha-delivery.com/interstitial/'
                """ posting payload from api to interstitial endpoint
                """
                res = session.post(url, headers=headers, data=payload)
            else:
                print("Good Cookie Directly")
                class Response:
                    def __init__(self, text):
                        datadome = text['datadome']
                        self.text = f'{{"cookie":"datadome={datadome}"}}'
                    def __str__(self):
                        return "<Response [200]>"
                res = Response(payload)
        elif payload.startswith('http'):
            print("Slider Payload")
            url = 'https://geo.captcha-delivery.com/captcha/check'
            """ posting payload from api to captcha endpoint
            """
            res = session.get(payload, headers=headers)
        else:
            raise Exception('Invalid payload')
        print(res)
        print('generated dd cookie')
        print(res.text)
        response = json.loads(res.text)
        cookie = response['cookie'].split('; ')[0].split('=')[1]
        """ setting the cookie
        """
        session.cookies.set(name='datadome', value=cookie, domain='.seloger.com', path='/')

        url = main_url
        # checking if cookie is valid
        response = session.get(url, headers=request_headers)
        print(response)

        # if the status code is 302 or 200, the cookie is valid
        if response.status_code == 200 or response.status_code == 302:
            print('successfully solved ' + 'captcha' if is_slider else 'interstitial')
            print("--- %s seconds ---" % (end_time - start_time))
        else:
            old_cookie = session.cookies.get('datadome')
            print(build_url(response.text, old_cookie, main_url))
            print('error genning cookie')

    except Exception as error:
        traceback.print_exc()
        print(error)


def get_datadome_payload(curl, cid, proxy):
    """
    # Get the interstitial payload from the host api

    :param url:
    :param cid:
    :return interstitial payload:
    """
    print('trying to get dd payload')
    url = host_api_url + '/verify-browser'
    headers = {
        'Content-Type': 'application/json'
    }

    license_key = 'bf25aecf-f3f8-4bf9-9488-7b94dfcee77c'

    payload = {
        'url': curl,
        'cid': cid,
        'proxy': proxy
    }
    res = requests.post(url, headers=headers, json=payload)

    if res.status_code != 200:
        raise Exception('Failed to post payload')

    while True:
        url = host_api_url + '/get-payload'
        payload = {
            'task_id': res.json().get('task_id'),
            'license_key': license_key
        }
        res = requests.post(url, headers=headers, json=payload)
        response = json.loads(res.text)
        if response['status'] == 'ready':
            return response['value']
        if response['status'] == 'error':
            raise Exception('Failed to get payload')
        time.sleep(0.5)


def build_url(script, old_cookie, url):
    """
    # Build the url for the interstitial

    :param script:
    :param old_cookie:
    :param url:
    :return redirect url:
    """
    data = script.split('var dd=')[1].split('</script')[0].strip().replace("'", '"')
    data: dict = json.loads(data)

    params = {
        'initialCid': data['cid'],
        'hash': data['hsh'],
        'cid': old_cookie,
        'referer': url,
        's': data['s'],
        'dm': 'cd'
    }
    if data['rt'] == 'i':
        params.update({
            'b': data['b'],
        })
    if data['rt'] == 'c':
        params.update({
            't': data['t'],
            'e': data['e'],
        })

    if data.get('cp') and data['cp']['name'] and data['cp']['value']:
        params[data['cp']['name']] = data['cp']['value']
    endpoint = 'captcha' if data['rt'] == 'c' else 'interstitial'
    params = urllib.parse.urlencode(params, doseq=True)
    redirect = f'https://{data["host"]}/{endpoint}/?{params}'

    return redirect, data['rt'] == 'c'


if __name__ == '__main__':
    get_datadome_flow()
