import os
import platform

current_dir = os.path.dirname(os.path.realpath(__file__))
previous_dir = os.path.dirname(current_dir)

API_PORT = 8000
CHROME_PORT = 9222

CHROME_PATH = '/usr/bin/google-chrome-stable'
if platform.system() == 'Darwin':
    CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

ALLOWED_HOSTS = [
    'leboncoin',
    'seloger',
    'datadome',
    'captcha-delivery',
    'yelp',
    'idealista',
    'leclerc'
]

# Create files/ directory if it doesn't exist
if not os.path.exists(current_dir + '/files'):
    os.makedirs(current_dir + '/files') 