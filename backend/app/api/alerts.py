import httpx
from fastapi import APIRouter, Request
from app.core.config import settings

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.post("/webhook")
async def receive_prometheus_alert(request: Request):
    data = await request.json()
    for alert in data.get("alerts", []):
        status = alert.get("status")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        message = f"🚨 Alerte: {labels.get('alertname')} sur {labels.get('instance')}"
        if settings.telegram_bot_token and settings.telegram_chat_id:
            url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
            await httpx.AsyncClient().post(url, json={"chat_id": settings.telegram_chat_id, "text": message})
    return {"status": "processed"}