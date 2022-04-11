import uvicorn
from fastapi import FastAPI, HTTPException
from datadome import DatadomeSolver
from pydantic import BaseModel
import validators

ALLOWED_URLS = ["shopping.rakuten.com"]

class Request(BaseModel):
    url: str

app = FastAPI()

@app.post("/cl1uci9tv00000al9553aekn3")
async def root(request: Request):
    try:
        validators.domain(request.url)
        for url in ALLOWED_URLS:
            if not (url in request.url):
                raise HTTPException(status_code=400, detail="bad url")
    except validators.ValidationFailure:
        raise HTTPException(status_code=404, detail="not found")

    try:
        solver = DatadomeSolver()
        cookie = solver.go_to(request.url)
        return {
            "status": "success",
            "cookies": cookie
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "exc": str(e)
        })

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8005, reload=True)
