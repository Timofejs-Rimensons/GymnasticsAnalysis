from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routers import router
from app.config import settings
import os

# Create storage directories if they don't exist
os.makedirs("storage/uploads", exist_ok=True)
os.makedirs("storage/outputs", exist_ok=True)
os.makedirs("storage/temp", exist_ok=True)

app = FastAPI(
    title="Handstand Analyzer API",
    description="Analyze handstand videos and grade performance across 5 phases",
    version="1.0.0"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (for downloading CSV/PDF)
app.mount("/outputs", StaticFiles(directory="storage/outputs"), name="outputs")

# Include routes
app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": "Handstand Analyzer API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)