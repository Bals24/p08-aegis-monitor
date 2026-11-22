import httpx
from datetime import UTC, datetime
from fastapi import APIRouter, Request
from app.core.config import settings

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# Historique en mémoire (les 50 dernières alertes)
INCIDENT_HISTORY = []


@router.get("/history")
async def get_history():
    return INCIDENT_HISTORY[-50:]


@router.post("/webhook")
async def receive_prometheus_alert(request: Request):
    data = await request.json()
    for alert in data.get("alerts", []):
        status = alert.get("status")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        
        alert_name = labels.get("alertname", "Unknown")
        severity = labels.get("severity", "warning")
        summary = annotations.get("summary", "No description")
        instance = labels.get("instance", labels.get("url", "Unknown"))
        
        # Enregistrement dans l'historique pour le dashboard
        INCIDENT_HISTORY.append({
            "time": datetime.now(UTC).isoformat(),
            "status": status,
            "severity": severity,
            "alert": alert_name,
            "target": instance,
            "summary": summary,
        })

        # Envoi Telegram
        if settings.telegram_bot_token and settings.telegram_chat_id:
            emoji = "🚨" if severity == "critical" else "⚠️"
            status_emoji = "🔴 DOWN" if status == "firing" else "🟢 RESOLVED"
            message = (
                f"{emoji} <b>Aegis Monitor</b>\n\n"
                f"Status: {status_emoji}\n"
                f"Alerte: {alert_name}\n"
                f"Cible: {instance}\n"
                f"Détails: {summary}\n"
            )
            url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": settings.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
            }
            async with httpx.AsyncClient() as client:
                await client.post(url, json=payload)
                
    return {"status": "processed"}