"""Enrol known faces into the persistent face bank from an image.

Example (inside the biometrics container, largest face first):

    python scripts/seed_face_bank.py \
        --image-url http://frontend:1111/group1.jpg \
        --person 00000000-0000-0000-0000-000000000001=Arthur Vance \
        --person 00000000-0000-0000-0000-000000000002=Eleanor Vance
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cluster_engine import cluster_engine  # noqa: E402
from face_bank import face_bank  # noqa: E402


def parse_person(value: str):
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected person_id=Display Name")
    person_id, name = value.split("=", 1)
    return person_id.strip(), name.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the face bank from a photo.")
    parser.add_argument("--image-url", required=True, help="Reachable image URL")
    parser.add_argument(
        "--person",
        action="append",
        type=parse_person,
        required=True,
        help="person_id=Display Name (repeat; mapped to faces largest-first)",
    )
    args = parser.parse_args()

    faces = cluster_engine.detect_and_cluster(args.image_url)
    if not faces:
        print("No faces detected in image.")
        return 1

    print(f"Detected {len(faces)} face(s).")
    for (person_id, name), face in zip(args.person, faces):
        entry = face_bank.enroll(person_id, name, face["embedding"])
        print(f"Enrolled {entry['name']} ({entry['person_id']}) from {face['face_id']}")

    print(f"Face bank now holds {face_bank.size()} person(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
