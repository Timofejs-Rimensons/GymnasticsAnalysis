from fastapi import FastAPI
from app.api.routers import router as handstand_router


app = FastAPI(title="Handstand Analyzer API")

# mount your router under /handstand
app.include_router(handstand_router, prefix="/handstand", tags=["handstand"])


# optional: allow `python main.py` for local dev
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
