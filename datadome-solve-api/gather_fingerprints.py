import requests
import secrets
import json
import time

headers = {
    'authority': 'api.gologin.com',
    'accept': '*/*',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqd3RpZCI6IjY1NTIwODgzNTFmZmFiODQyYTY3OTZhYiIsInR5cGUiOiJ1c2VyIiwic3ViIjoiNjU1MjA4ODM1MWZmYWIyOTIxNjc5NWZhIn0.5uTCEXGUdHTQW5i-pDW2EXTusIQaSnyxo8HzuA5ZxJI',
    'content-type': 'application/json',
    'gologin-meta-header': 'site-mac-10_15_7',
    'origin': 'https://app.gologin.com',
    'referer': 'https://app.gologin.com/',
    'sec-ch-ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'transaction-id': '',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    'x-two-factor-token': '',
}

params = {
    'os': 'mac',
    'isM1': 'true',
    'template': '655208c8bfa76b8683346f7c',
}

for _ in range(40):
    response = requests.get('https://api.gologin.com/browser/fingerprint', params=params, headers=headers)

    random_hash = secrets.token_hex(8)
    fingerprint_path = f"fingerprints/{random_hash}.json"
    assert response.status_code == 200, f"Failed to gather fingerprint: {response.text}"
    with open(fingerprint_path, "w", encoding="utf-8") as f:
        json.dump(response.json(), f, indent=2)

    print(f"Saved: {fingerprint_path}")
    time.sleep(1)