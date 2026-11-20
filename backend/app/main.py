from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_client import make_asgi_app, Counter, Histogram
import time
import asyncio
from app.probes.monitor import background_monitoring_task, TARGETS_STATUS

REQUEST_COUNT = Counter('http_requests_total', 'Total des requêtes HTTP', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Latence des requêtes HTTP', ['method', 'endpoint'])

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Aegis Monitor API starting...")
    asyncio.create_task(background_monitoring_task())
    yield
    print("👋 Aegis Monitor API shutting down...")

app = FastAPI(
    title="Aegis Monitor API",
    description="API de monitoring de sites web (Projet P08 ESTI)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, http_status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(time.time() - start_time)
    return response

# Endpoint pour Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Endpoint pour la Page de Statut Publique
@app.get("/api/status")
async def get_status():
    return {"targets": list(TARGETS_STATUS.values())}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "aegis-monitor"}