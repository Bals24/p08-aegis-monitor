import asyncio
import logging
from datetime import UTC, datetime

import httpx
from prometheus_client import Counter, Gauge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegis.probes")

AEGIS_SITE_UP = Gauge("aegis_site_up", "1 si le site fonctionne, 0 sinon", ["url", "name"])
AEGIS_RESPONSE_TIME_SECONDS = Gauge("aegis_response_time_seconds", "Temps de réponse en secondes", ["url", "name"])
AEGIS_PROBE_TOTAL = Counter("aegis_probe_total", "Nombre total de sondes", ["url", "name"])
AEGIS_PROBE_FAILURES_TOTAL = Counter("aegis_probe_failures_total", "Nombre d'échecs", ["url", "name"])
AEGIS_MONITORING_SITES_TOTAL = Gauge("aegis_monitoring_sites_total", "Nombre de sites surveillés")

class SiteState:
    def __init__(self, url: str, name: str, method: str = "GET", expected_keyword: str = ""):
        self.url = url
        self.name = name
        self.method = method
        self.expected_keyword = expected_keyword
        self.status = "UNKNOWN"
        self.http_status: int | None = None
        self.response_time_ms: float | None = None
        self.error: str | None = None
        self.consecutive_failures = 0
        self.last_checked_at: str | None = None

TARGETS = [
    SiteState("https://www.google.com", "Google", expected_keyword=""),
    SiteState("https://github.com", "GitHub", expected_keyword=""),
    SiteState("http://site-inexistant-test-12345.com", "Site Test (Panne)", expected_keyword=""),
]

AEGIS_MONITORING_SITES_TOTAL.set(len(TARGETS))

# Masque pour ne pas être bloqué par les sites (User-Agent de Chrome)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

async def check_site(state: SiteState):
    state.last_checked_at = datetime.now(UTC).isoformat()
    AEGIS_PROBE_TOTAL.labels(url=state.url, name=state.name).inc()

    try:
        start_time = asyncio.get_event_loop().time()
        async with httpx.AsyncClient(
            timeout=10.0, 
            follow_redirects=True,
            headers=HEADERS
        ) as client:
            response = await client.request(state.method, state.url)
            latency = asyncio.get_event_loop().time() - start_time

            state.http_status = response.status_code
            state.response_time_ms = round(latency * 1000, 2)
            
            is_content_valid = True
            if state.expected_keyword:
                is_content_valid = state.expected_keyword.lower() in response.text.lower()

            if response.status_code < 400 and is_content_valid:
                state.status = "UP"
                state.consecutive_failures = 0
                state.error = None
                AEGIS_SITE_UP.labels(url=state.url, name=state.name).set(1)
            else:
                state.status = "DOWN"
                state.error = f"HTTP {response.status_code}" + (" (Mot-clé manquant)" if not is_content_valid else "")
                state.consecutive_failures += 1
                AEGIS_PROBE_FAILURES_TOTAL.labels(url=state.url, name=state.name).inc()
                AEGIS_SITE_UP.labels(url=state.url, name=state.name).set(0)

    except httpx.TimeoutException:
        state.status = "DOWN"
        state.error = "Timeout (Le site est trop lent)"
        state.consecutive_failures += 1
        AEGIS_PROBE_FAILURES_TOTAL.labels(url=state.url, name=state.name).inc()
        AEGIS_SITE_UP.labels(url=state.url, name=state.name).set(0)
        
    except httpx.ConnectError:
        state.status = "DOWN"
        state.error = "DNS ou Connexion refusée"
        state.consecutive_failures += 1
        AEGIS_PROBE_FAILURES_TOTAL.labels(url=state.url, name=state.name).inc()
        AEGIS_SITE_UP.labels(url=state.url, name=state.name).set(0)
        
    except httpx.RequestError as e:
        state.status = "DOWN"
        state.error = f"Erreur réseau: {str(e)[:50]}"
        state.consecutive_failures += 1
        AEGIS_PROBE_FAILURES_TOTAL.labels(url=state.url, name=state.name).inc()
        AEGIS_SITE_UP.labels(url=state.url, name=state.name).set(0)

    if state.response_time_ms is not None:
        AEGIS_RESPONSE_TIME_SECONDS.labels(url=state.url, name=state.name).set(state.response_time_ms / 1000)

    status_emoji = "✅" if state.status == "UP" else "❌"
    logger.info(f"{status_emoji} [{state.name}] {state.status} | {state.error or 'OK'}")

async def background_monitoring_task():
    logger.info("🕵️‍♂️ [PROBES] Démarrage du moteur de surveillance...")
    while True:
        tasks = [check_site(state) for state in TARGETS]
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(15)