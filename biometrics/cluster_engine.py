"""Group-photo face clustering.

Scans a group image, isolates up to ``max_faces`` distinct faces (largest
first), extracts each 512D ArcFace embedding and matches it against the face
bank. Used by ``POST /api/v1/biometrics/detect-all-faces``.
"""

import uuid
from typing import Any, Dict, List

from config import MAX_FACES, MATCH_THRESHOLD
from face_processor import face_processor


class ClusterEngine:
    def __init__(self, max_faces: int = MAX_FACES):
        self.max_faces = max_faces

    def detect_and_cluster(self, r2_url: str, threshold: float | None = None) -> List[Dict[str, Any]]:
        app = face_processor.ensure_model()
        img = face_processor.download_image(r2_url)
        faces = app.get(img)

        # Largest bounding box first so the main subjects win when > max_faces.
        faces_sorted = sorted(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
            reverse=True,
        )
        top_faces = faces_sorted[: self.max_faces]

        threshold = threshold if threshold is not None else MATCH_THRESHOLD
        results: List[Dict[str, Any]] = []
        for face in top_faces:
            bbox = [float(coord) for coord in face.bbox]
            embedding = face.normed_embedding
            results.append(
                {
                    "face_id": f"face_{uuid.uuid4().hex[:8]}",
                    "bbox": bbox,
                    "embedding": embedding.tolist(),  # 512D L2-normalised floats
                    "match": face_processor.get_matches(embedding, threshold),
                }
            )
        return results


cluster_engine = ClusterEngine()
