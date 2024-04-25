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


data = {
    "captchaUrl": "https://www.seloger.com/list.htm?projects=2&types=2,1,9&natures=1&places=[{%22subDivisions%22:[%2275%22]},{%22subDivisions%22:[%2292%22]}]&price=140000/NaN&surface=14/NaN&sort=d_dt_crea&mandatorycommodities=0&picture=15&enterprise=0&epc=E,D,C,B,A,F,G&qsVersion=1.0&m=search_refine-redirection-search_results",
    "host": "smartbalance2.com",
    "port": "43182",
    "username": "user-sp0e9f6467-sessionduration-30",
    "password": "EWXv1a50bXfxc3vnsw",
    "visit_home": True
}

for i in range(5):
    response = post('http://localhost:8001/v1/createTask', json=data)
    print(response.text)
    break