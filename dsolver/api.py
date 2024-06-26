import json
from fastapi import FastAPI, Request, Response
from uuid import uuid4
import os
import threading
import pychrome
import random
from urllib.parse import unquote, quote

API_PORT = 8000


# create files/ directory if it doesn't exist
current_dir = os.path.dirname(os.path.realpath(__file__))
if not os.path.exists(current_dir + '/files'):
    os.makedirs(current_dir + '/files')

previous_dir = os.path.dirname(current_dir)
tasks = {}

app = FastAPI()

port = random.randint(9222, 9322)
# add extension ../extension
print(previous_dir)
os.system(f'"/usr/bin/google-chrome-stable" --remote-debugging-port={port} --load-extension={previous_dir}/extensionv2 --user-data-dir={previous_dir}/user-data-dir &')

# A simple method to create a browser tab and navigate to a URL
def create_browser_tab(url):
    browser = pychrome.Browser(url=f"http://127.0.0.1:{port}")
    tab = browser.new_tab()
    tab.start()
    tab.call_method("Network.enable")
    tab.call_method("Page.enable")
    tab.call_method("Page.navigate", url=url, _timeout=15)
    tab.wait(5)  # Wait for 5 seconds for the page to load
    return tab, browser

def process_url(task_id):
    task = tasks[task_id]
    url = task['url']
    tab, browser = create_browser_tab(url)
    for _ in range(10):
        if task['status'] == 'ready':
            break
        tab.wait(1)
    tab.stop()
    browser.close_tab(tab)


# verify by url
@app.post("/verify-browser")
async def verify_browser(request: Request):
    data = await request.json()
    url = data['url']
    cid = data['cid']
    print(cid)
    task_id = str(uuid4())
    tasks[task_id] = {
        'status': 'pending',
        'value': None,
        'cid': cid,
        'url': url,
    }
    # open a new thread to process the payload
    t = threading.Thread(target=process_url, args=(task_id,))
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
    body = data['body']
    payload = body['payload']
    print('is_payload')
    # turn 'k=v&k=v' into {'k': 'v', 'k': 'v'}
    json_data = {}
    urlparams = payload.split('&')
    for param in urlparams:
        try:
            key, value = param.split('=', 1)
        except:
            key, value = param, ''
        # urldecode
        json_data[key] = unquote(value)
    print(json_data)
    cid = data['hashedUrl']
    print(cid)
    # modify all tasks with the same cid
    for _, task in tasks.items():
        if task['cid'] == cid:
            task['value'] = json_data
            task['status'] = 'ready'

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)