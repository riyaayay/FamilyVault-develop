# Quality Assurance, Testing & Security Matrix

**Owner:** Ayush  
**Stack:** Pytest, Postman Collections, Playwright (E2E), Bash / Python security audit scripts  

## Responsibilities
- Maintain testing matrix covering:
  - Database permission & tenant-isolation cases (PostgreSQL RLS).
  - Biometric threshold boundaries (`0.849` vs `0.850`).
  - Kinship-resolution edge cases.
- Cross-tenant multi-tenant breach simulation scripts: Verify no tenant can access another clan or nuclear family's private vault records.
- Biometric edge cases: multi-face group photos, zero-face detection, and non-destructive rejected media persistence.
- Manage the GitHub Project Kanban board and lead final penetration audit in Sprint 4.

## Getting Started
Refer to [docs/COLLABORATION_PROTOCOL.md](../docs/COLLABORATION_PROTOCOL.md) for branch naming (`feature/ayush-*`) and PR conventions.

## Security & RLS Test Suite
To run all Row Level Security (RLS) penetration tests against the local database:
python -m pytest tests/test_rls_policies.py -v


=======

## Biometric Edge-Case & Boundary Suite
Validates the 0.850 auto-publish boundary vs 0.849 inbox routing cutoff, zero-face uploads, multi-person detections, and persistent storage invariance:
python -m pytest tests/test_biometric_edgecases.py -v

## Cross-Database Parity & Orphan Detection
Asserts 100% 1-to-1 UUIDv4 parity between PostgreSQL users.id and Neo4j graph nodes across the 10 seeded personas, verifying zero orphaned nodes and graph edge referential integrity:
python -m pytest tests/test_crossdb_orphan_detection.py -v

## Cross-Tenant RLS Penetration Attack Suite
Simulates forged JWT claims and malicious tenant boundaries to test cross-household isolation, external clan intrusion, premature time-capsule unlocks, and role-based write prevention:
python -m pytest tests/test_cross_tenant_pentest.py -v