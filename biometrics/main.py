"""FamilyVault Biometrics & Media Service (FastAPI).

Responsibilities:
* Mint presigned upload URLs (Cloudflare R2, or local disk when unconfigured).
* Detect faces in images (InsightFace Buffalo_L / ArcFace) and extract 512D
  embeddings.
* Match embeddings against the persistent face bank and route media to the
  Milestone Timeline (confident single match) or the manual-review Inbox.
* Let reviewers accept/reject inbox items.
"""

import os
import re
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from cluster_engine import cluster_engine
from config import (
    API_KEY,
    CONTRACT_MATCH_THRESHOLD,
    DATA_DIR,
    MATCH_THRESHOLD,
    MAX_UPLOAD_BYTES,
    THRESHOLD_SOURCE,
    UPLOADS_DIR,
    threshold_parity,
    storage_mode,
)
from face_bank import face_bank
from face_processor import (
    ImageFetchError,
    ModelUnavailableError,
    face_processor,
)
from media_store import media_store
from r2_client import R2ConfigurationError, generate_presigned_upload_url

load_dotenv()

PORT = int(os.getenv("PORT", 8002))

# In-memory views of the persistent queues. Kept as module-level lists so the
# existing edge-case tests can clear them directly.
MOCK_INBOX = media_store.inbox
MOCK_TIMELINE = media_store.timeline
MOCK_VAULT = media_store.archive


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure runtime state directories exist and (optionally) warm the model so
    # /health reflects a failed weight download at boot rather than first use.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if os.getenv("BIOMETRICS_PRELOAD_MODEL", "1").lower() not in ("0", "false", "no"):
        try:
            face_processor.ensure_model()
        except ModelUnavailableError as exc:
            print(f"[startup] Face model unavailable: {exc}")
    yield


app = FastAPI(title="FamilyVault Biometrics Service", lifespan=lifespan)


# --------------------------------------------------------------------------- #
# Auth (optional shared API key; disabled unless BIOMETRICS_API_KEY is set)
# --------------------------------------------------------------------------- #
def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class UploadRequest(BaseModel):
    file_name: str
    content_type: str


class UploadResponse(BaseModel):
    upload_url: str
    public_url: str
    file_name: str
    storage: str = "r2"


class MatchRequest(BaseModel):
    media_id: str
    r2_url: str
    media_type: str = "image"
    uploaded_by: Optional[str] = None


class MatchResponse(BaseModel):
    media_id: str
    r2_url: str
    status: str
    faces: List[Dict[str, Any]]
    error: Optional[str] = None


class DetectAllFacesRequest(BaseModel):
    media_id: str
    r2_url: str


class DetectAllFacesResponse(BaseModel):
    media_id: str
    faces: List[Dict[str, Any]]


class FaceBankEnrollRequest(BaseModel):
    person_id: str
    name: Optional[str] = None
    image_url: Optional[str] = None
    embedding: Optional[List[float]] = None


class TriageRequest(BaseModel):
    status: str  # "accepted" | "rejected"
    reason: Optional[str] = None


_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def _safe_name(file_name: str) -> str:
    name = os.path.basename(file_name).strip()
    if not name or not _SAFE_NAME.match(name):
        raise HTTPException(status_code=400, detail="Invalid file name")
    return name


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
@app.get("/health")
def health_check():
    """Liveness + degradation report (model, threshold parity, storage, size)."""
    model_ok = face_processor.model_available
    return {
        "status": "ok" if model_ok else "degraded",
        "service": "biometrics-service",
        "model": {
            "available": model_ok,
            "loaded": face_processor.model_loaded,
            "error": face_processor.init_error,
        },
        "threshold": {
            "value": MATCH_THRESHOLD,
            "source": THRESHOLD_SOURCE,
            "contract_value": CONTRACT_MATCH_THRESHOLD,
            "parity": threshold_parity(),
        },
        "storage": storage_mode(),
        "face_bank": {"size": face_bank.size()},
        "queues": media_store.counts(),
    }


# --------------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------------- #
@app.post(
    "/api/v1/biometrics/upload-url",
    response_model=UploadResponse,
    dependencies=[Depends(require_api_key)],
)
def get_upload_url(request: UploadRequest, http_request: Request):
    """Presigned, time-limited upload URL (R2, or local fallback in dev)."""
    ext = request.file_name.split(".")[-1] if "." in request.file_name else ""
    unique_filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    try:
        url_data = generate_presigned_upload_url(
            unique_filename,
            request.content_type,
            base_url=str(http_request.base_url),
        )
    except R2ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not url_data:
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")
    return url_data


@app.put(
    "/api/v1/biometrics/local-upload/{file_name}",
    dependencies=[Depends(require_api_key)],
)
async def local_upload(file_name: str, request: Request):
    """Receive a direct upload when running on the local-disk fallback."""
    if storage_mode() != "local":
        raise HTTPException(status_code=404, detail="Local upload is not enabled")
    safe_name = _safe_name(file_name)
    body = await request.body()
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file too large")
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOADS_DIR / safe_name).write_bytes(body)
    return {"ok": True, "file_name": safe_name, "size": len(body)}


@app.get("/api/v1/biometrics/media/{file_name}")
def serve_media(file_name: str):
    """Serve a stored upload back out (local fallback only)."""
    safe_name = _safe_name(file_name)
    path = UPLOADS_DIR / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Media not found")
    return FileResponse(path)


