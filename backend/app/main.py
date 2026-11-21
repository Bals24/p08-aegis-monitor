import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram, make_asgi_app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.alerts import router as alerts_router
from app.api.sites import router as sites_router
from app.probes.monitor import background_monitoring_task

# --- SÉCURITÉ : RATE LIMITING ---
limiter = Limiter(key_func=get_remote_address)
app_limiter = FastAPI() # Hack pour initialiser limiter avant app

REQUEST_COUNT = Counter("http_requests_total", "Total", ["method", "endpoint", "http_status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Latence", ["method", "endpoint"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Aegis Monitor API starting (Secured)...")
    asyncio.create_task(background_monitoring_task())
    yield

app = FastAPI(title="Aegis Monitor", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware CORS strict
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost"], # Strict : uniquement notre proxy HTTPS
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- ROUTES ---
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
@limiter.limit("10/minute") # Protège le dashboard
async def serve_dashboard(request: Request):
    return FileResponse(str(STATIC_DIR / "index.html"))

app.include_router(sites_router)
app.include_router(alerts_router)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, http_status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(time.time() - start_time)
    return response

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.get("/health")
async def health():
    return {"status": "ok"}