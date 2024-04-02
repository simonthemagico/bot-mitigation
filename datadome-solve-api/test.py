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
    'password': 'EWXv1a50bXfxc3vnsw',
    'username': 'user-sp0e9f6467',
    'port': 40005,
    'host': 'smartbalance2.com',
    'captchaUrl': 'https://www.idealista.com/',

}

response = post('http://localhost:8001/v1/createTask', json=data)
print(response.text)