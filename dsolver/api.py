import os
import threading

from urllib.parse import unquote
from uuid import uuid4
from fastapi import FastAPI, Request, Response

from tasks import tasks, process_url, handle_captcha
from config import CHROME_PATH, CHROME_PORT, API_PORT, previous_dir
from utils import fix_proxy

os.system(f'"{CHROME_PATH}" --remote-debugging-port={CHROME_PORT} --load-extension={previous_dir}/extensionv2 --user-data-dir={previous_dir}/user-data-dir &')
app = FastAPI()

@app.get('/render')
def render(request: Request):
    data = request.query_params
    hash_ = data['hash']
    html = f"""
    <html>
    <script>
    window.addEventListener("message", (event) => {{
        if (event.origin !== window.location.origin) return;
        if (event.data.type !== "FROM_EXTENSION") return;
        chrome.runtime.sendMessage(event.data.extensionId, {{message: 'store', 'hash': "{hash_}", 'apiPort': {API_PORT}}});
        console.log('sent payload');
    }});
    </script>
    </html>
    """
    return Response(content=html, media_type="text/html")

@app.post("/verify-browser")
async def verify_browser(request: Request):
    data = await request.json()
    required_fields = ['url', 'cid', 'proxy']
    if not all(field in required_fields for field in data):
        return {
           "error": "MISSING_PARAMETER",
           "message": f"Missing Field found",
           "required": required_fields
        }
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
        args = (url, cid, CHROME_PORT, tasks[task_id])
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

@app.post("/createTask")
async def create_task(request: Request):
    data = await request.json()
    
    # Extract data from new format
    task_data = data.get('task', {})
    if not task_data or 'websiteURL' not in task_data or 'captchaUrl' not in task_data:
        return {
            "errorId": 1,
            "errorCode": "ERROR_PARAMETER_MISSING",
            "errorDescription": "Missing required task parameters: websiteURL, captchaUrl"
        }

    # Map new format to existing format
    url = task_data['captchaUrl']
    cid = task_data['oldCookie']

    # Extract proxy details
    if 'proxyAddress' in task_data:
        # Extract proxy details
        proxy = {
            'host': task_data.get('proxyAddress'),
            'port': task_data.get('proxyPort'),
            'user': task_data.get('proxyLogin'),
            'password': task_data.get('proxyPassword')
        }
        if not all([proxy['host'], proxy['port']]):
            return {
                "errorId": 1,
                "errorCode": "ERROR_PROXY_CONFIGURATION",
                "errorDescription": "Invalid proxy configuration. All proxy fields are required."
            }
    elif 'proxy' in task_data:
        proxy = task_data['proxy']
    else:
        return {
            "errorId": 1,
            "errorCode": "ERROR_PROXY_MISSING",
            "errorDescription": "Proxy configuration is required"
        }
    proxy = fix_proxy(proxy)
    # Create task
    task_id = str(uuid4())
    tasks[task_id] = {
        'status': 'processing',
        'value': None,
        'cid': cid,
        'url': url,
    }

    # Handle task processing
    func = process_url
    args = (task_id, cid, proxy)
    if 'captcha-delivery' in url:
        func = handle_captcha
        args = (url, cid, CHROME_PORT, tasks[task_id])

    t = threading.Thread(target=func, args=args)
    t.start()
    tasks[task_id]['status'] = 'processing'

    return {
        'errorId': 0,
        'status': 'processing',
        'taskId': task_id
    }

@app.post("/getTaskResult")
async def get_task_result(request: Request):
    data = await request.json()
    
    # Validate input
    if 'taskId' not in data:
        return {
            "errorId": 1,
            "errorCode": "ERROR_PARAMETER_MISSING",
            "errorDescription": "Missing required parameter: taskId"
        }
    
    task_id = data['taskId']
    if task_id not in tasks:
        return {
            "errorId": 1,
            "errorCode": "ERROR_TASK_NOT_FOUND",
            "errorDescription": "Task not found"
        }
    
    task = tasks[task_id]
    
    # If task is still processing
    if task['status'] == 'processing':
        return {
            "errorId": 0,
            "status": "processing"
        }

    # If task is ready
    if task['status'] == 'ready':
        value = task['value']
        if isinstance(value, str) and value.startswith('http'):
            solution = {'url': value}
        elif value.get('payload'):
            solution = {'interstitial': value}
        else:
            solution = {'cookie': task['payload']}
        return {
            "errorId": 0,
            "status": "ready",
            "solution": solution
        }

    if task['status'] == 'blocked':
        return {
            "errorId": 1,
            "errorCode": "ERROR_PROXY_BANNED",
            "errorDescription": "Proxy is banned, please change your proxy"
        }

    # If task failed
    return {
        "errorId": 1,
        "errorCode": "ERROR_TASK_FAILED",
        "errorDescription": "Task processing failed"
    }

@app.post("/v1/response")
async def response(request: Request):
    data = await request.json()
    print(data)
    body = data['body']
    payload = body['payload']
    json_data = payload
    if not payload.startswith('http'):
        json_data = {}
        urlparams = payload.split('&')
        for param in urlparams:
            try:
                key, value = param.split('=', 1)
            except:
                key, value = param, ''
            if not key.strip():
                continue
            json_data[key.strip()] = unquote(value.strip())
    cid = data['hashedUrl'] or ''
    for _, task in tasks.items():
        if task['cid'] == cid:
            if 'captcha-delivery' not in task['url'] and isinstance(json_data, dict) and json_data.get('payload'):
                continue
            if isinstance(json_data, dict) and cid in json_data.get('datadome', ''):
                continue
            task['value'] = json_data
            task['payload'] = payload
            if json_data == 'blocked':
                task['status'] = 'blocked'
            else:
                task['status'] = 'ready'

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
