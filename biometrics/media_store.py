"""Persistent queues for media routing: inbox, timeline and rejected archive.

Kept intentionally small: three JSON-backed lists. The inbox holds media whose
faces were not confidently matched (or any non-image media); the timeline holds
auto-published media; the archive holds items a reviewer rejected, so nothing a
user sends is ever silently discarded (testing-matrix case #26).
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from config import DATA_DIR

STORE_PATH = DATA_DIR / "media_store.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MediaStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else STORE_PATH
        self._lock = threading.Lock()
        self.inbox: list[dict] = []
        self.timeline: list[dict] = []
        self.archive: list[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            if self.path.is_file():
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                self.inbox = list(payload.get("inbox", []))
                self.timeline = list(payload.get("timeline", []))
                self.archive = list(payload.get("archive", []))
        except (OSError, ValueError) as exc:
            print(f"[MediaStore] Could not load {self.path}: {exc}")

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(
                    {
                        "inbox": self.inbox,
                        "timeline": self.timeline,
                        "archive": self.archive,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            tmp.replace(self.path)
        except OSError as exc:
            print(f"[MediaStore] Could not persist {self.path}: {exc}")

    # -- routing -------------------------------------------------------------
    @staticmethod
    def _inbox_item(item: dict) -> dict:
        faces = item.get("faces", []) or []
        pending = sum(1 for f in faces if not f.get("match")) if faces else 1
        return {
            "media_id": item["media_id"],
            "r2_url": item.get("r2_url", ""),
            "thumbnail_url": item.get("thumbnail_url", item.get("r2_url", "")),
            "media_type": item.get("media_type", "image"),
            "uploaded_by": item.get("uploaded_by", ""),
            "uploaded_at": item.get("uploaded_at", _now()),
            "pending_faces_count": pending,
            "reason": item.get("reason"),
            "faces": faces,
        }

    def add_inbox(self, item: dict) -> dict:
        entry = self._inbox_item(item)
        with self._lock:
            self.inbox.append(entry)
        self.save()
        return entry

    def add_timeline(self, item: dict) -> dict:
        entry = dict(item)
        entry.setdefault("published_at", _now())
        with self._lock:
            self.timeline.append(entry)
        self.save()
        return entry

    # -- triage --------------------------------------------------------------
    def triage(self, media_id: str, status: str, reason: str | None = None) -> dict | None:
        """accept/reject an inbox item. Returns the updated record or None."""
        with self._lock:
            index = next(
                (k for k, i in enumerate(self.inbox) if i.get("media_id") == media_id),
                None,
            )
            if index is None:
                return None
            found = self.inbox.pop(index)

            found["status"] = "accepted" if status == "accepted" else "rejected"
            found["triaged_at"] = _now()
            if status == "accepted":
                self.timeline.append(found)
            else:
                if reason:
                    found["rejection_reason"] = reason
                self.archive.append(found)
        self.save()
        return found

    def counts(self) -> dict:
        return {
            "inbox": len(self.inbox),
            "timeline": len(self.timeline),
            "archive": len(self.archive),
        }


media_store = MediaStore()
