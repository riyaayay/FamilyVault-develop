# FamilyVault — Sprint 1 Testing & Edge Case Matrix
**Owner:** Ayush (Lead QA, Security & Edge Case Auditor)  
**Sprint Window:** Aug 22 – Aug 24  
**Deliverable Path:** `testing-matrix.md` (Root)  
**Target Branch:** `develop` (Direct Push, Docs-only)  

---

## 1. Database Permission & RLS Isolation Matrix (`contracts/schema.sql`)

| # | Table / Domain | Seeded Personas / Actors | Test Scenario | Expected Result | Owner | Status |
|---|---|---|---|---|---|---|
| 1 | `joint_families` | Michael Vance (Nuclear B) | Attempt `SELECT` on unrelated tenant joint clan | 0 rows returned via RLS | Runeet | ☐ |
| 2 | `nuclear_families` | David Vance (Nuclear A Head) | Attempt `SELECT` on Nuclear B records | 0 rows returned | Runeet | ☐ |
| 3 | `users` | Lucas Vance (Gen 3 Nuclear A) | Attempt `SELECT` on profile outside joint clan | 0 rows returned | Runeet | ☐ |
| 4 | `users` | Arthur Vance (Gen 1 Admin) | Update self profile row | `200 OK` / row updated | Runeet | ☐ |
| 5 | `documents` | Eleanor Vance (Gen 1 Admin) | Access `JOINT_CLAN` tier doc in own clan | Row returned | Runeet | ☐ |
| 6 | `documents` | Michael Vance (Nuclear B Head) | Access `NUCLEAR_HOUSEHOLD` doc belonging to Nuclear A (e.g. David's Deed) | 0 rows returned | Runeet | ☐ |
| 7 | `documents` | Sarah Vance (Nuclear A) | Access `NUCLEAR_HOUSEHOLD` doc within Nuclear A | Row returned | Runeet | ☐ |
| 8 | `documents` | Robert Vance (Gen 2 Uncle) | Select `PRIVATE_STRICT` document not addressed to him | 0 rows returned | Runeet | ☐ |
| 9 | `documents` | Target Recipient | Select `PRIVATE_STRICT` document where `capsule_status != 'RELEASED'` | 0 rows (locked until status changes) | Runeet | ☐ |
| 10 | `documents` | Emma Vance (Gen 3 Viewer) | Access `time_capsule_unlock_at` future doc (`capsule_status = 'LOCKED'`) | 0 rows returned, even under JOINT_CLAN | Runeet | ☐ |
| 11 | `documents` | Document Uploader | Query uploaded doc regardless of tier/lock state | Row returned (uploader override policy) | Runeet | ☐ |
| 12 | `documents` | Clara Vance (Nuclear B) | Attempt `INSERT` doc into Nuclear A household | Rejected by RLS `WITH CHECK` clause | Runeet | ☐ |
| 13 | `media_contributions`| David Vance (Nuclear A) | Select `PENDING_INBOX` item not in `matched_face_ids` | 0 rows returned | Runeet | ☐ |
| 14 | `media_contributions`| Sophia Vance (Gen 3 Nuclear B) | Select `PENDING_INBOX` item where `users.id` in `matched_face_ids` | Row returned | Runeet | ☐ |
| 15 | `health_records` | Michael Vance (Nuclear B) | Access Sarah Vance's health logs (`is_emergency_visible = false`) | 0 rows returned | Runeet | ☐ |
| 16 | `health_records` | Arthur Vance (Joint Admin) | Access Eleanor's cardiology record (`is_emergency_visible = true`) | Row returned | Runeet | ☐ |
| 17 | `pets` / `properties`| External Clan User | Attempt cross-clan access to Vance property deed / pet profile | 0 rows returned | Runeet | ☐ |
| 18 | `audit_logs` | Lucas Vance (Gen 3 Viewer) | Query clan audit logs without `ADMIN` role | 0 rows returned | Runeet | ☐ |
| 19 | Cross-cutting | App Backend Client | Issue database query without valid `auth.uid()` (Service role leakage) | Blocked; queries must enforce user session claims | Runeet | ☐ |

---

## 2. Biometric Pipeline & Cloudflare R2 Upload Matrix (`contracts/MATCH_CONSTANTS.json` & `/biometrics`)

| # | Case | Input / Parameters | Expected Routing / Result | Owner | Status |
|---|---|---|---|---|---|
| 20 | Sub-threshold similarity | Cosine similarity = `0.849` | Divert to inbox queue (`PENDING_INBOX`) | Ayushman | ☐ |
| 21 | Exact boundary match | Cosine similarity = `0.850` | Auto-publish to recipient gallery (`>= 0.85`) | Ayushman | ☐ |
| 22 | High confidence match | Cosine similarity = `0.851` | Auto-publish to recipient gallery | Ayushman | ☐ |
| 23 | Non-image media routing | Similarity $\ge 0.85$, `media_type = 'video'` or `'audio'` | Divert to inbox queue regardless of score (`OR` rule) | Ayushman | ☐ |
| 24 | Zero face detection | Photo uploaded with no detectable face | Route to manual review/inbox; zero unhandled exceptions | Ayushman | ☐ |
| 25 | Multi-face group photo | Photo containing 2+ Vance family members | Generate separate 512D vectors; map each face independently | Ayushman | ☐ |
| 26 | Rejection persistence | Recipient rejects inbox media item | Media record marked rejected; persists in sender's archive | Ayushman | ☐ |
| 27 | Constant synchronization | Verify hardcoded values across `/biometrics` vs `contracts/MATCH_CONSTANTS.json` | 100% parity; single source of truth (`0.85`) | Ayushman | ☐ |
| 28 | Presigned URL round-trip | Postman PUT request with sample JPEG to generated R2 signed URL | `200 OK`; object accessible in target bucket path | Ayushman | ☐ |
| 29 | Expired presigned URL | Upload attempt after signed URL expiry window | `403 Forbidden` / Signature Expired from Cloudflare R2 | Ayushman | ☐ |

---

## 3. Graph Schema & Kinship Resolution Matrix (`graph-service/init_schema.cypher`)

| # | Case | Graph State / Cypher Query Target | Expected Constraint / Behavior | Owner | Status |
|---|---|---|---|---|---|
| 30 | `Person.id` uniqueness | Insert duplicate `:Person {id: uuid}` into Neo4j | Constraint violation error; transaction aborted | Riya | ☐ |
| 31 | UUID synchronization | Cross-match `users.id` (Postgres) against `:Person.id` (Neo4j AuraDB) | 1:1 parity across all 10 Vance seeded profiles | Riya / Runeet | ☐ |
| 32 | Cyclic relationship paradox | Set a member as their own ancestor/descendant | Cyclic paradox blocked by validation engine | Riya | ☐ |
| 33 | Chronological contradiction | Set child `birth_date` earlier than parent's | Relation rejected by domain validation | Riya | ☐ |
| 34 | Tenant graph isolation | Query `shortestPath` from Clan 1 member to Clan 2 member | 0 paths / Empty graph traversal | Riya | ☐ |
| 35 | Multi-gen heads recursion | Recursive query for Joint Family Heads across 3 generations | Terminates cleanly; returns Arthur & Eleanor Vance without loops | Riya | ☐ |
| 36 | Missing node traversal | Traversal path query targeting deleted or isolated node | Safe empty array return; no unhandled 500 error | Riya | ☐ |

---

## Sprint 1 QA Exit Criteria (Ayush)

- [ ] `testing-matrix.md` committed directly to `develop` branch.
- [ ] Every test case (1–36) registered on the GitHub Project Kanban board with assigned tags (`domain:security`, `domain:biometrics`, `domain:graph`) and respective owner.
- [ ] Schema smoke-test completed on `contracts/schema.sql` (Runeet) validating dummy tenant isolation.
- [ ] Constraint smoke-test completed on `graph-service/init_schema.cypher` (Riya) on fresh AuraDB instance.
- [ ] Peer review completed for Ayushman's PR (`feature/ayushman-r2-upload`) after Postman demo confirms signed URL round-trip.