from fastapi import APIRouter
from pydantic import BaseModel

from app.probes.monitor import TARGETS, SiteState

router = APIRouter(prefix="/api/sites", tags=["sites"])


class SiteCreate(BaseModel):
    url: str
    name: str
    method: str = "GET"
    expected_keyword: str = ""


@router.get("/", response_model=list[dict])
async def list_sites():
    """Liste tous les sites surveillés avec leur état actuel."""
    return [
        {
            "url": state.url,
            "name": state.name,
            "status": state.status,
            "http_status": state.http_status,
            "response_time_ms": state.response_time_ms,
            "consecutive_failures": state.consecutive_failures,
            "last_checked_at": state.last_checked_at,
            "error": state.error,
        }
        for state in TARGETS
    ]


@router.post("/", status_code=201)
async def add_site(site: SiteCreate):
    """Ajoute un nouveau site à la surveillance (MVP en mémoire)."""
    if any(s.url == site.url for s in TARGETS):
        return {"message": "Site déjà surveillé"}
    
    new_state = SiteState(
        url=site.url,
        name=site.name,
        method=site.method,
        expected_keyword=site.expected_keyword,
    )
    TARGETS.append(new_state)
    return {"message": "Site ajouté avec succès", "site": new_state.url}