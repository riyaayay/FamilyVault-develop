import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
import sys
import importlib.util
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
biometrics_dir = project_root / "biometrics"

if str(biometrics_dir) not in sys.path:
    sys.path.insert(0, str(biometrics_dir))

def load_module_from_path(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

bio_main = load_module_from_path("biometrics_main", biometrics_dir / "main.py")

client = TestClient(bio_main.app)

@pytest.fixture(autouse=True)
def clear_queues():
    bio_main.MOCK_INBOX.clear()
    bio_main.MOCK_TIMELINE.clear()
    yield
    bio_main.MOCK_INBOX.clear()
    bio_main.MOCK_TIMELINE.clear()


def test_boundary_match_at_threshold_0_850():
    mock_face_result = [{
        "face_id": "face_test_01",
        "bbox": [10, 10, 100, 100],
        "match": {"person_id": "usr-seeded-001", "confidence": 0.850, "name": "Arthur Vance"},
        "action_required": False
    }]

    with patch.object(bio_main.face_processor, "process_image", return_value=mock_face_result):
        payload = {
            "media_id": "media_threshold_0850",
            "r2_url": "https://r2.familyvault.internal/media_threshold_0850.jpg",
            "media_type": "image"
        }
        response = client.post("/api/v1/biometrics/match", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "timeline" in data["status"]
        assert len(bio_main.MOCK_TIMELINE) == 1
        assert bio_main.MOCK_TIMELINE[0]["media_id"] == "media_threshold_0850"
        assert len(bio_main.MOCK_INBOX) == 0


def test_boundary_rejection_at_threshold_0_849():
    mock_face_result = [{
        "face_id": "face_test_02",
        "bbox": [10, 10, 100, 100],
        "match": None,
        "suggested_persons": [{"person_id": "usr-seeded-001", "confidence": 0.849, "name": "Arthur Vance"}],
        "action_required": True
    }]

    with patch.object(bio_main.face_processor, "process_image", return_value=mock_face_result):
        payload = {
            "media_id": "media_threshold_0849",
            "r2_url": "https://r2.familyvault.internal/media_threshold_0849.jpg",
            "media_type": "image"
        }
        response = client.post("/api/v1/biometrics/match", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "inbox" in data["status"]
        assert len(bio_main.MOCK_INBOX) == 1
        assert bio_main.MOCK_INBOX[0]["media_id"] == "media_threshold_0849"
        assert len(bio_main.MOCK_TIMELINE) == 0


def test_edge_case_zero_faces_detected():
    with patch.object(bio_main.face_processor, "process_image", return_value=[]):
        payload = {
            "media_id": "media_zero_face_landscape",
            "r2_url": "https://r2.familyvault.internal/landscape.jpg",
            "media_type": "image"
        }
        response = client.post("/api/v1/biometrics/match", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["faces"] == []


def test_edge_case_multi_person_group_photo():
    multi_faces = [
        {
            "face_id": "face_group_1",
            "bbox": [10, 10, 50, 50],
            "match": {"person_id": "usr-01", "confidence": 0.92, "name": "David Vance"},
            "action_required": False
        },
        {
            "face_id": "face_group_2",
            "bbox": [60, 10, 100, 50],
            "match": {"person_id": "usr-02", "confidence": 0.88, "name": "Michael Vance"},
            "action_required": False
        }
    ]

    with patch.object(bio_main.face_processor, "process_image", return_value=multi_faces):
        payload = {
            "media_id": "media_family_reunion_group",
            "r2_url": "https://r2.familyvault.internal/group.jpg",
            "media_type": "image"
        }
        response = client.post("/api/v1/biometrics/match", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "inbox" in data["status"]
        assert len(data["faces"]) == 2
        assert len(bio_main.MOCK_INBOX) == 1
        assert bio_main.MOCK_INBOX[0]["media_id"] == "media_family_reunion_group"
        assert len(bio_main.MOCK_TIMELINE) == 0


def test_persistence_invariance_rejected_media_persists():
    mock_rejected_face = [{
        "face_id": "face_ambiguous_01",
        "bbox": [15, 15, 80, 80],
        "match": None,
        "suggested_persons": [],
        "action_required": True
    }]

    with patch.object(bio_main.face_processor, "process_image", return_value=mock_rejected_face):
        payload = {
            "media_id": "media_rejected_photo_01",
            "r2_url": "https://r2.familyvault.internal/unrecognized_person.jpg",
            "media_type": "image"
        }
        post_res = client.post("/api/v1/biometrics/match", json=payload)
        assert post_res.status_code == 200
        assert "inbox" in post_res.json()["status"]

        inbox_res = client.get("/api/v1/biometrics/inbox")
        assert inbox_res.status_code == 200
        pending_items = inbox_res.json()["pending_items"]
        assert any(item["media_id"] == "media_rejected_photo_01" for item in pending_items)
