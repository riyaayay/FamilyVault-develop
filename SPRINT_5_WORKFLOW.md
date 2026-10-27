# FamilyVault — Sprint 5 Master Workflow: Milestone Time Capsules, Multi-Trustee Governance & Emergency Red Alert

**Document Version**: 5.0.0  
**Status**: Completed & Integrated  
**Lead Architect**: Runeet (`realruneett01`)  
**Target Branch**: `develop`  
**Services Covered**: Next.js Frontend (:1111), Core Backend (:8000), Graph Service (:8001), PostgreSQL (54322), Cloudflare R2  

---

## 1. Executive Summary & Sprint Objectives

Sprint 5 operationalizes generational legacy security and life-saving emergency medical response:
1. **Milestone-Locked Time Capsules & Digital Wills**: Documents locked until a specific future date or until a quorum of trusted family trustees digitally sign off. Sealed documents are hidden from unauthorized heirs and transition to `RELEASED` upon quorum fulfillment.
2. **Multi-Trustee Governance Flow**: Cryptographic sign-off API (`POST /api/v1/vault/{doc_id}/sign`) recording signatures and maintaining quorum audit trails.
3. **Emergency 'Red Alert' Protocol**: 24-hour scannable cryptographic emergency telemetry pass (`GET /api/v1/health/emergency-pass/{token}`) with SHA-256 tamper verification, AIIMS cardiology hotline access, pacemaker specifications, and instant clan-wide broadcast triggering (`POST /api/v1/health/emergency-alert/trigger`).

---

## 2. Master Chronological Deliverables Sequence by Owner

```
[D1: Runeet (Time Capsule & Trustee Quorum API)]
       │
       ▼
[D2: Runeet (Emergency Pass & Red Alert Broadcast API)]
       │
       ▼
[D3: Anushka (Milestone Badging & Red Alert Overlay UI)]
       │
       ▼
[D4: Raghuvendra (Nuclear Dashboard Milestone Clocks)]
       │
       ▼
[D5: Riya (Neo4j Trustee Graph & Cypher Traversal)]
       │
       ▼
[D6: Ayush (Cross-Tenant RLS Penetration Pentest)] -> SPRINT 5 GATE PASSED
```

### Detailed Deliverable Breakdown

| Deliverable & Owner | Preceding Work (Must Be Done First) | Scope & Technical Work Executed | Output Artifact / Delivered Contract | Next Owner & Work Triggered | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Deliverable 1**<br>**Runeet**<br>*(Lead Architect / Core Backend)* | PostgreSQL schema with `documents` table and `time_capsule_status` enum. | Builds milestone time capsule engine: timestamp unlock triggers (`time_capsule_unlock_at`), multi-trustee sign-off endpoint (`POST /api/v1/vault/{doc_id}/sign`), and milestone badge query API (`GET /api/v1/vault/milestones/badges`). | `backend/app/api/v1/endpoints/vault.py`<br>`backend/app/schemas/document.py` | **Runeet** (Core Backend)<br>Triggered to author Emergency Pass & Alert API. | **DONE** |
| **Deliverable 2**<br>**Runeet**<br>*(Core Backend)* | Eleanor Vance emergency medical profile and SHA-256 tamper hash. | Implements scannable 24-hour Emergency Telemetry Pass (`GET /api/v1/health/emergency-pass/{token}`) with cryptographic HMAC/SHA-256 verification, and Red Alert Broadcast trigger (`POST /api/v1/health/emergency-alert/trigger`). | `backend/app/api/v1/endpoints/health.py`<br>`backend/tests/test_sprint4_and_sprint5.py` | **Anushka** (Tree Frontend)<br>Triggered to render milestone badges and emergency alert modal. | **DONE** |
| **Deliverable 3**<br>**Anushka**<br>*(Tree Frontend Engineer)* | **Deliverables 1 & 2**<br>(Runeet's milestone badge metadata & emergency pass API). | Implements `MilestoneNodeBadge.tsx` and `EmergencyAlertOverlay.tsx` on the family tree canvas. Members with locked time capsules/wills display lock pills with signature progress (`1/2`); members in distress display pulsing red beacons that open the emergency dossier. | `frontend/components/family/MilestoneNodeBadge.tsx`<br>`frontend/components/family/EmergencyAlertOverlay.tsx`<br>`frontend/app/dashboard/family/page.tsx` | **Raghuvendra** (Dashboard UI)<br>Triggered to wire milestone countdown clocks on nuclear dashboard. | **DONE** |
| **Deliverable 4**<br>**Raghuvendra**<br>*(Dashboard Frontend)* | **Deliverable 3**<br>(Anushka's milestone badges and Runeet's vault APIs). | Updates `/dashboard/nuclear-family` with live milestone countdown clocks, digital will trustee approval status cards, and one-click trustee approval trigger. | `frontend/app/dashboard/nuclear-family/page.tsx` | **Riya** (Graph Service Lead)<br>Triggered to map trustee relationships in Neo4j. | **DONE** |
| **Deliverable 5**<br>**Riya**<br>*(Graph Service Lead)* | Runeet's trustee relationship data in PostgreSQL. | Creates `TRUSTEE_FOR` relationship in Neo4j graph, enabling graph traversal queries that identify authorized family trustees and their generational distance from the testator. | `graph-service/trustee_graph.cypher` | **Ayush** (Security & Pentest Engineer)<br>Triggered to execute RLS penetration attack test suite. | **DONE** |
| **Deliverable 6**<br>**Ayush**<br>*(Security & Pentest Engineer)* | **Deliverables 1 to 5**<br>(All governance and security APIs complete). | Executes multi-tenant breach attack simulation against locked time capsules, unreleased digital wills, and private medical dossiers. Validates zero data leaks across household boundaries. | `tests/test_cross_tenant_pentest.py`<br>`tests/test_rls_policies.py` | **Entire Team**<br>Sprint 5 Deliverables Verified & Closed. | **DONE** |

---

## 3. Verification Commands

```powershell
# 1. Run Sprint 5 Governance & Emergency Pass Backend Tests
cd backend
python -m pytest tests/test_sprint4_and_sprint5.py -v

# 2. Run Emergency Medical Dossier Compilation Test
python -m pytest tests/test_emergency_dossier.py -v

# 3. Verify Frontend Typecheck & Turbopack Build
cd ../frontend
npm run typecheck
npm run build
```
