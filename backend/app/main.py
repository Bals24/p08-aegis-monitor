from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(" Aegis Monitor starting...")
    yield
    print(" Aegis Monitor shutting down...")

app = FastAPI(
    title="Aegis Monitor API",
    description="Tableau de bord M2 de monitoring intelligent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "aegis-monitor"}

@app.get("/")
async def root():
    return {
        "name": "Aegis Monitor",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }