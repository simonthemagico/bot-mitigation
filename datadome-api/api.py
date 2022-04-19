import traceback
import uvicorn
from fastapi import FastAPI, HTTPException
from datadome import DatadomeSolver
from pydantic import BaseModel
import validators

CUID_URLS = {
    "cl1uci9tv00000al9553aekn3": "shopping.rakuten.com",
    "cl2617ro9000009mo0vs8gfvu": "leboncoin.fr"
}

POOL_USES = {
    "leboncoin.fr": "smartproxy"
}

class Request(BaseModel):
    url: str
    proxy_string: str = None

app = FastAPI()

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
        solver = DatadomeSolver(proxy_pool=POOL_USES.get(url))
        cookie = solver.go_to(request.url)
        return {
            "status": "success",
            "cookies": cookie
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "exc": e.__class__.__name__
        })

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8005, reload=True)
