import json
import signal

import subprocess
import time
from fastapi import FastAPI, Request, Response
from uuid import uuid4
import os
import threading
import pychrome
from urllib.parse import unquote, urlparse
import tempfile
import platform

API_PORT = 8000


# create files/ directory if it doesn't exist
current_dir = os.path.dirname(os.path.realpath(__file__))
if not os.path.exists(current_dir + '/files'):
    os.makedirs(current_dir + '/files')

previous_dir = os.path.dirname(current_dir)

CHROME_PATH = '/usr/bin/google-chrome-stable'
if platform.system() == 'Darwin':
    CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

CHROME_PORT = 9222
# add extension ../extension
os.system(f'"{CHROME_PATH}" --remote-debugging-port={CHROME_PORT} --load-extension={previous_dir}/extensionv2 --user-data-dir={previous_dir}/user-data-dir &')

tasks = {}

app = FastAPI()

def get_new_tab(browser):
    tab = browser.new_tab()
    tab.start()
    tab.call_method("Network.enable")
    tab.call_method("Page.enable")
    tab.call_method("Network.clearBrowserCookies")
    return tab

# add extension ../extension
# A simple method to create a browser tab and navigate to a URL
def create_browser_tab(url, cid, port, extensions):
    url_obj = urlparse(url)
    browser = pychrome.Browser(url=f"http://127.0.0.1:{port}")
    if 'captcha-delivery' not in url_obj.hostname:
        tab = get_new_tab(browser)
        render_url = f'http://localhost:{API_PORT}/render?extension_id={extensions[0]["id"]}&hash={cid}'
        tab.call_method("Page.navigate", url=render_url, _timeout=5)
        tab.wait(2)
        tab.stop()
        browser.close_tab(tab)
    tab = get_new_tab(browser)
    # add datadome={cid} as cookie to browser
    tab.call_method("Network.setCookie", name='datadome', value=cid, domain=url_obj.hostname.replace('www.', ''), path='/', secure=True)
    tab.call_method("Page.navigate", url=url, _timeout=15)
    # set localStorage.setItem('hash', 'cid')
    tab.call_method("Runtime.evaluate", expression=f"localStorage.setItem('hash', '{cid}')")
    tab.wait(5)  # Wait for 5 seconds for the page to load
    return tab, browser

def get_installed_extensions(user_data_dir):
    for prefix in ['', 'Secure ']:
        preferences_path = os.path.join(user_data_dir, 'Default', f'{prefix}Preferences')
        print(preferences_path)
        # Wait until the Preferences file is created
        max_wait_time = 20  # seconds
        start_time = time.time()
        while not os.path.exists(preferences_path):
            if time.time() - start_time > max_wait_time:
                raise FileNotFoundError(f"Preferences file not found in {max_wait_time} seconds.")
            time.sleep(1)

        with open(preferences_path, 'r') as file:
            preferences = json.load(file)

        extensions = preferences.get('extensions', {}).get('settings', {})
        if extensions:
            break
    assert extensions, "No extensions found in Preferences file"
    installed_extensions = []

    for ext_id, ext_info in extensions.items():
        if ext_info.get('state') == 1:  # Check if the extension is enabled
            extension_name = ext_info.get('manifest', {}).get('name')
            # check if path has previous_dir in it
            if previous_dir in ext_info.get('path', ''):
                installed_extensions.append({
                    'id': ext_id,
                    'name': extension_name
                })

    return installed_extensions

def handle_captcha(url, cid, port, extensions, task):
    try:
        tab, browser = create_browser_tab(url, cid, port, extensions)
        for _ in range(30):
            if task['status'] == 'ready':
                break
            tab.wait(1)
        if task['status'] != 'ready':
            task['status'] = 'error'
        tab.stop()
        browser.close_tab(tab)
    except Exception as e:
        print(e)
        task['status'] = 'error'
        raise e

