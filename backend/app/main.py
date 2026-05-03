from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.seed import init_db_and_seed
from app.routers import auth, profile, roadmap

app = FastAPI(title="CareerBridge API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:8080", 
        "http://127.0.0.1:8080", 
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup() -> None:
    init_db_and_seed()

@app.get("/health")
def health():
    return {"status": "ok"}

# Роутеры подключаются ТОЛЬКО здесь, в самом конце
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(roadmap.router)