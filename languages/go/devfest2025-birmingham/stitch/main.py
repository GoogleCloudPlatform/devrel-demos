from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

@app.get("/greetings")
def read_greetings(name: str = None):
    if name:
        return {"message": f"Hello {name}"}
    return {"message": "Hello World"}

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

app.mount("/static", StaticFiles(directory="static"), name="static")