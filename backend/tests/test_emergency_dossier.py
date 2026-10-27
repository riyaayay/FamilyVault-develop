from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db

client = TestClient(app)

async def mock_get_db():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result
    yield mock_session

@pytest.fixture(autouse=True)
def override_db():
    app.dependency_overrides[get_db] = mock_get_db
    yield
    app.dependency_overrides.clear()

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_health_status():
    response = client.get("/api/v1/health/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"

def test_emergency_dossier_compilation():
    test_user_id = "00000000-0000-0000-0000-000000000001"
    response = client.post(f"/api/v1/health/emergency-dossier/{test_user_id}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    dossier = res_data["data"]
    assert dossier["patient_id"] == test_user_id
    assert "blood_group" in dossier
    assert len(dossier["critical_allergies"]) > 0
    assert len(dossier["active_medications"]) > 0
    assert len(dossier["emergency_contacts"]) > 0
    assert len(dossier["tamper_proof_hash"]) == 64
