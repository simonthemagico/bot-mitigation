import traceback
import uvicorn
import uuid
import os
from fastapi import FastAPI, HTTPException
from typing import Dict, Optional
from datadome import DatadomeSolver
from config import RESPONSES_DIRNAME, SESSION_EXPIRE_HOURS
from pydantic import BaseModel
import validators
from datetime import datetime, timedelta

# background tasks
from fastapi import BackgroundTasks
from starlette.background import BackgroundTasks
import asyncio

CUID_URLS = {
    "cl1uci9tv00000al9553aekn3": "shopping.rakuten.com",
    "cl2617ro9000009mo0vs8gfvu": "leboncoin.fr",
    "cl3ibwlga000009ln44yhgzmw": "seloger.com",
    "clivpe56n000008kz4h693ot5": "pointp.fr",
}

POOL_USES = {
    "leboncoin.fr": "smartproxy",
    "shopping.rakuten.com": "smartproxy",
    "seloger.com": "smartproxy-full",
    "pointp.fr": "smartproxy-dc",
}

class BrowserSession:
    def __init__(self, browser, timestamp):
        self.browser = browser
        self.timestamp = timestamp

class SessionID(BaseModel):
    session_id: str
    url: Optional[str] = None

sessions: Dict[str, BrowserSession] = {}

class Request(BaseModel):
    url: str
    proxy_string: str = None

app = FastAPI()

async def cleanup_sessions():
    while True:
        current_time = datetime.now()
        sessions_to_remove = []

        for session_id, session in sessions.items():
            if current_time - session.timestamp > timedelta(hours=SESSION_EXPIRE_HOURS):
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            # perform any necessary browser cleanup here, such as closing the browser
            del sessions[session_id]
        
        # sleep for an interval (for example, 5 minutes) before checking again
        await asyncio.sleep(300)

@app.on_event("startup")
async def startup_event():
    # use BackgroundTasks to start the cleanup task in the background when the app starts
    task = BackgroundTasks()
    task.add_task(cleanup_sessions)

@app.post("/bypass/{cuid}")
async def root(request: Request, cuid: str):
    if not cuid:
        raise HTTPException(status_code=404, detail="not found")
    try:
        validators.domain(request.url)
        url = CUID_URLS[cuid]
        if not (url in request.url):
            raise HTTPException(status_code=400, detail="bad url")
    except validators.ValidationFailure:
        raise HTTPException(status_code=404, detail="not found")

    try:
        solver = DatadomeSolver(proxy_pool=POOL_USES.get(url), proxy_string=request.proxy_string, responses_dirname=os.path.join(RESPONSES_DIRNAME, "conn_{}".format(uuid.uuid4().hex)))
        # solver = DatadomeSolver(proxy_pool=POOL_USES.get(url), proxy_string=request.proxy_string)
        cookie = solver.go_to(request.url)
        return {
            "status": "success",
            "cookies": cookie
        }
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "exc": e.__class__.__name__
        })

@app.post("/setup")
async def setup_session(request: Request):
    try:
        url = request.url
        proxy_string = request.proxy_string
        proxy_pool = POOL_USES.get(url)
        if not proxy_pool and not proxy_string:
            raise HTTPException(status_code=400, detail="bad url")
        session_id = str(uuid.uuid4())
        solver = DatadomeSolver(proxy_pool=proxy_pool, proxy_string=proxy_string, responses_dirname=os.path.join(RESPONSES_DIRNAME, "conn_{}".format(session_id)))
        sessions[session_id] = BrowserSession(solver, datetime.now())
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "exc": e.__class__.__name__
        })

@app.post("/request")
async def perform_request(request: SessionID):
    session_id = request.session_id
    if session_id not in sessions or (datetime.now() - sessions[session_id].timestamp > timedelta(hours=SESSION_EXPIRE_HOURS)):
        if session_id in sessions:
            del sessions[session_id]  # remove expired session
        raise HTTPException(status_code=404, detail="session not found or expired")

    try:
        browser = sessions[session_id].browser
        html = browser.go_to(request.url, html_only=True)
        return {"status": "success", "html": html}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "exc": e.__class__.__name__
        })

@app.post("/close")
async def close_session(request: SessionID):
    session_id = request.session_id
    if session_id in sessions:
        # perform any necessary browser cleanup here, such as closing the browser
        del sessions[session_id]
        return {"status": "success"}
    else:
        raise HTTPException(status_code=404, detail="session not found")

if __name__ == "__main__":
    # uvicorn api:app --host 0.0.0.0 --port 8005 --workers 10
    uvicorn.run("api:app", host="0.0.0.0", port=8005, reload=False)
