import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram, make_asgi_app

from app.api.alerts import router as alerts_router
from app.api.sites import router as sites_router
from app.probes.monitor import background_monitoring_task

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total des requêtes HTTP",
    ["method", "endpoint", "http_status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Latence des requêtes HTTP",
    ["method", "endpoint"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Aegis Monitor API starting...")
    asyncio.create_task(background_monitoring_task())
    yield
    print("👋 Aegis Monitor API shutting down...")


app = FastAPI(
    title="Aegis Monitor API",
    description="Tableau de bord  de monitoring ",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_dashboard():
    if INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE))
    return {"error": "Dashboard file not found", "path": str(INDEX_FILE)}


app.include_router(sites_router)
app.include_router(alerts_router)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        http_status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method, endpoint=request.url.path
    ).observe(time.time() - start_time)
    return response


metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "aegis-monitor"}