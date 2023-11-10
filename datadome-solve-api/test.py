from api import create_task
import asyncio

captcha_url = 'https://geo.captcha-delivery.com/captcha/?initialCid=AHrlqAAAAAMAOrCI_A7YMg4AW6A3og==&hash=05B30BD9055986BD2EE8F5A199D973&cid=ZOpMeJSjxPdRvLH7ZAlN7Qj0247nZ5cuYnPW0YWx6TkSRq9U3YGayUmSgGjoaTU7nLr43ApRjW8rNKLW10NYhK3wr2pIkefayeH3epljWPDcSqkcDeJ339BLvYZozpZd&t=fe&referer=https%3A//www.leboncoin.fr/&s=2089&e=b3d7a8325e57a65c8744288824cc70acd551a7655ad4c159cb9b709303930431'
# captcha_url = 'https://www.leboncoin.fr'
asyncio.run(create_task(captcha_url))