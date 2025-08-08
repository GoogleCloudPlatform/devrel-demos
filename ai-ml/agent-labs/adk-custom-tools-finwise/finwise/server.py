from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from finwise.main import run_finwise_and_get_final_response

app = FastAPI()

app.mount("/static", StaticFiles(directory="finwise/ui/static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("finwise/ui/index.html")

@app.get("/run-agent")
async def run_agent_endpoint(prompt: str):
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    try:
        final_response = await run_finwise_and_get_final_response(prompt)
        if final_response:
            return {"response": final_response}
        else:
            raise HTTPException(status_code=500, detail="Agent did not return a final response.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Note: Running this directly is for development. 
    # For production, use a command like `uvicorn finwise.server:app --reload`
    uvicorn.run(app, host="0.0.0.0", port=8000)
