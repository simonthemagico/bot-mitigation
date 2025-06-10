import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.louisvuitton_search import LouisVuittonSearchByPass

def test_louisvuitton_bypass():
    print("=== Testing Louis Vuitton Akami Bypass ===")

    bypass = LouisVuittonSearchByPass(
        proxy_pool="brd-customer-hl_f9eb8d89-zone-leboncoinnew20000:bc37zhm96zj1@brd.superproxy.io:33335",
        # proxy_pool="sp0e9f6467:EWXv1a50bXfxc3vnsw@fr.smartproxy.com:40001",  # residential_smartproxy
        # proxy_pool="spdicbst2v:h5b4tPbwbg4Nx8ZleU@fr.smartproxy.com:40001",  # mobile_smartproxy
        url="https://fr.louisvuitton.com/fra-fr/homme/portefeuilles-et-petite-maroquinerie/tous-les-portefeuilles-et-petite-maroquinerie/_/N-t1iazbp7",
        task_id="tk_test_new",
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
        print(f"\nError during test: {e}")

if __name__ == "__main__":
     test_louisvuitton_bypass()