def process_url(task_id, cid, proxy):
    tmpdirname = tempfile.mkdtemp()
    # find open port
    port = 9223
    while True:
        try:
            subprocess.check_output(f'lsof -i:{port}', shell=True)
            port += 1
        except:
            break
        if port > 9322:
            raise Exception('No open ports found')
    print("Using port", port)
    proxy_command = [
        'proxy',
        '--proxy-pool', proxy,
        '--port', str(port-1000),
        '--plugins', 'restrict_by_host_upstream.RestrictHostUpstream,proxy.plugin.ProxyPoolPlugin',
        '--restrict-by-host-upstream', '.*(seloger|datadome|captcha-delivery).*',
    ]
    process = subprocess.Popen(proxy_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        commands = [
            CHROME_PATH,
            f'--remote-debugging-port={port}',
            f'--load-extension={previous_dir}/extensionv2',
            f'--user-data-dir={tmpdirname}',
            f'--proxy-server=http://127.0.0.1:{port-1000}',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-default-apps',
        ]
        p = subprocess.Popen(commands, start_new_session=True)
        task = tasks[task_id]
        url = task['url']
        try:
            extensions = get_installed_extensions(tmpdirname)
            handle_captcha(url, cid, port, extensions, task)
        except Exception as e:
            print(e)
            task['status'] = 'error'
        finally:
            print('killing process')
            p.kill()
        if process.poll() is None:
            os.kill(process.pid, signal.SIGINT)
            process.communicate()
    finally:
        print('terminating process')
        process.terminate()
        process.wait()
    os.system(f'rm -rf {tmpdirname}')

# hash=value&hash=value
@app.get('/render')
def render(request: Request):
    data = request.query_params
    # html that sends the payload to the extension using chrome api
    extension_id = data['extension_id']
    hash_ = data['hash']
    html = f"""
    <html>
    <head>
    <script>
    function sendPayload() {{
        chrome.runtime.sendMessage('{extension_id}', {{message: 'store', 'hash': "{hash_}"}});
        console.log('sent payload');
    }}
    setTimeout(sendPayload, 1000);
    </script>
    </head>
    <body onload="sendPayload()">
    </body>
    </html>
    """
    return Response(content=html, media_type="text/html")

# verify by url
@app.post("/verify-browser")
async def verify_browser(request: Request):
    data = await request.json()
    url = data['url']
    cid = data['cid']
    proxy = data['proxy']
    task_id = str(uuid4())
    tasks[task_id] = {
        'status': 'pending',
        'value': None,
        'cid': cid,
        'url': url,
    }
    func = process_url
    args = (task_id, cid, proxy)
    if 'captcha-delivery' in url:
        func = handle_captcha
        args = (url, cid, CHROME_PORT, [], tasks[task_id])
    # open a new thread to process the payload
    t = threading.Thread(target=func, args=args)
    t.start()
    tasks[task_id]['status'] = 'processing'
    return {
        'task_id': task_id,
    }


@app.post("/get-payload")
async def get_datadome(request: Request):
    data = await request.json()
    task_id = data['task_id']
    if task_id not in tasks:
        return {
            'status': 'error',
            'value': 'task_id not found',
            'task_id': task_id,
        }
    return {
        'status': tasks[task_id]['status'],
        'value': tasks[task_id]['value'],
        'task_id': task_id,
    }

# listen for any incoming requests starting with /task-<task_id>
@app.get("/task-{task_id}")
def get_task(task_id: str):
    if task_id not in tasks:
        return {
            'status': 'error',
            'value': 'task_id not found',
            'task_id': task_id,
        }
    task = tasks[task_id]
    cid = task['cid']
    with open(f'{current_dir}/files/{cid}.html', 'r') as f:
        script = f.read()
    # render the html
    return Response(content=script, media_type="text/html")

@app.post("/v1/response")
async def response(request: Request):
    data = await request.json()
    print(data)
    body = data['body']
    payload = body['payload']
    # turn 'k=v&k=v' into {'k': 'v', 'k': 'v'}
    json_data = payload
    if not payload.startswith('http'):
        json_data = {}
        urlparams = payload.split('&')
        for param in urlparams:
            try:
                key, value = param.split('=', 1)
            except:
                key, value = param, ''
            # urldecode
            json_data[key] = unquote(value)
    cid = data['hashedUrl'] or ''
    # modify all tasks with the same cid
    for _, task in tasks.items():
        if task['cid'] == cid:
            # if task is /captcha then do not accept payload
            if 'captcha-delivery' not in task['url'] and isinstance(json_data, dict) and json_data.get('payload'):
                continue
            if isinstance(json_data, dict) and cid in json_data.get('datadome', ''):
                continue
            task['value'] = json_data
            task['status'] = 'ready'

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)