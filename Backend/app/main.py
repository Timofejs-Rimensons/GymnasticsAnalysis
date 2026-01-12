from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.routers import router, TEMP_DIR
import os

os.environ['GLOG_minloglevel'] = '2'

app = FastAPI(title="GymnasticsAPI")

from fastapi.middleware.cors import CORSMiddleware

#TODO: Restrict origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount the router for API endpoints
app.include_router(router, prefix="/api", tags=["upload"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Gymnastics API"}

if __name__ == "__main__":
    import unicorn
    unicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)