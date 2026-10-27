"""InsightFace (Buffalo_L / ArcFace) face detection and embedding extraction.

The model is loaded lazily on first use rather than at import time. That keeps
imports (and the unit-test suite) fast and lets ``/health`` report a degraded
state instead of crashing when the weights are unavailable.
"""

import uuid

import cv2
import numpy as np
import requests

try:
    from insightface.app import FaceAnalysis
except ImportError:  # pragma: no cover - environment without insightface
    FaceAnalysis = None

from config import (
    IMAGE_FETCH_TIMEOUT_SECONDS,
    MATCH_THRESHOLD,
    MAX_IMAGE_BYTES,
    SUGGESTION_FLOOR,
    resolve_local_media_path,
)
from face_bank import face_bank


class ModelUnavailableError(RuntimeError):
    """Raised when the InsightFace model cannot be used."""


class ImageFetchError(RuntimeError):
    """Raised when the source image cannot be downloaded or decoded."""


class FaceProcessor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FaceProcessor, cls).__new__(cls)
            cls._instance._app = None
            cls._instance._init_error = None
        return cls._instance

    # -- model lifecycle -----------------------------------------------------
    @property
    def model_available(self) -> bool:
        """True when the insightface package is installed at all."""
        return FaceAnalysis is not None

    @property
    def model_loaded(self) -> bool:
        return self._app is not None

    @property
    def init_error(self) -> str | None:
        return self._init_error

    def ensure_model(self):
        """Load the model on first use. Raises ModelUnavailableError on failure."""
        if self._app is not None:
            return self._app
        if FaceAnalysis is None:
            self._init_error = "insightface library is not installed"
            raise ModelUnavailableError(self._init_error)
        try:
            print("Initializing InsightFace model (Buffalo_L)...")
            app = FaceAnalysis(
                name="buffalo_l",
                root="~/.insightface",
                providers=["CPUExecutionProvider"],
            )
            app.prepare(ctx_id=0, det_size=(640, 640))
            self._app = app
            self._init_error = None
            print("InsightFace model initialized successfully.")
        except Exception as exc:  # pragma: no cover - depends on weights/network
            self._init_error = str(exc)
            print(f"[FaceProcessor] Model initialization failed: {exc}")
            raise ModelUnavailableError(self._init_error) from exc
        return self._app

    # -- io ------------------------------------------------------------------
    def download_image(self, url: str) -> np.ndarray:
        """Fetch an image (from disk for our own local media URLs, else HTTP)
        and decode it to an OpenCV BGR array."""
        local = resolve_local_media_path(url)
        if local is not None:
            try:
                content = local.read_bytes()
            except OSError as exc:
                raise ImageFetchError(f"Could not read local media: {exc}") from exc
        else:
            try:
                response = requests.get(url, timeout=IMAGE_FETCH_TIMEOUT_SECONDS)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise ImageFetchError(f"Could not fetch image: {exc}") from exc
            content = response.content

        if len(content) > MAX_IMAGE_BYTES:
            raise ImageFetchError(
                f"Image exceeds {MAX_IMAGE_BYTES} bytes limit"
            )

        image_array = np.asarray(bytearray(content), dtype="uint8")
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if img is None:
            raise ImageFetchError("Failed to decode image")
        return img

    # -- matching ------------------------------------------------------------
    def get_matches(self, embedding, threshold: float | None = None) -> dict | None:
        """Best face-bank match for a 512D embedding, or None below threshold."""
        result = face_bank.match(
            embedding,
            threshold if threshold is not None else MATCH_THRESHOLD,
            SUGGESTION_FLOOR,
        )
        return result["match"]

    def match_embedding(self, embedding, threshold: float | None = None) -> dict:
        """Full ranking: ``{"match": best_or_None, "suggestions": [...]}``."""
        return face_bank.match(
            embedding,
            threshold if threshold is not None else MATCH_THRESHOLD,
            SUGGESTION_FLOOR,
        )

    # -- pipeline ------------------------------------------------------------
    def process_image(self, image_url: str, threshold: float | None = None) -> list[dict]:
        """Download, detect every face, embed and match against the face bank."""
        app = self.ensure_model()
        img = self.download_image(image_url)
        faces = app.get(img)

        threshold = threshold if threshold is not None else MATCH_THRESHOLD
        results = []

        for face in faces:
            bbox = [int(coord) for coord in face.bbox]
            embedding = face.normed_embedding
            ranking = self.match_embedding(embedding, threshold)

            if ranking["match"] is not None:
                matched_person = ranking["match"]
                action_required = False
                suggested_persons: list[dict] = []
            else:
                matched_person = None
                action_required = True
                suggested_persons = ranking["suggestions"]

            result = {
                "face_id": f"face_{uuid.uuid4().hex[:8]}",
                "bbox": bbox,
                "match": matched_person,
                "action_required": action_required,
            }
            if suggested_persons:
                result["suggested_persons"] = suggested_persons
            results.append(result)

        return results


face_processor = FaceProcessor()
