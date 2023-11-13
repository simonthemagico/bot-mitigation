import uvicorn
from fastapi import FastAPI
from puzzle import find_puzzle_fit_area
from pydantic import BaseModel
import tempfile
import requests

class PuzzleSolverRequest(BaseModel):
    bgImageUrl: str
    pieceImageUrl: str

app = FastAPI()

@app.post("/api/v1/puzzleSolver")
def puzzleSolver(puzzleSolverRequest: PuzzleSolverRequest):
    with tempfile.NamedTemporaryFile(suffix='.jpg') as f, tempfile.NamedTemporaryFile(suffix='.jpg') as f2:
        # download the images
        bg_response = requests.get(puzzleSolverRequest.bgImageUrl)
        piece_response = requests.get(puzzleSolverRequest.pieceImageUrl)

        # write the images to disk
        f.write(bg_response.content)
        f2.write(piece_response.content)

        x, y = find_puzzle_fit_area(f.name, piece_image_path=f2.name)
        print(f"Piece fits at x = {x} and y = {y}.")
        return {"x": x, "y": y}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8015)