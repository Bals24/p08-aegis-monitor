import asyncio
from datetime import datetime

import httpx
from prometheus_client import Gauge, Histogram

WEBSITE_UP = Gauge(
    "aegis_website_up",
    "1 si le site est en ligne, 0 sinon",
    ["url", "method"],
)
WEBSITE_RESPONSE_TIME = Histogram(
    "aegis_website_response_time_seconds",
    "Temps de réponse en secondes",
    ["url", "method"],
)

TARGETS_STATUS = {}

TARGETS = [
    {"url": "https://www.google.com", "method": "GET", "name": "Google"},
    {"url": "https://github.com", "method": "GET", "name": "GitHub"},
    {
        "url": "http://site-inexistant-test-12345.com",
        "method": "GET",
        "name": "Site Test (Panne volontaire)",
    },
]

for t in TARGETS:
    TARGETS_STATUS[t["url"]] = {
        "name": t["name"],
        "status": "unknown",
        "latency": 0,
        "last_check": "Never",
    }


async def check_target(target: dict):
    url = target["url"]
    method = target["method"]
    name = target["name"]
    try:
        start_time = asyncio.get_event_loop().time()
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.request(method, url)
            latency = asyncio.get_event_loop().time() - start_time

            is_up = 1 if response.status_code < 400 else 0
            WEBSITE_UP.labels(url=url, method=method).set(is_up)
            WEBSITE_RESPONSE_TIME.labels(url=url, method=method).observe(latency)

            TARGETS_STATUS[url] = {
                "name": name,
                "status": "UP" if is_up else "DOWN",
                "latency": round(latency * 1000, 2),
                "last_check": datetime.now().strftime("%H:%M:%S"),
                "code": response.status_code,
            }
    except httpx.RequestError as e:
        WEBSITE_UP.labels(url=url, method=method).set(0)
        TARGETS_STATUS[url] = {
            "name": name,
            "status": "DOWN",
            "latency": 0,
            "last_check": datetime.now().strftime("%H:%M:%S"),
            "error": str(e),
        }


async def background_monitoring_task():
    print("🕵️‍♂️ [PROBES] Démarrage de la surveillance en arrière-plan...")
    while True:
        tasks = [check_target(target) for target in TARGETS]
        await asyncio.gather(*tasks)
        await asyncio.sleep(15)
