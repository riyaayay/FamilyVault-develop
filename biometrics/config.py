"""Shared configuration for the FamilyVault biometrics service.

The matcher's similarity threshold is a single source of truth defined in
``contracts/MATCH_CONSTANTS.json``. An explicit ``MATCH_THRESHOLD`` env var
still wins (useful for tests / ops), but when it is absent we read the
contract file so the value can never silently drift from the frontend and
core-backend (testing-matrix case #27).
"""

import json
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

# biometrics/ (this file lives at biometrics/config.py)
SERVICE_DIR = Path(__file__).resolve().parent

# Runtime state (face bank, queues, local uploads). Overridable so tests can
# point at a throwaway directory and docker can mount a named volume.
DATA_DIR = Path(os.getenv("BIOMETRICS_DATA_DIR", str(SERVICE_DIR / "data")))

DEFAULT_MATCH_THRESHOLD = 0.85
# Suggestions below the auto-publish threshold but above this floor are shown
# to a human reviewer (Sprint 4: "0.70 to 0.85 needs a head's decision").
SUGGESTION_FLOOR = float(os.getenv("SUGGESTION_FLOOR", "0.70"))
EMBEDDING_DIMENSION = 512
MAX_FACES = int(os.getenv("MAX_FACES", "15"))

# Matches the 15-minute R2 presigned lifetime from Sprint 3.
PRESIGN_EXPIRATION_SECONDS = int(os.getenv("PRESIGN_EXPIRATION_SECONDS", "900"))

# When Cloudflare R2 is not configured (no creds in local dev) the service can
# fall back to on-disk storage so the upload -> recognise -> route path still
# works end to end. Set to "0" to hard-fail instead.
ALLOW_LOCAL_STORAGE = os.getenv("BIOMETRICS_ALLOW_LOCAL_STORAGE", "1").lower() not in ("0", "false", "no")

UPLOADS_DIR = DATA_DIR / "uploads"
# Reject oversized uploads at the local-upload endpoint (25 MB).
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
# Image download guard for the face pipeline.
IMAGE_FETCH_TIMEOUT_SECONDS = float(os.getenv("IMAGE_FETCH_TIMEOUT_SECONDS", "20"))
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(25 * 1024 * 1024)))

# Optionally require an API key on write endpoints. Off by default so the
# existing local frontend keeps working; set BIOMETRICS_API_KEY in production.
API_KEY = os.getenv("BIOMETRICS_API_KEY")


def _find_contract_file() -> Path | None:
    candidates = [
        SERVICE_DIR / "contracts" / "MATCH_CONSTANTS.json",
        SERVICE_DIR.parent / "contracts" / "MATCH_CONSTANTS.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


CONTRACT_PATH = _find_contract_file()
CONTRACT: dict = {}
if CONTRACT_PATH is not None:
    try:
        CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        CONTRACT = {}

CONTRACT_MATCH_THRESHOLD = CONTRACT.get("MATCH_THRESHOLD")


def _resolve_threshold() -> tuple[float, str]:
    env_value = os.getenv("MATCH_THRESHOLD")
    if env_value not in (None, ""):
        return float(env_value), "env"
    if CONTRACT_MATCH_THRESHOLD is not None:
        return float(CONTRACT_MATCH_THRESHOLD), "contract"
    return DEFAULT_MATCH_THRESHOLD, "default"


MATCH_THRESHOLD, THRESHOLD_SOURCE = _resolve_threshold()


def threshold_parity() -> bool | None:
    """True when the effective threshold equals the contract value."""
    if CONTRACT_MATCH_THRESHOLD is None:
        return None
    return abs(MATCH_THRESHOLD - float(CONTRACT_MATCH_THRESHOLD)) < 1e-9


def storage_mode() -> str:
    """Which object-storage backend upload URLs are minted against."""
    configured = all(
        os.getenv(name)
        for name in ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT_URL")
    )
    if configured:
        return "r2"
    if ALLOW_LOCAL_STORAGE:
        return "local"
    return "unconfigured"


MEDIA_ROUTE_PREFIX = "/api/v1/biometrics/media/"


def resolve_local_media_path(url: str) -> Path | None:
    """If ``url`` points at this service's local media route, return the file.

    Lets the pipeline read a just-uploaded file directly from disk instead of
    HTTP-fetching this service from inside its own container (where the
    published port is not reachable).
    """
    try:
        path = urlparse(url).path
    except ValueError:
        return None
    if not path.startswith(MEDIA_ROUTE_PREFIX):
        return None
    name = os.path.basename(path[len(MEDIA_ROUTE_PREFIX):])
    if not name:
        return None
    candidate = UPLOADS_DIR / name
    return candidate if candidate.is_file() else None
