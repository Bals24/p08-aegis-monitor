from fastapi import APIRouter, Query
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
    return [
        {
            "url": s.url,
            "name": s.name,
            "status": s.status,
            "response_time_ms": s.response_time_ms,
            "consecutive_failures": s.consecutive_failures,
            "error": s.error,
            "last_checked_at": s.last_checked_at,
        }
        for s in TARGETS
    ]


@router.post("/", status_code=201)
async def add_site(site: SiteCreate):
    if any(s.url == site.url for s in TARGETS):
        return {"message": "Site déjà surveillé"}
    TARGETS.append(
        SiteState(
            url=site.url,
            name=site.name,
            method=site.method,
            expected_keyword=site.expected_keyword,
        )
    )
    return {"message": "Site ajouté avec succès"}


@router.delete("/", status_code=200)
async def delete_site(url: str = Query(...)):
    for i, site in enumerate(TARGETS):
        if site.url == url:
            TARGETS.pop(i)
            return {"message": "Site supprimé"}
    return {"message": "Site non trouvé"}