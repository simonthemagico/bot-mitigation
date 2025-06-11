import os
import threading
from typing import Dict, Any

from urllib.parse import unquote
from uuid import uuid4
from fastapi import FastAPI, Request, Response

from tasks import process_url, handle_captcha
from config import CHROME_PATH, CHROME_PORT, API_PORT, previous_dir
from utils import fix_proxy
from logger import app_logger
from task_cleaner import TaskCleaner

tasks: Dict[str, Dict[str, Any]] = {}
task_cleaner = TaskCleaner(tasks)
task_cleaner.start()

os.system(f'"{CHROME_PATH}" --remote-debugging-port={CHROME_PORT} --load-extension={previous_dir}/extensionv2 --disable-extensions-except={previous_dir}/extensionv2 --user-data-dir={previous_dir}/user-data-dir &')
app = FastAPI()

@app.get('/render')
def render(request: Request):
    app_logger.info("Received /render request with query params: %s", request.query_params)
    data = request.query_params
    hash_ = data.get('hash')
    if not hash_:
        app_logger.error("Missing 'hash' parameter in /render request")
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
    app_logger.info("Returning HTML response for /render with hash: %s", hash_)
    return Response(content=html, media_type="text/html")


@app.post("/createTask")
async def create_task(request: Request):
    app_logger.info("Received /createTask request.")
    if not await request.body():
        app_logger.error("Empty request body in /createTask")
        return {
            "errorId": 1,
            "errorCode": "ERROR_EMPTY_BODY",
            "errorDescription": "Request body is empty"
        }
    try:
        data = await request.json()
    except Exception as e:
        app_logger.error("Invalid JSON in /createTask: %s", e)
        return {
            "errorId": 1,
            "errorCode": "ERROR_INVALID_JSON",
            "errorDescription": "Invalid JSON body"
        }
    
    # Extract data from new format
    task_data = data.get('task', {})
    if not task_data or 'websiteURL' not in task_data or 'captchaUrl' not in task_data:
        app_logger.error("Missing required task parameters in /createTask: %s", task_data)
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
        proxy = {
            'host': task_data.get('proxyAddress'),
            'port': task_data.get('proxyPort'),
            'user': task_data.get('proxyLogin'),
            'password': task_data.get('proxyPassword')
        }
        if not all([proxy['host'], proxy['port']]):
            app_logger.error("Invalid proxy configuration in /createTask: %s", proxy)
            return {
                "errorId": 1,
                "errorCode": "ERROR_PROXY_CONFIGURATION",
                "errorDescription": "Invalid proxy configuration. All proxy fields are required."
            }
    elif 'proxy' in task_data:
        proxy = task_data['proxy']
    else:
        app_logger.error("Missing proxy configuration in /createTask")
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
        'task_id': task_id
    }

    app_logger.info("Created new task with id: %s via /createTask", task_id)

    # Handle task processing
    func = process_url
    args = (proxy, tasks[task_id])
    if 'captcha-delivery' in url:
        app_logger.info("Detected captcha delivery URL in /createTask for task id: %s", task_id)
        func = handle_captcha
        args = (url, cid, CHROME_PORT, tasks[task_id])
        
    t = threading.Thread(target=func, args=args)
    t.start()
    tasks[task_id]['status'] = 'processing'
    task_cleaner.add_task(task_id, t)

    app_logger.info("Started processing task: %s via /createTask", task_id)
    return {
        'errorId': 0,
        'status': 'processing',
        'taskId': task_id
    }


@app.post("/getTaskResult")
async def get_task_result(request: Request):
    app_logger.info("Received /getTaskResult request.")
    data = await request.json()
    
    if 'taskId' not in data:
        app_logger.error("Missing parameter 'taskId' in /getTaskResult request: %s", data)
        return {
            "errorId": 1,
            "errorCode": "ERROR_PARAMETER_MISSING",
            "errorDescription": "Missing required parameter: taskId"
        }
    
    task_id = data['taskId']
    app_logger.info("Processing getTaskResult for task_id: %s", task_id)
    if task_id not in tasks:
        app_logger.error("Task %s not found in /getTaskResult", task_id)
        return {
            "errorId": 1,
            "errorCode": "ERROR_TASK_NOT_FOUND",
            "errorDescription": "Task not found"
        }
    
    task = tasks[task_id]
    response = {
        "errorId": 1,
        "errorCode": "ERROR_TASK_FAILED",
        "errorDescription": "Task processing failed"
    }
    if task['status'] == 'processing':
        app_logger.info("Task %s is still processing", task_id)
        response = {
            "errorId": 0,
            "status": "processing"
        }

    if task['status'] == 'ready':
        app_logger.info("Task %s is ready. Preparing solution.", task_id)
        value = task['value']
        if isinstance(value, str) and value.startswith('http'):
            solution = {'url': value}
        elif value.get('payload'):
            solution = {'interstitial': value}
        else:
            solution = {'cookie': task['payload']}
        response = {
            "errorId": 0,
            "status": "ready",
            "solution": solution
        }

    if task['status'] == 'blocked':
        app_logger.warning("Task %s is blocked: proxy banned", task_id)
        response = {
            "errorId": 1,
            "errorCode": "ERROR_PROXY_BANNED",
            "errorDescription": "Proxy is banned, please change your proxy"
        }

    if response.get('errorCode') == 'ERROR_TASK_FAILED':
        app_logger.error("Task %s processing failed", task_id)
    if task['status'] in ['ready', 'error', 'blocked']:
        task_cleaner.remove_task(task_id)
    return response

@app.post("/v1/response")
async def response(request: Request):
    app_logger.info("Received /v1/response request.")
    data = await request.json()
    app_logger.info("Data received in /v1/response: %s", data)
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
        if task['status'] in ['ready', 'blocked']:
            continue
        if task['cid'] == cid:
            if 'captcha-delivery' not in task['url'] and isinstance(json_data, dict) and json_data.get('payload'):
                continue
            if isinstance(json_data, dict) and cid in json_data.get('datadome', ''):
                continue
            task['value'] = json_data
            task['payload'] = payload
            if payload == 'blocked':
                task['status'] = 'blocked'
                app_logger.warning("Task with cid %s set to blocked due to payload", cid)
            else:
                task['status'] = 'ready'
                app_logger.info("Task with cid %s set to ready", cid)

# Add cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    task_cleaner.stop()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=API_PORT, http="h11")
