# import os
# from dotenv import load_dotenv
# load_dotenv()
# from gologin import GoLogin, getRandomPort
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
# random_port = getRandomPort()

# gl = GoLogin({
#     'token': os.environ.get('GOLOGIN_API_KEY'),
#     'profile_id': os.environ.get('GOLOGIN_PROFILE'),
#     'port': random_port,
#     # 'executablePath': '/Users/apple/.gologin/browser/orbita-browser-120/Orbita-Browser.app/Contents/MacOS/Orbita',
# })

# address = gl.start()

# service = Service('/Users/apple/Downloads/bot-mitigation/chromedriver')


# options = Options()
# options.add_experimental_option("debuggerAddress", address)
# # driver = webdriver.Chrome(options=options)
# driver = webdriver.Chrome(options=options, service=service)

# driver.get("https://www.idealista.com/en/ajax/ads/99969147/contact-phones")

# print(address)
# input()

# driver.quit()
# gl.stop()


from requests import post


data = {
    'password': 'EWXv1a50bXfxc3vnsw',
    'username': 'user-sp0e9f6467',
    'port': 40002,
    'host': 'smartbalance2.com',
    'captchaUrl': 'https://www.idealista.com/en/ajax/ads/99969147/contact-phones',

}

response = post('http://localhost:8001/v1/createTask', json=data)
print(response.text)