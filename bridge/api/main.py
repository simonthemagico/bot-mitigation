import sys
from pathlib import Path

# Add parent directory to path to allow imports from modules
bridge_dir = Path(__file__).parent.parent
sys.path.insert(0, str(bridge_dir))

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
from contextlib import asynccontextmanager
import traceback

from modules.google_search import GoogleSearchBypass
from modules.seloger_search import SeLogerSearchBypass
from modules.louisvuitton_search import LouisVuittonSearchByPass
from modules.aprium_search import ApriumSearchByPass
from modules.yelp_search import YelpSearchBypass

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
TIMEOUT = 100  # seconds

# Constant for max concurrent tasks
MAX_TASKS = 4

# Set up logging (both file and console so tracebacks are visible)
log_file = bridge_dir / 'logs' / 'bridge.log'
log_file.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file)),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Enums for task types and statuses
class BypassMethod(str, Enum):
    GOOGLE_SEARCH = "google_search"
    SELOGER_SEARCH = "seloger_search"
    LOUISVUITTON_SEARCH = "louisvuitton_search"
    APRIUM_SEARCH = "aprium_search"
    YELP_SEARCH = "yelp_search"

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
    BypassMethod.SELOGER_SEARCH: SeLogerSearchBypass,
    BypassMethod.LOUISVUITTON_SEARCH: LouisVuittonSearchByPass,
    BypassMethod.APRIUM_SEARCH: ApriumSearchByPass,
    BypassMethod.YELP_SEARCH: YelpSearchBypass,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(cleanup_old_tasks())
    await asyncio.sleep(1)
    yield
    logger.info("Shutting down cleanup task...")

# Initialize FastAPI and task store
app = FastAPI(
    title="bridge.datamonkeyz.com",
    description="JS browser bypass API",
    version="1.0.0",
    lifespan=lifespan
)

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
    task_store[task_id] = {
        **initial_response.dict(),
        "handler": None,
        "timestamp": time.time()
    }

    asyncio.create_task(execute_bypass_with_timeout(task_id, task, TIMEOUT))

    return initial_response

# Separate function for task execution
async def execute_bypass_with_timeout(
        task_id: str,
        task: TaskRequest,
        timeout_seconds: int
    ):
    handler = None
    try:
        # Update status to in progress
        task_store[task_id].update({"status": TaskStatus.IN_PROGRESS})

        handler_class = BYPASS_HANDLERS.get(task.bypass_method)
        if not handler_class:
            raise ValueError(f"No handler found for method: {task.bypass_method}")

        # Initialize handler

        handler = handler_class(
            proxy_pool=task.proxy_pool,
            url=task.url,
            task_id=task_id,
            headless=task.headless
        )

        # Store handler reference for potential cancellation
        task_store[task_id]["handler"] = handler
        loop = asyncio.get_event_loop()
        bypass_task = loop.run_in_executor(None, handler.bypass)

        # Wait for the bypass to complete with timeout
        page_content, cookies, headers, curl_command = await asyncio.wait_for(
            bypass_task,
            timeout=timeout_seconds
        )

        # Update task store with success
        task_store[task_id].update({
            "status": TaskStatus.DONE,
            "headers": headers,
            "cookies": cookies,
            "curl_command": curl_command
        })

        logger.info(f"Task {task_id} completed successfully")

    except asyncio.TimeoutError:
        # Log full traceback for debugging timeouts
        logger.exception(f"Task {task_id} timed out after {timeout_seconds} seconds")

        # Ensure Chrome is killed if handler was created
        if handler:
            logger.info(f"Cleaning up Chrome instance for timed out task {task_id}")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, handler.cleanup)
            logger.info(f"Successfully terminated Chrome instance for task {task_id}")

        # Handle timeout - ensure proper cleanup
        task_store[task_id].update({
            "status": TaskStatus.TIMEOUT,
            "error": f"Task timed out after {timeout_seconds} seconds"
        })

    except Exception as e:
        # Capture full traceback so it's available both in logs and API response
        error_trace = traceback.format_exc()
        logger.error(f"Task {task_id} failed with traceback:\n{error_trace}")

        # Ensure cleanup happens even on error
        if handler:
            try:
                # Run cleanup in executor to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, handler.cleanup)
                logger.info(f"Terminated Chrome instance after error for task {task_id}")
            except Exception as cleanup_error:
                # Also log full traceback if cleanup itself fails
                logger.exception(f"Error during cleanup after error for task {task_id}: {str(cleanup_error)}")

        task_store[task_id].update({
            "status": TaskStatus.ERROR,
            "error": error_trace
        })

# Cleanup tasks older than 10 min.
async def cleanup_old_tasks():

    while True:
        now = time.time()
        expired_tasks = [
            task_id for task_id, task in list(task_store.items())  # Use list() to avoid runtime changes error
            if task["status"] in [TaskStatus.DONE, TaskStatus.ERROR, TaskStatus.TIMEOUT]
            and now - task["timestamp"] > 600  # Remove tasks older than 10 min
        ]

        if expired_tasks:
            logger.info(f"Cleaning up {len(expired_tasks)} expired tasks...")

        for task_id in expired_tasks:
            try:
                task_store.pop(task_id, None)
            except KeyError:
                pass

        await asyncio.sleep(300)

@app.get("/task/{task_id}", response_model=TaskResponse)
async def get_task(
        task_id: str,
        token: str = Depends(verify_token)
    ):
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    # Create a copy of the task data without the handler
    task_data = {k: v for k, v in task_store[task_id].items() if k != "handler"}

    return task_data

@app.get("/health")
async def health_check(
    token: str = Depends(verify_token)
):
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "tasks_in_store": len(task_store),
        "active_tasks": sum(
            1 for t in task_store.values()
            if t["status"] in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        )
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
