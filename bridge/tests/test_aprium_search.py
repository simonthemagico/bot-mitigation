import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import traceback

from modules.aprium_search import ApriumSearchByPass
import time

def test_aprium_bypass():
    print("=== Testing Louis Vuitton Akami Bypass ===")

    bypass = ApriumSearchByPass(
        proxy_pool="http://brd-customer-hl_f9eb8d89-zone-leboncoinnew20000-ip-213.159.12.120:bc37zhm96zj1@brd.superproxy.io:33335",
        url="https://notre-dame.pharmacie-monge.fr/recherche?categorie=Beaut%C3%A9|Corps|Soins%20hydratants",
        task_id="tk_test123",
        headless=False
    )

    try:
        print("\n1. Starting bypass process...")
        _, cookies, headers_dict, curl = bypass.bypass()

        print("\n2. Results:")
        # print(f"\nCookies received:")
        # for k, v in cookies.items():
        #     print(f"  {k}: {v}")

        print(f"\nCurl command:")
        print(curl)

        # print(f"\n headers: {headers_dict}")

        print("\nContent saved to louisvuitton_test.html")

    except Exception as e:
        t = traceback.format_exc()
        print(f"\nError during test: {e}, {t}")

if __name__ == "__main__":
     test_aprium_bypass()
