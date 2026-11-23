import httpx
from datetime import UTC, datetime
from fastapi import APIRouter, Request
from app.core.config import settings

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

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

        # Envoi Telegram AVEC LIEN DIRECT VERS LE DASHBOARD
        if settings.telegram_bot_token and settings.telegram_chat_id:
            emoji = "🚨" if severity == "critical" else "⚠️"
            status_emoji = "🔴 EN PANNE" if status == "firing" else "🟢 RÉTABLI"
            
            message = (
                f"{emoji} <b>Aegis Monitor</b>\n\n"
                f"État : {status_emoji}\n"
                f"Alerte : {alert_name}\n"
                f"Site : {instance}\n"
                f"Détails : {summary}\n\n"
                f"🔗 <a href='http://localhost:8000'>Ouvrir le Tableau de Bord</a>"
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