# --------------------------------------------------------------------------- #
# Matching & routing
# --------------------------------------------------------------------------- #
@app.post(
    "/api/v1/biometrics/match",
    response_model=MatchResponse,
    dependencies=[Depends(require_api_key)],
)
def match_faces(request: MatchRequest):
    """Detect faces, match against the face bank and route to inbox/timeline."""
    faces_data: List[Dict[str, Any]] = []
    routed_to = "inbox"
    error: Optional[str] = None

    if request.media_type != "image":
        error = f"non-image media ({request.media_type}) always requires review"
    else:
        try:
            faces_data = face_processor.process_image(request.r2_url)
        except ModelUnavailableError as exc:
            error = f"face model unavailable: {exc}"
        except ImageFetchError as exc:
            error = f"could not read image: {exc}"
        except Exception as exc:  # never leak an unhandled 500 to the caller
            print(f"Error during matching: {exc}")
            error = f"processing error: {exc}"
        else:
            if not faces_data:
                error = "no faces detected"
            elif len(faces_data) > 1:
                error = f"{len(faces_data)} faces detected, requires review"
            elif any(face.get("action_required", False) for face in faces_data):
                error = "no confident match"
            else:
                routed_to = "timeline"

    item = {
        "media_id": request.media_id,
        "r2_url": request.r2_url,
        "media_type": request.media_type,
        "uploaded_by": request.uploaded_by or "",
        "faces": faces_data,
        "reason": error,
    }
    if routed_to == "timeline":
        media_store.add_timeline(item)
    else:
        media_store.add_inbox(item)

    status = f"processed - routed to {routed_to}"
    if error:
        status = f"{status} ({error})"

    return MatchResponse(
        media_id=request.media_id,
        r2_url=request.r2_url,
        status=status,
        faces=faces_data,
        error=error,
    )


@app.post(
    "/api/v1/biometrics/detect-all-faces",
    response_model=DetectAllFacesResponse,
    dependencies=[Depends(require_api_key)],
)
def detect_all_faces(request: DetectAllFacesRequest):
    """Detect up to 15 faces in a group photo and extract 512D embeddings."""
    try:
        faces = cluster_engine.detect_and_cluster(request.r2_url)
    except ModelUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail=f"Face model unavailable: {exc}"
        ) from exc
    except ImageFetchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Error during detect-all-faces: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DetectAllFacesResponse(media_id=request.media_id, faces=faces)


# --------------------------------------------------------------------------- #
# Queues & triage
# --------------------------------------------------------------------------- #
@app.get("/api/v1/biometrics/inbox")
def get_inbox():
    return {"pending_items": MOCK_INBOX, "count": len(MOCK_INBOX)}


@app.get("/api/v1/biometrics/timeline")
def get_timeline():
    return {"published_items": MOCK_TIMELINE, "count": len(MOCK_TIMELINE)}


@app.get("/api/v1/biometrics/vault")
def get_vault():
    return {"vault_items": MOCK_VAULT, "count": len(MOCK_VAULT)}


@app.patch(
    "/api/v1/biometrics/inbox/{media_id}/triage",
    dependencies=[Depends(require_api_key)],
)
def triage_inbox_item(media_id: str, request: TriageRequest):
    """Accept (publish to timeline) or reject (archive) one inbox item."""
    status = request.status.strip().lower()
    if status not in ("accepted", "rejected"):
        raise HTTPException(
            status_code=400, detail="status must be 'accepted' or 'rejected'"
        )
    updated = media_store.triage(media_id, status, request.reason)
    if updated is None:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    return {"success": True, "item": updated}


# --------------------------------------------------------------------------- #
# Face bank (enrolment)
# --------------------------------------------------------------------------- #
@app.get("/api/v1/biometrics/face-bank")
def list_face_bank():
    return {"count": face_bank.size(), "persons": face_bank.list_persons()}


@app.post(
    "/api/v1/biometrics/face-bank/enroll",
    dependencies=[Depends(require_api_key)],
)
def enroll_face(request: FaceBankEnrollRequest):
    """Enrol a known person's face, either from an image URL or a raw embedding."""
    name = request.name or request.person_id

    if request.embedding is not None:
        try:
            entry = face_bank.enroll(request.person_id, name, request.embedding)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"success": True, "person": entry, "source": "embedding"}

    if request.image_url:
        try:
            faces = cluster_engine.detect_and_cluster(request.image_url)
        except ModelUnavailableError as exc:
            raise HTTPException(
                status_code=503, detail=f"Face model unavailable: {exc}"
            ) from exc
        except ImageFetchError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not faces:
            raise HTTPException(
                status_code=422, detail="No face detected in the provided image"
            )
        # detect_and_cluster returns faces largest-first.
        entry = face_bank.enroll(request.person_id, name, faces[0]["embedding"])
        return {"success": True, "person": entry, "source": "image_url"}

    raise HTTPException(
        status_code=400, detail="Provide either 'embedding' or 'image_url'"
    )


@app.delete(
    "/api/v1/biometrics/face-bank/{person_id}",
    dependencies=[Depends(require_api_key)],
)
def remove_face(person_id: str):
    if not face_bank.remove(person_id):
        raise HTTPException(status_code=404, detail="Person not in face bank")
    return {"success": True, "person_id": person_id}
