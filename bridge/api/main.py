from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import Optional, Dict
from enum import Enum
import logging
import time
from asyncio import create_task as create_async_task, TimeoutError
import asyncio
import secrets

# Import your existing bypass handler
from modules.google_search import GoogleSearchBypass

# API Key header definition
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)

# API keys
API_KEYS = {
    "bri_live_51IkEHVAFM6jPN0afKwmUtcW1EkQyHGYmLM9QNDtBAWsx0huWaHyFfEDSlFcnzjM1fojdcJrkNeSPneJ3VC1ZvkOP00O8fbReYR"
}

async def get_api_key(api_key_header: str = Security(API_KEY_HEADER)):
    if api_key_header in API_KEYS:
        return api_key_header
    raise HTTPException(
        status_code=403,
        detail="Invalid API Key"
    )

# Constant for timeout
TIMEOUT = 30  # seconds

# Set up logging
logging.basicConfig(
    filename='logs/bridge.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enums for task types and statuses
class BypassMethod(str, Enum):
    GOOGLE_SEARCH = "google-search"  # Your current method
    # Future methods:
    # LINKEDIN = "linkedin"
    # FACEBOOK = "facebook"
    # AMAZON = "amazon"

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
    task_id: str
    status: TaskStatus
    bypass_method: BypassMethod
    cookies: Optional[Dict[str, str]] = None
    curl_command: Optional[str] = None
    error: Optional[str] = None

# Handler mapping
BYPASS_HANDLERS = {
    BypassMethod.GOOGLE_SEARCH: GoogleSearchBypass,
    # Add more handlers as we implement them:
    # BypassMethod.AMAZON: AmazonBypass,
    # BypassMethod.LINKEDIN: LinkedInBypass,
}

# Initialize FastAPI and task store
app = FastAPI(
    title="bridge.lobstr.io",
    description="JS browser bypass API",
    version="1.0.0"
)

# Simple in-memory store
task_store = {}

# Generate stripe-like task ID
def generate_task_id(prefix="tk_") -> str:
    """Generate a Stripe-like task ID"""
    # Generate 24 chars of random string (like Stripe)
    random_part = secrets.token_hex(12)  # 24 chars in hex
    return f"{prefix}{random_part}"

@app.post("/task", response_model=TaskResponse)
async def create_task(
        task: TaskRequest, 
        api_key: str = Depends(get_api_key)
    ):
    task_id = generate_task_id()
    logger.info(f"New task {task_id} for URL: {task.url}")

    # Initialize task in store immediately
    initial_response = TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        bypass_method=task.bypass_method
    )
    task_store[task_id] = initial_response.dict()

    # Define the actual task execution
    async def execute_bypass():
        try: 
            # Update status to in progress
            task_store[task_id].update({"status": TaskStatus.IN_PROGRESS})

            handler_class = BYPASS_HANDLERS.get(task.bypass_method)
            if not handler_class:
                raise ValueError(f"No handler found for method: {task.bypass_method}")

            handler = handler_class(
                proxy_pool=task.proxy_pool,
                url=task.url,
                headless=task.headless
            )
            
            # Execute bypass
            page_content, cookies, curl_command = handler.bypass()
            
            # Update task store with success
            task_store[task_id].update({
                "status": TaskStatus.DONE,
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

    # Start task execution with timeout
    try:
        # Create and run task with timeout
        await asyncio.wait_for(execute_bypass(), timeout=TIMEOUT)
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

    # Return initial response with task_id
    return initial_response


@app.get("/task/{task_id}", response_model=TaskResponse)
async def get_task(
        task_id: str, 
        api_key: str = Depends(get_api_key)
    ):
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_store[task_id]

@app.get("/health")
async def health_check(
    api_key: str = Depends(get_api_key)
):
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "tasks_in_store": len(task_store)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)