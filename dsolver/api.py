from fastapi import FastAPI, Request, Response
from uuid import uuid4
import os
import threading
import pychrome
import random


# create files/ directory if it doesn't exist
current_dir = os.path.dirname(os.path.realpath(__file__))
if not os.path.exists(current_dir + '/files'):
    os.makedirs(current_dir + '/files')

app = FastAPI()

port = random.randint(9222, 9322)

os.system(f'"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port={port} &')

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

def process(task_id):
    url = "http://localhost:8000/task-" + task_id
    tab, browser = create_browser_tab(url)
    task = tasks[task_id]
    for _ in range(10):
        if task['status'] == 'ready':
            break
        tab.wait(1)
    tab.stop()
    browser.close_tab(tab)

tasks = {}

@app.post("/post-payload")
async def post_datadome(request: Request):
    data = await request.json()
    script = data['script']
    task_id = str(uuid4())
    cid = data['cid']

    tasks[task_id] = {
        'status': 'pending',
        'value': None,
        'cid': cid,
    }
    # save the payload to a file with the task_id as the filename
    with open(f'{current_dir}/files/{cid}.html', 'w') as f:
        f.write(script)

    # open a new thread to process the payload
    t = threading.Thread(target=process, args=(task_id,))
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

@app.post("/interstitial/")
async def interstitial(request: Request):
    # application/x-www-form-urlencoded; charset=UTF-8
    data = await request.form()
    cid = data['cid']
    json_data = {}
    for key, value in data.items():
        json_data[key] = value
    # modify all tasks with the same cid
    for _, task in tasks.items():
        if task['cid'] == cid:
            task['value'] = json_data
            task['status'] = 'ready'
    # remove file
    try:
        os.remove(f'{current_dir}/files/{cid}.html')
    except:
        pass
    return {
        "cookie": "datadome=" + cid + ';'
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)