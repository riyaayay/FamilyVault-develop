"""Unit tests for the biometrics service's completion work.

The InsightFace model is never loaded here: the pipeline is exercised through
patched ``face_processor`` / ``cluster_engine`` methods, so the suite is fast
and offline-safe in CI.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import config
import main
from face_processor import ModelUnavailableError

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clean_state():
    main.MOCK_INBOX.clear()
    main.MOCK_TIMELINE.clear()
    main.MOCK_VAULT.clear()
    main.face_bank.clear()
    yield
    main.MOCK_INBOX.clear()
    main.MOCK_TIMELINE.clear()
    main.MOCK_VAULT.clear()
    main.face_bank.clear()


def _confident_face():
    return [
        {
            "face_id": "face_ok",
            "bbox": [10, 10, 100, 100],
            "match": {"person_id": "usr-1", "confidence": 0.92, "name": "Arthur Vance"},
            "action_required": False,
        }
    ]


# -- health -----------------------------------------------------------------
def test_health_reports_state_and_threshold_parity():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in ("ok", "degraded")
    assert "model" in body and "face_bank" in body and "storage" in body
    assert body["threshold"]["value"] == 0.85
    assert body["threshold"]["parity"] is True
    assert body["storage"] == "local"


def test_threshold_matches_contract_constant():
    assert config.threshold_parity() is True
    assert config.MATCH_THRESHOLD == config.CONTRACT_MATCH_THRESHOLD


# -- face bank --------------------------------------------------------------
def test_enroll_list_and_delete_embedding():
    embed = [0.001] * config.EMBEDDING_DIMENSION
    res = client.post(
        "/api/v1/biometrics/face-bank/enroll",
        json={"person_id": "usr-1", "name": "Arthur Vance", "embedding": embed},
    )
    assert res.status_code == 200

    listed = client.get("/api/v1/biometrics/face-bank").json()
    assert listed["count"] == 1
    assert listed["persons"][0]["person_id"] == "usr-1"
    assert listed["persons"][0]["embedding_dim"] == config.EMBEDDING_DIMENSION

    assert client.delete("/api/v1/biometrics/face-bank/usr-1").status_code == 200
    assert client.get("/api/v1/biometrics/face-bank").json()["count"] == 0


def test_enroll_rejects_wrong_dimension():
    res = client.post(
        "/api/v1/biometrics/face-bank/enroll",
        json={"person_id": "usr-1", "embedding": [0.0, 0.0]},
    )
    assert res.status_code == 400


def test_enroll_requires_embedding_or_image():
    res = client.post(
        "/api/v1/biometrics/face-bank/enroll",
        json={"person_id": "usr-1", "name": "Arthur Vance"},
    )
    assert res.status_code == 400


# -- matching & routing -----------------------------------------------------
def test_single_confident_face_auto_publishes_to_timeline():
    with patch.object(main.face_processor, "process_image", return_value=_confident_face()):
        res = client.post(
            "/api/v1/biometrics/match",
            json={"media_id": "m1", "r2_url": "http://x/a.jpg", "media_type": "image"},
        )
    assert res.status_code == 200
    assert "timeline" in res.json()["status"]
    assert len(main.MOCK_TIMELINE) == 1
    assert main.MOCK_TIMELINE[0]["media_id"] == "m1"
    assert len(main.MOCK_INBOX) == 0


def test_multi_face_photo_routes_to_inbox():
    faces = _confident_face() + [
        {**_confident_face()[0], "face_id": "face_2"}
    ]
    with patch.object(main.face_processor, "process_image", return_value=faces):
        res = client.post(
            "/api/v1/biometrics/match",
            json={"media_id": "group1", "r2_url": "http://x/g.jpg", "media_type": "image"},
        )
    assert res.status_code == 200
    assert "inbox" in res.json()["status"]
    assert len(main.MOCK_INBOX) == 1
    assert main.MOCK_INBOX[0]["pending_faces_count"] == 0  # both confident


def test_non_image_routes_to_inbox():
    res = client.post(
        "/api/v1/biometrics/match",
        json={"media_id": "vid1", "r2_url": "http://x/v.mp4", "media_type": "video"},
    )
    assert res.status_code == 200
    assert "inbox" in res.json()["status"]
    assert len(main.MOCK_INBOX) == 1


def test_match_degrades_gracefully_when_model_unavailable():
    with patch.object(
        main.face_processor,
        "process_image",
        side_effect=ModelUnavailableError("weights missing"),
    ):
        res = client.post(
            "/api/v1/biometrics/match",
            json={"media_id": "m2", "r2_url": "http://x/a.jpg", "media_type": "image"},
        )
    assert res.status_code == 200  # never a raw 500
    body = res.json()
    assert "inbox" in body["status"]
    assert body["error"] and "unavailable" in body["error"]
    assert len(main.MOCK_INBOX) == 1


def test_detect_all_faces_returns_503_when_model_unavailable():
    with patch.object(
        main.cluster_engine,
        "detect_and_cluster",
        side_effect=ModelUnavailableError("no model"),
    ):
        res = client.post(
            "/api/v1/biometrics/detect-all-faces",
            json={"media_id": "m3", "r2_url": "http://x/a.jpg"},
        )
    assert res.status_code == 503


# -- upload fallback --------------------------------------------------------
def test_local_upload_roundtrip():
    res = client.post(
        "/api/v1/biometrics/upload-url",
        json={"file_name": "photo.jpg", "content_type": "image/jpeg"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["storage"] == "local"
    assert "local-upload" in payload["upload_url"]

    file_name = payload["file_name"]
    put = client.put(
        f"/api/v1/biometrics/local-upload/{file_name}",
        content=b"fake-jpeg-bytes",
        headers={"Content-Type": "image/jpeg"},
    )
    assert put.status_code == 200

    got = client.get(f"/api/v1/biometrics/media/{file_name}")
    assert got.status_code == 200
    assert got.content == b"fake-jpeg-bytes"


# -- triage -----------------------------------------------------------------
def test_triage_accept_moves_inbox_item_to_timeline():
    with patch.object(main.face_processor, "process_image", return_value=[]):
        client.post(
            "/api/v1/biometrics/match",
            json={"media_id": "m4", "r2_url": "http://x/a.jpg", "media_type": "image"},
        )
    assert len(main.MOCK_INBOX) == 1

    res = client.patch(
        "/api/v1/biometrics/inbox/m4/triage", json={"status": "accepted"}
    )
    assert res.status_code == 200
    assert len(main.MOCK_INBOX) == 0
    assert any(i["media_id"] == "m4" for i in main.MOCK_TIMELINE)


def test_triage_reject_archives_item():
    with patch.object(main.face_processor, "process_image", return_value=[]):
        client.post(
            "/api/v1/biometrics/match",
            json={"media_id": "m5", "r2_url": "http://x/a.jpg", "media_type": "image"},
        )
    res = client.patch(
        "/api/v1/biometrics/inbox/m5/triage",
        json={"status": "rejected", "reason": "blurry"},
    )
    assert res.status_code == 200
    assert len(main.MOCK_INBOX) == 0
    assert any(i["media_id"] == "m5" for i in main.MOCK_VAULT)


def test_triage_unknown_item_returns_404():
    res = client.patch(
        "/api/v1/biometrics/inbox/nope/triage", json={"status": "accepted"}
    )
    assert res.status_code == 404
