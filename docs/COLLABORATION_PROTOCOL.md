# FamilyVault — Team Collaboration & Execution Protocol

**Target Completion:** September 2, 2026 | **Final Demo:** September 3, 2026  
**Repository:** [realruneett01/FamilyVault](https://github.com/realruneett01/FamilyVault)  
**Lead & Repo Admin:** Runeet  

---

## 1. One-Time Setup — Day 0 (before Sprint 1 begins)
Every team member must have their local environment configured before feature development begins.

### Role-by-Role Responsibilities:
- **Runeet (Repo Owner / Admin)**:
  - Repository initialized with `main` and `develop` branches.
  - Branch protection enabled (requires PR approval, blocks direct pushes).
  - Add teammates as collaborators (`Raghuvendra`, `Anushka`, `Riya`, `Ayushman`, `Ayush`).
  - Top-level folders: `/frontend`, `/backend`, `/graph-service`, `/biometrics`, `/contracts`, `/tests`, `/docs`.
  - Author `CONTRIBUTING.md`, `.gitignore`, and `docs/COLLABORATION_PROTOCOL.md`.
  - Provision Supabase PostgreSQL project and record credentials in the shared credentials document.
- **Riya (Graph Infrastructure)**:
  - Provision Neo4j AuraDB instance; share Bolt URI and credentials.
  - Align with Runeet on UUID convention linking PostgreSQL `users.id` to Neo4j `Person.id`.
- **Ayushman (Media Infrastructure)**:
  - Create Cloudflare R2 bucket and API tokens.
  - Document `MATCH_THRESHOLD = 0.85` constant in `/contracts/MATCH_CONSTANTS.json`.
- **Ayush (QA Infrastructure)**:
  - Create GitHub Project Kanban board: `Backlog` → `In Progress` → `Blocked` → `Ready for QA` → `Done`.
  - Draft Sprint 1 testing matrix in `/tests/README.md`.
  - Set up `#familyvault-dev` Slack/Discord channel.
- **Raghuvendra & Anushka (Frontend Bootstrap)**:
  - Raghuvendra initializes Next.js (App Router) + Tailwind + shadcn/ui inside `/frontend` and pushes scaffold to `develop`.
  - Anushka pulls `develop` and sets up `@xyflow/react` for the tree canvas.

### 1.1 Shared Credentials Document
Maintained in a secure document accessible only to the 6 team members. Contains Supabase keys, Neo4j connection string, Cloudflare R2 tokens, and constants. **Zero credentials committed to git.**

---

## 2. Contracts-First Handoff (Breaking Dependency Chains)
To eliminate idle wait time across dependencies (Runeet → Riya → Anushka, and Riya/Ayushman → Raghuvendra), API owners must publish contract files on Day 1–2 of the sprint:
- **Runeet**: Add `/contracts/schema.sql` by Day 1 documenting tables, RLS logic, and the shared UUID convention for Riya.
- **Riya**: Add `/contracts/graph-tree-response.json` by Day 2 mocking `GET /api/graph/tree` for Anushka.
- **Ayushman**: Add `/contracts/media-match-response.json` by Day 2 mocking biometric match/inbox payloads for Raghuvendra.
- **Rules**: Any schema or contract change must be communicated immediately in `#familyvault-dev`.

---

## 3. Git Workflow Conventions

### Branch Naming:
- `feature/<firstname>-<short-description>` (e.g., `feature/runeet-db-schema`, `feature/riya-neo4j-init`)
- `fix/<firstname>-<short-description>`

### Commit Messages:
Conventional prefixes: `feat:`, `fix:`, `chore:`, `test:`, `docs:`. Example: `feat: add shortestPath kinship query`.

### Pull Request Rules:
1. Target branch is **always** `develop` (never `main`).
2. Provide a 1-line description of what changed and affected contracts/endpoints.
3. Tag assigned reviewer; changes touching auth, RLS, or biometrics must also tag **Ayush**.
4. Reviews must be completed the same working day.
5. Squash-merge once approved, then delete the branch.

### Reviewer Pairings:
- **Runeet ↔ Riya**: Schema & UUID synchronization.
- **Raghuvendra ↔ Anushka**: Frontend UI & interactive canvas.
- **Ayushman → Ayush**: Biometric security and signed URL pipelines.
- **Ayush's Test Suites**: Reviewed by the owner of the tested service.

### Main Branch Releases:
Only **Runeet** merges `develop` → `main` at sprint end after Ayush confirms all test items pass. Each merge is tagged (`sprint-1`, `sprint-2`, etc.).

---

## 4. Sprint Breakdown

### Sprint 1: Foundations, Schemas & Base Scaffolding
- **Runeet**: `feature/runeet-db-schema`, `feature/runeet-rls-policies`
  - DDL for `joint_families`, `nuclear_families`, `users`, `documents`, `media_contributions`, `health_records`, `pets`, `properties`.
  - Three-tier RLS policies and `/contracts/schema.sql`.
- **Riya**: `feature/riya-neo4j-init`
  - Node constraints (`:Person`), initial Cypher schema, UUID verification.
- **Raghuvendra**: `feature/raghuvendra-dashboard-shell`
  - Landing page, dashboard navigation, and authentication client shell.
- **Anushka**: `feature/anushka-treecanvas-base`
  - React Flow canvas with pan/zoom and placeholder nodes.
- **Ayushman**: `feature/ayushman-r2-upload`
  - Cloudflare R2 bucket integration and signed URL upload endpoints in `/biometrics`.
- **Ayush**: Smoke-test schema, draft test matrix, configure issue board.

### Sprint 2: Core Domain APIs, Seeding & Tree Canvas
- **Runeet**: CRUD routes for Vault, Pets, Health, Properties; Emergency Dossier route; 3-generation narrative seed script (`backend/scripts/seed.py`).
- **Riya**: Cypher shortestPath kinship algorithm, `GET /api/graph/tree`.
- **Raghuvendra**: Nuclear family dashboard views wired to Runeet's APIs.
- **Anushka**: Connect React Flow tree to `/api/graph/tree`.
- **Ayushman**: InsightFace 512D embedding generator.
- **Ayush**: Automated CRUD test suite and RLS tenant isolation tests.

### Sprint 3: Biometric Pipeline & Inbox Approval Workflow
- **Ayushman**: Cosine similarity matching (`MATCH_THRESHOLD = 0.85`), automated face-to-graph tagging.
- **Raghuvendra**: Media Inbox UI with Accept/Reject actions and kinship badges.
- **Anushka**: Tree canvas search, auto-centering, zoom limits, and member drawer.
- **Runeet & Riya**: Pair verification of Postgres UUID ↔ Neo4j Person ID synchronization across all seeded users.
- **Ayush**: Biometric boundary tests and multi-tenant RLS penetration attack tests.

### Sprint 4: Final Audit, Bug Fixes & Deployment
- **Ayush (Lead)**: End-to-end security penetration audit and P0/P1 triage.
- **Raghuvendra & Anushka**: Mobile viewport responsiveness and UI polish.
- **Runeet, Riya & Ayushman**: Query optimizations, exception handling, backend deployment to Render/Railway, frontend deployment to Vercel.
- **Release**: Runeet merges `develop` → `main` and tags `sprint-4-release`.

---

## 5. Elevated AI-Augmented Architecture Standards (Team Mandate)
Every team member is utilizing AI assistants; standard CRUD is baseline. FamilyVault is built as an enterprise-grade generational operating system:

1. **Runeet (Backend & Database)**:
   - **Three-Tier RLS**: `JOINT_CLAN`, `NUCLEAR_HOUSEHOLD`, `PRIVATE_STRICT`.
   - **Milestone-Locked Vault & Digital Will**: Timestamp or trustee-verified unlock conditions.
   - **Emergency 'Red Alert' Medical Dossier**: Instant compilation endpoint (`POST /api/v1/health/emergency-dossier/{user_id}`).
   - **Single Source of Truth UUID Sync**: PostgreSQL `users.id` = Neo4j `Person.id`.
2. **Riya (Graph & Kinship)**:
   - **Cultural Kinship Engine**: Indian kinship terminology (Chacha, Mama, Bua, Gotra) and mathematical paradox validation (no cyclic ancestry).
3. **Ayushman (Biometrics & Storage)**:
   - **Multi-Person Face Detection**: Detect multiple family members in group photos.
   - **Auto-Tagging to Graph Nodes**: Automatically associate detected faces with Neo4j person nodes.
4. **Anushka & Raghuvendra (Frontend)**:
   - **Generational Memory Horizon**: Interactive node click drawers, kinship path highlighting, and media lore timeline.
5. **Ayush (Security & QA)**:
   - **Cross-Tenant Breach Simulation**: Automated scripts attempting unauthorized multi-tenant data access.
