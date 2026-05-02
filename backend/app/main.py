from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .seed import init_db_and_seed
from .routers import auth as auth_router
from .routers import profile as profile_router

app = FastAPI(title="CareerBridge API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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


app.include_router(auth_router.router)
app.include_router(profile_router.router)
