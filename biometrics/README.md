# Biometrics & Media Service

**Owner:** Ayushman  
**Stack:** Python, InsightFace (ONNX / PyTorch), Cloudflare R2 (S3-compatible Object Storage), FastAPI  

## Responsibilities
- Cloudflare R2 bucket integration and signed upload URL generation.
- 512D facial embedding extraction using InsightFace.
- Cosine similarity matching against the shared constant: `MATCH_THRESHOLD = 0.85` (defined in [contracts/MATCH_CONSTANTS.json](../contracts/MATCH_CONSTANTS.json)).
- Multi-person face detection in family group photos with automated graph node tagging to Neo4j `Person.id`.
- Publish and maintain [contracts/media-match-response.json](../contracts/media-match-response.json) to unblock frontend media inbox development.

## Getting Started
Refer to [docs/COLLABORATION_PROTOCOL.md](../docs/COLLABORATION_PROTOCOL.md) for branch naming (`feature/ayushman-*`) and PR conventions.
