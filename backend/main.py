"""FastAPI backend for the formal verification pipeline demo."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.repo import router as repo_router

app: FastAPI = FastAPI(title="FV Pipeline Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repo_router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
