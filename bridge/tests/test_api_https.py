import requests

# API Endpoint
URL = "https://api.bridge.lobstr.io/health"

# Authentication Token
TOKEN = "77f6bc041b99accf93093ebdc67a45ef472a4496"

# Headers with authentication
HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

def test_api_health():
    """Send a request to /health with authentication."""
    try:
        response = requests.get(URL, headers=HEADERS, timeout=10)
        response.raise_for_status()  # Raise an error for non-2xx responses

        print(f"✅ Success! Status Code: {response.status_code}")
        print(f"Response JSON: {response.json()}")

    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")

if __name__ == "__main__":
    test_api_health()
