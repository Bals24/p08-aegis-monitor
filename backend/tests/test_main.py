from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """Teste si l'API est vivante."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_dashboard_serving():
    """Teste si le tableau de bord est servi."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Aegis Monitor" in response.text

def test_api_sites_endpoint():
    """Teste l'endpoint des sites."""
    response = client.get("/api/sites/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)