#!/usr/bin/env python3
# test_health.py

import requests

def test_health():
    API_TOKEN = "77f6bc041b99accf93093ebdc67a45ef472a4496"  # or your real token
    BASE_URL = "http://localhost:8000"                  # adjust if needed

    url = f"{BASE_URL}/health"
    headers = {
        "Authorization": f"Token {API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print("Status code:", response.status_code)
        print("Response JSON:", response.json())
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_health()
