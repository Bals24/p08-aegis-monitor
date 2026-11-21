import asyncio
import logging
from datetime import datetime, timezone

import httpx
from prometheus_client import Counter, Gauge

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegis.probes")

# --- MÉTRIQUES PROMETHEUS (Conformité Recommandation Senior) ---
AEGIS_SITE_UP = Gauge(
    "aegis_site_up",
    "1 si le site fonctionne, 0 sinon",
    ["url", "name"]
)
AEGIS_RESPONSE_TIME_SECONDS = Gauge(
    "aegis_response_time_seconds",
    "Temps de réponse en secondes",
    ["url", "name"]
)
AEGIS_HTTP_STATUS_CODE = Gauge(
    "aegis_http_status_code",
    "Code HTTP reçu",
    ["url", "name"]
)
AEGIS_PROBE_TOTAL = Counter(
    "aegis_probe_total",
    "Nombre total de sondes effectuées",
    ["url", "name"]
)
AEGIS_PROBE_FAILURES_TOTAL = Counter(
    "aegis_probe_failures_total",
    "Nombre d'échecs de sondes",
    ["url", "name"]
)
AEGIS_MONITORING_SITES_TOTAL = Gauge(
    "aegis_monitoring_sites_total",
    "Nombre de sites surveillés"
)

# --- ÉTAT DES SITES (En mémoire pour le MVP, migrable vers Postgres ensuite) ---
class SiteState:
    def __init__(self, url: str, name: str, method: str = "GET", expected_keyword: str = ""):
        self.url = url
        self.name = name
        self.method = method
        self.expected_keyword = expected_keyword
        self.status = "UNKNOWN"
        self.http_status = None
        self.response_time_ms = None
        self.error = None
        self.consecutive_failures = 0
        self.last_checked_at = None

# Liste des cibles (Peut être chargée depuis une DB plus tard)
TARGETS = [
    SiteState("https://www.google.com", "Google Search", expected_keyword="Search"),
    SiteState("https://github.com", "GitHub Home", expected_keyword="Sign in"),
    SiteState("http://site-inexistant-test-12345.com", "Site E-commerce (Panne simulée)"),
]

# Initialisation de la métrique de nombre de sites
AEGIS_MONITORING_SITES_TOTAL.set(len(TARGETS))


async def check_site(state: SiteState):
    """Sonde robuste avec gestion des erreurs et tracking des échecs consécutifs."""
    state.last_checked_at = datetime.now(timezone.utc).isoformat()
    AEGIS_PROBE_TOTAL.labels(url=state.url, name=state.name).inc()

    try:
        start_time = asyncio.get_event_loop().time()
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.request(state.method, state.url)
            latency = asyncio.get_event_loop().time() - start_time

            state.http_status = response.status_code
            state.response_time_ms = round(latency * 1000, 2)
            
            # Vérification du contenu si un mot-clé est attendu
            is_content_valid = True
            if state.expected_keyword:
                is_content_valid = state.expected_keyword.lower() in response.text.lower()

            if response.status_code < 400 and is_content_valid:
                state.status = "UP"
                state.consecutive_failures = 0 # Reset des échecs
                state.error = None
                AEGIS_SITE_UP.labels(url=state.url, name=state.name).set(1)
            else:
                raise Exception(f"HTTP {response.status_code} ou mot-clé manquant")

    except httpx.TimeoutException:
        state.status = "DOWN"
        state.error = "Connection timeout"
        state.consecutive_failures += 1
        AEGIS_PROBE_FAILURES_TOTAL.labels(url=state.url, name=state.name).inc()
        AEGIS_SITE_UP.labels(url=state.url, name=state.name).set(0)
        
    except httpx.RequestError as e:
        state.status = "DOWN"
        state.error = str(e) # ex: "DNS resolution failed"
        state.consecutive_failures += 1
        AEGIS_PROBE_FAILURES_TOTAL.labels(url=state.url, name=state.name).inc()
        AEGIS_SITE_UP.labels(url=state.url, name=state.name).set(0)
        
    except Exception as e:
        state.status = "DOWN"
        state.error = str(e)
        state.consecutive_failures += 1
        AEGIS_PROBE_FAILURES_TOTAL.labels(url=state.url, name=state.name).inc()
        AEGIS_SITE_UP.labels(url=state.url, name=state.name).set(0)

    # Mise à jour des métriques de temps et de code HTTP (même en cas d'erreur pour le code)
    if state.response_time_ms is not None:
        AEGIS_RESPONSE_TIME_SECONDS.labels(url=state.url, name=state.name).set(state.response_time_ms / 1000)
    if state.http_status is not None:
        AEGIS_HTTP_STATUS_CODE.labels(url=state.url, name=state.name).set(state.http_status)

    # Log pour le debug
    status_emoji = "✅" if state.status == "UP" else "❌"
    logger.info(f"{status_emoji} [{state.name}] {state.status} | Latence: {state.response_time_ms}ms | Échecs consécutifs: {state.consecutive_failures}")


async def background_monitoring_task():
    """Boucle infinie qui ne plante jamais, même si une sonde échoue."""
    logger.info("🕵️‍♂️ [PROBES] Démarrage du moteur de surveillance robuste...")
    while True:
        # On lance toutes les sondes en parallèle (un site lent ne bloque pas les autres)
        tasks = [check_site(state) for state in TARGETS]
        await asyncio.gather(*tasks, return_exceptions=True) # return_exceptions=True empêche le crash de la boucle
        
        await asyncio.sleep(15) # Intervalle de 15 secondes