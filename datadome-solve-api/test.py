# from gologin import GoLogin

# gl = GoLogin({
#     'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2NTUzOWVmMDhiYjk4NTE1MGFjODQxZGIiLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2NTU2MmJmNDJiNzUwYTk0MmM4MDZiMDYifQ.hi0HYSUvBkGSEO32J411xnq2dygdQLyJBQZjoeyBLzI',
#     'profile_id': '660bffa4e460d05bf289275a',
# })

# address = gl.start()


# print(address)
# input()

# gl.stop()


from requests import post

#https://geo.captcha-delivery.com/captcha/?initialCid=AHrlqAAAAAMA-ZVwX4EqCuUATYEVuA%3D%3D&hash=77D81445BE5A1B811A597604196595&cid=ND~xwR_1JfdSJ2dhjAjWOQK3BEhwdJtMD9Cr6OhxdH~1YCi6HDzRwiIvFedZJDmer7IAADdMiruasrch5tQqdEUMsmV6d7tv3thXYRRwJfFeos6E_f6J3ZUVZBcRc8BM&t=fe&referer=https%3A%2F%2Fwww.seloger.com%2Flist.htm%3Fprojects%3D2%26types%3D2%2C1%2C9%26natures%3D1%26places%3D%5B%7B%2522subDivisions%2522%3A%5B%252275%2522%5D%7D%2C%7B%2522subDivisions%2522%3A%5B%252292%2522%5D%7D%5D%26price%3D140000%2FNaN%26surface%3D14%2FNaN%26sort%3Dd_dt_crea%26mandatorycommodities%3D0%26picture%3D15%26enterprise%3D0%26epc%3DE%2CD%2CC%2CB%2CA%2CF%2CG%26qsVersion%3D1.0%26m%3Dsearch_refine-redirection-search_results&s=24172&e=7b63f20bb7d4860342e2df0f0bab7aa5adb1077485d727f5e4c7a2d7564da65f&dm=cd
data = {
    "captchaUrl": "https://www.seloger.com/list.htm?projects=2&types=2,4,1,12,11,14,10&natures=1&places=[{%22inseeCodes%22:[350238]}]&surface=80/NaN&mandatorycommodities=0&enterprise=0&qsVersion=1.0&m=search_refine-redirection-search_results",
    # "captchaUrl": "https://www.seloger.com",
    "host": "smartbalance2.com",
    "port": "43182",
    "username": "user-sp0e9f6467-sessionduration-30",
    "password": "EWXv1a50bXfxc3vnsw",
    "visit_home": True,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.110 Safari/537.36"
}

for i in range(5):
    response = post('http://localhost:8001/v1/createTask', json=data)
    print(response.text)
    break