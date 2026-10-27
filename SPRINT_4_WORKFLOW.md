# FamilyVault — Sprint 4 Master Workflow: Media Ingestion, Multi-Face Clustering & Cultural Kinship

**Document Version**: 4.0.0  
**Status**: Completed & Integrated  
**Lead Architect**: Runeet (`realruneett01`)  
**Target Branch**: `develop`  
**Services Covered**: Next.js Frontend (:1111), Core Backend (:8000), Graph Service (:8001), Biometrics Engine (:8002), Cloudflare R2  

---

## 1. Executive Summary & Sprint Objectives

Sprint 4 introduces automated AI media intelligence, multi-person facial recognition, and dynamic cultural kinship to FamilyVault. Group photos uploaded by family members are scanned for multiple faces, matched against the Vance Clan biometric face bank using 512D ArcFace embeddings, and automatically sorted:
- High confidence matches (>= 0.85) route directly to member generational timelines.
- Ambiguous or group matches route to the Household Head Media Inbox for manual triage with bounding box overlays and color-coded confidence meters.
- The Graph Service dynamically calculates Indian cultural kinship terminology (Chacha, Tauji, Mama, Bua, Masi) along with mathematical acyclic family tree verification.

---

## 2. Master Chronological Deliverables Sequence by Owner

```
[D1: Runeet (Core Media API)]
       │
       ▼
[D2: Ayushman (InsightFace Multi-Clustering)]
       │
       ▼
[D3: Runeet (Batch Triage & Audit API)]
       │
       ▼
[D4: Raghuvendra (Media Inbox UI & Overlays)]
       │
       ▼
[D5: Riya (Cultural Kinship & Paradox Checks)]
       │
       ▼
[D6: Anushka (Lineage Kinship Glow Path)]
       │
       ▼
[D7: Ayush (Biometric Edge-Case Test Suite)] -> SPRINT 4 GATE PASSED
```

### Detailed Deliverable Breakdown

| Deliverable & Owner | Preceding Work (Must Be Done First) | Scope & Technical Work Executed | Output Artifact / Delivered Contract | Next Owner & Work Triggered | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Deliverable 1**<br>**Runeet**<br>*(Lead Architect / Core Backend)* | Postgres schema with `media_contributions` table. | Builds Core Media schemas, registration endpoint `POST /api/v1/media/`, and timeline query `GET /api/v1/media/timeline/{user_id}` with strict RLS tenant isolation. | `backend/app/schemas/media.py`<br>`backend/app/api/v1/endpoints/media.py` | **Ayushman** (Biometrics Lead)<br>Triggered to connect multi-face detection. | **DONE** |
| **Deliverable 2**<br>**Ayushman**<br>*(Biometrics Lead)* | **Deliverable 1**<br>(Runeet's media schema & R2 presigned upload pipeline). | Extends InsightFace 512D ArcFace pipeline to extract multi-face embeddings from group photos, evaluating cosine similarity against known member face banks and tagging action_required flags. | `biometrics/face_processor.py`<br>`biometrics/main.py`<br>`contracts/media-match-response.json` | **Runeet** (Core Backend)<br>Triggered to build Single & Batch Triage API. | **DONE** |
| **Deliverable 3**<br>**Runeet**<br>*(Core Backend)* | **Deliverable 2**<br>(Ayushman's biometric match response contract). | Builds `PATCH /api/v1/media/{media_id}/triage` and `POST /api/v1/media/batch-triage` endpoints with transactional status transition (`PENDING_INBOX` -> `AUTO_PUBLISHED` / `REJECTED`) and auditor logging (`approved_by`, `approval_timestamp`). | `backend/app/api/v1/endpoints/media.py`<br>`backend/tests/test_sprint4_and_sprint5.py` | **Raghuvendra** (Dashboard UI)<br>Triggered to wire live media inbox UI. | **DONE** |
| **Deliverable 4**<br>**Raghuvendra**<br>*(Dashboard Frontend)* | **Deliverable 3**<br>(Runeet's triage endpoints and Ayushman's inbox API). | Builds `/dashboard/inbox` with multi-select checkboxes, bounding box SVG overlays, color-coded confidence meters (green >=0.85, amber 0.70-0.85, red <0.70), and single/batch triage action buttons. | `frontend/app/dashboard/inbox/page.tsx`<br>`frontend/components/inbox/inbox-grid.tsx`<br>`frontend/lib/media-inbox.ts` | **Riya** (Graph Service Lead)<br>Triggered to supply kinship badges for contributors. | **DONE** |
| **Deliverable 5**<br>**Riya**<br>*(Graph Service Lead)* | Seeded Neo4j graph and Vance Clan relationships. | Implements dynamic cultural kinship deduction (`GET /api/graph/kinship`) resolving Indian terminology (Chacha, Tauji, Mama, Bua, Masi) and cyclic ancestry paradox validation. | `graph-service/kinship.py`<br>`GET /api/graph/kinship/{from_id}/{to_id}` | **Anushka** (Tree Frontend)<br>Triggered to render kinship glowing path on tree canvas. | **DONE** |
| **Deliverable 6**<br>**Anushka**<br>*(Tree Frontend Engineer)* | **Deliverable 5**<br>(Riya's dynamic cultural kinship endpoint). | Wires cultural kinship endpoint to React Flow canvas; clicking any two members calculates relationship and highlights genealogical traversal path with glowing SVG edges and cultural kinship pill. | `frontend/components/family/KinshipPathGlow.tsx`<br>`frontend/app/dashboard/family/page.tsx` | **Ayush** (Security & QA)<br>Triggered to run biometric edge-case test suite. | **DONE** |
| **Deliverable 7**<br>**Ayush**<br>*(Security & QA Engineer)* | **Deliverables 1 to 6**<br>(All services operational). | Executes automated edge-case test suite verifying 0-face landscape photos, multi-face group reunions, threshold boundary conditions (0.849 rejection vs 0.850 match), and persistence invariance. | `tests/test_biometric_edgecases.py`<br>100% Pass (5/5 tests) | **Entire Team**<br>Sprint 4 Deliverables Verified & Closed. | **DONE** |

---

## 3. Verification Commands

```powershell
# 1. Run Backend Media Triage & Timeline Tests
cd backend
python -m pytest tests/test_sprint4_and_sprint5.py -v

# 2. Run Biometric Edge-Case Test Suite
cd ..
python -m pytest tests/test_biometric_edgecases.py -v

# 3. Verify Frontend Typecheck & Turbopack Build
cd frontend
npm run typecheck
npm run build
```
