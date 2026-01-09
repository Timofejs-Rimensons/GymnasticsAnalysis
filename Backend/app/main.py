from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.routers import router as analysis_router, DATA_DIR
import os

app = FastAPI(title="Gymnastics Analysis API")

# Ensure the data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Mount the router for API endpoints
app.include_router(analysis_router, prefix="/api", tags=["analysis"])

# Mount the static directory to serve output files
app.mount("/output", StaticFiles(directory=DATA_DIR), name="output")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Gymnastics Analysis API"}

# Optional: allow `python main.py` for local dev
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)