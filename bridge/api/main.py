from fastapi import FastAPI, HTTPException, Security, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel
from typing import Optional, Dict
from enum import Enum
import logging
import time
from asyncio import create_task as create_async_task, TimeoutError
import asyncio
import secrets
import re

from modules.google_search import GoogleSearchBypass
from modules.seloger_search import SeLogerSearchBypass

VALID_TOKENS = {
    "77f6bc041b99accf93093ebdc67a45ef472a4496"
}

async def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")
    
    if not authorization.startswith("Token "):
        raise HTTPException(status_code=401, detail="Invalid token format. Use 'Token {token}'")
    
    token = authorization.replace("Token ", "")
    if token not in VALID_TOKENS:
        raise HTTPException(status_code=403, detail="Invalid token")
        
    return token

# Constant for timeout
TIMEOUT = 30  # seconds

# Constant for max concurrent tasks
MAX_TASKS = 4

# Set up logging
logging.basicConfig(
    filename='logs/bridge.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enums for task types and statuses
class BypassMethod(str, Enum):
    GOOGLE_SEARCH = "google_search"
    SELOGER_SEARCH = "seloger_search"
    LOUISVUITTON_SEARCH = "louisvuitton_search"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ERROR = "error"
    TIMEOUT = "timeout"

# API Models
class TaskRequest(BaseModel):
    url: str
    proxy_pool: str  # Format: "http://user:pass@host:port"
    bypass_method: BypassMethod = BypassMethod.GOOGLE_SEARCH  # Default to Google Search
    headless: Optional[bool] = True

class TaskResponse(BaseModel):
    id: str
    status: TaskStatus
    bypass_method: BypassMethod
    headers: Optional[Dict[str, str]] = None
    cookies: Optional[Dict[str, str]] = None
    curl_command: Optional[str] = None
    error: Optional[str] = None

# Handler mapping
BYPASS_HANDLERS = {
    BypassMethod.GOOGLE_SEARCH: GoogleSearchBypass,
    BypassMethod.SELOGER_SEARCH: SeLogerSearchBypass
}

# Initialize FastAPI and task store
app = FastAPI(
    title="bridge.lobstr.io",
    description="JS browser bypass API",
    version="1.0.0"
)

# Serve static files for Let's Encrypt (no auth required)
app.mount("/.well-known/acme-challenge", StaticFiles(directory="/opt/homebrew/var/www/.well-known/acme-challenge"), name="acme-challenge")

# Simple in-memory store
task_store = {}

# Generate task ID
def generate_task_id():
    """Generate a simple 40-character hex task ID"""
    return secrets.token_hex(20)

@app.post("/task", response_model=TaskResponse)
async def create_task(
        task: TaskRequest, 
        token: str = Depends(verify_token)
    ):
    # 1. Count tasks in PENDING or IN_PROGRESS
    active_tasks = sum(
        1 for t in task_store.values()
        if t["status"] in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
    )

    # 2. Reject if we outpace MAX_TASKS limit
    if active_tasks >= MAX_TASKS:
        raise HTTPException(
            status_code=429,
            detail="Over-capacity: too many tasks in progress. Please retry later."
        )

    # Otherwise proceed to create a new task
    task_id = generate_task_id()
    logger.info(f"New task {task_id} for URL: {task.url}")

    initial_response = TaskResponse(
        id=task_id,
        status=TaskStatus.PENDING,
        bypass_method=task.bypass_method
    )
    task_store[task_id] = initial_response.dict()

    # Create background task
    async def timeout_wrapper():
        try:
            await asyncio.wait_for(execute_bypass(task_id, task), timeout=TIMEOUT)
        except TimeoutError:
            logger.error(f"Task {task_id} timed out after {TIMEOUT} seconds")
            task_store[task_id].update({
                "status": TaskStatus.TIMEOUT,
                "error": f"Task timed out after {TIMEOUT} seconds"
            })
        except Exception as e:
            logger.error(f"Task {task_id} failed unexpectedly: {str(e)}")
            task_store[task_id].update({
                "status": TaskStatus.ERROR,
                "error": str(e)
            })

    asyncio.create_task(timeout_wrapper())

    return initial_response

# Separate function for task execution
async def execute_bypass(task_id: str, task: TaskRequest):
    try: 
        # Update status to in progress
        task_store[task_id].update({"status": TaskStatus.IN_PROGRESS})

        handler_class = BYPASS_HANDLERS.get(task.bypass_method)
        if not handler_class:
            raise ValueError(f"No handler found for method: {task.bypass_method}")

        # Run bypass in threadpool since it's blocking
        loop = asyncio.get_event_loop()
        handler = handler_class(
            proxy_pool=task.proxy_pool,
            url=task.url,
            task_id=task_id,
            headless=task.headless
        )
        
        # Execute bypass in thread pool
        page_content, cookies, headers, curl_command = await loop.run_in_executor(
            None, handler.bypass
        )
        
        # Update task store with success
        task_store[task_id].update({
            "status": TaskStatus.DONE,
            "headers": headers,
            "cookies": cookies,
            "curl_command": curl_command
        })

        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        task_store[task_id].update({
            "status": TaskStatus.ERROR,
            "error": str(e)
        })


@app.get("/task/{task_id}", response_model=TaskResponse)
async def get_task(
        task_id: str, 
        token: str = Depends(verify_token)
    ):
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_store[task_id]

@app.get("/health")
async def health_check(
    token: str = Depends(verify_token)
):
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "tasks_in_store": len(task_store)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)