"""Persistent face bank: the registry of known family-member face embeddings.

A person is identified by the *same* UUID used in Postgres ``users.id`` and the
Neo4j ``Person.id`` node. This service never mints its own identifier
(``.context/agent-rules.md``). Embeddings are 512D ArcFace vectors.

State is kept in memory for fast matching and written through to a JSON file
so enrolments survive a restart (``data/face_bank.json`` inside the container).
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from config import DATA_DIR, EMBEDDING_DIMENSION

FACE_BANK_PATH = DATA_DIR / "face_bank.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FaceBank:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else FACE_BANK_PATH
        self._lock = threading.Lock()
        self._persons: dict[str, dict] = {}
        self._load()

    # -- persistence ---------------------------------------------------------
    def _load(self) -> None:
        try:
            if self.path.is_file():
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                persons = payload.get("persons", {})
                if isinstance(persons, dict):
                    self._persons = persons
        except (OSError, ValueError) as exc:  # corrupt file -> start clean
            print(f"[FaceBank] Could not load {self.path}: {exc}")
            self._persons = {}

    def _persist(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps({"persons": self._persons}, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self.path)
        except OSError as exc:
            print(f"[FaceBank] Could not persist {self.path}: {exc}")

    # -- mutation ------------------------------------------------------------
    def enroll(self, person_id: str, name: str, embedding) -> dict:
        person_id = str(person_id).strip()
        if not person_id:
            raise ValueError("person_id is required")
        vector = [float(x) for x in embedding]
        if len(vector) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"embedding must be {EMBEDDING_DIMENSION}-dimensional, got {len(vector)}"
            )
        entry = {"name": name or person_id, "embedding": vector, "updated_at": _now()}
        with self._lock:
            self._persons[person_id] = entry
        self._persist()
        return {"person_id": person_id, "name": entry["name"], "updated_at": entry["updated_at"]}

    def remove(self, person_id: str) -> bool:
        with self._lock:
            existed = self._persons.pop(str(person_id), None) is not None
        if existed:
            self._persist()
        return existed

    def clear(self) -> None:
        with self._lock:
            self._persons = {}
        self._persist()

    # -- reads ---------------------------------------------------------------
    def size(self) -> int:
        with self._lock:
            return len(self._persons)

    def list_persons(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "person_id": pid,
                    "name": data.get("name", pid),
                    "embedding_dim": len(data.get("embedding", [])),
                    "updated_at": data.get("updated_at"),
                }
                for pid, data in self._persons.items()
            ]

    def match(self, embedding, threshold: float, floor: float = 0.70) -> dict:
        """Rank every enrolled person against ``embedding`` by cosine similarity.

        Returns ``{"match": best_or_None, "suggestions": [...]}`` where
        ``match`` is populated only when the best score reaches ``threshold``
        and ``suggestions`` holds every candidate at or above ``floor``.
        """
        query = np.asarray([float(x) for x in embedding], dtype=np.float64)
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return {"match": None, "suggestions": []}

        ranked: list[dict] = []
        with self._lock:
            snapshot = list(self._persons.items())

        for person_id, data in snapshot:
            candidate = np.asarray(data.get("embedding", []), dtype=np.float64)
            if candidate.shape != query.shape:
                continue
            candidate_norm = np.linalg.norm(candidate)
            if candidate_norm == 0:
                continue
            similarity = float(np.dot(query, candidate) / (query_norm * candidate_norm))
            if similarity >= floor:
                ranked.append(
                    {
                        "person_id": person_id,
                        "name": data.get("name", person_id),
                        "confidence": round(similarity, 4),
                    }
                )

        ranked.sort(key=lambda item: item["confidence"], reverse=True)
        best = ranked[0] if ranked and ranked[0]["confidence"] >= threshold else None
        return {"match": best, "suggestions": ranked}


face_bank = FaceBank()
