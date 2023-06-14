import traceback
import uvicorn
import uuid
import os
from fastapi import FastAPI, HTTPException
from datadome import DatadomeSolver
from pydantic import BaseModel
import validators

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
        solver = DatadomeSolver(proxy_pool=POOL_USES.get(url), proxy_string=request.proxy_string, responses_dirname=os.path.join("/data/logs/", "conn_{}".format(uuid.uuid4().hex)))
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

if __name__ == "__main__":
    # uvicorn api:app --host 0.0.0.0 --port 8005 --workers 10
    uvicorn.run("api:app", host="0.0.0.0", port=8005, reload=False)
