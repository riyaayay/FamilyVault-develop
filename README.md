# FamilyVault 🏛️

> **A Generational Operating System for joint Indian families** — secure document vault, biometric media timeline, interactive kinship graph, and emergency medical protocol, built as a resume-ready full-stack prototype.

---

## ✨ Architecture Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        FAMILYVAULT SYSTEM TOPOLOGY                        │
├───────────────────────────────────────────────────────────────────────────┤
│  Next.js 15 Frontend (:1111)                                              │
│  ├── /login          → Living-character auth (saccadic eye tracking)      │
│  ├── /dashboard      → Bento grid home                                    │
│  ├── /dashboard/family      → React Flow lineage tree (Neo4j-backed)      │
│  ├── /dashboard/nuclear-family → Household roster, pets, media upload     │
│  ├── /dashboard/vault → Time capsules & digital wills                     │
│  ├── /dashboard/health → Clan health board + Emergency Red Alert          │
│  ├── /dashboard/inbox → Biometric media triage                            │
│  └── /dashboard/lore  → Generational photo/audio/video timeline           │
│                                                                           │
│  FastAPI Core Backend (:8000) — Python 3.11                               │
│  ├── /api/v1/health   → Health records, Emergency Dossier (SHA-256)       │
│  ├── /api/v1/vault    → 3-tier RLS vault, Time Capsule, Digital Will      │
│  ├── /api/v1/media    → Biometric media ingestion & triage                │
│  ├── /api/v1/users    → Clan directory, Graph sync endpoint               │
│  ├── /api/v1/pets     → Household pets & vaccination schedules            │
│  └── /api/v1/properties → Ancestral real estate registry                 │
│                                                                           │
│  Neo4j Graph Service (:8001) — Python                                     │
│  ├── /api/graph/tree     → React Flow node/edge payload                   │
│  ├── /api/graph/kinship  → Chacha/Mama/Bua traversal (Cypher)             │
│  └── /api/graph/person   → Person upsert (service-role auth)              │
│                                                                           │
│  Biometrics Microservice (:8002) — Python + InsightFace                   │
│  ├── Smart routing: ≥0.85 cosine → Timeline / <0.85 → Inbox              │
│  └── R2 presigned upload (15-min expiry) + 512D ArcFace embeddings        │
│                                                                           │
│  PostgreSQL 16 (:54322) — Supabase-compatible schema with full RLS        │
│  Neo4j AuraDB (or local) — Person nodes + familial edges                  │
│  Cloudflare R2 — Media object storage                                     │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (Local Docker)

### Prerequisites
- Docker Desktop ≥ 4.x
- Node.js 20+
- Python 3.11+

### 1. Environment Setup
```bash
cp .env.example .env
# Edit .env — fill in SUPABASE_* and R2_* values from your project dashboard.
# For purely local dev (no Supabase/R2), the defaults work out of the box.
```

### 2. Start All Services with Docker Compose
```bash
docker compose up --build
```

Services available at:
| Service | URL |
|---|---|
| Frontend | http://localhost:1111 |
| Core Backend API | http://localhost:18000/docs |
| Graph Service | http://localhost:18001 |
| Biometrics Service | http://localhost:18002 |
| PostgreSQL | localhost:54322 |
| Neo4j Browser | http://localhost:7474 |

### 3. Seed the Database (Vance Clan Benchmark)
```bash
cd backend
pip install -r requirements.txt
python scripts/seed.py
```

### 4. Sync Postgres → Neo4j
```bash
python scripts/sync_postgres_to_neo4j.py
```

---

## 🔧 Local Development (Without Docker)

**Terminal 1 — PostgreSQL** (or use your Supabase project URL):
```bash
# Start local postgres on port 54322, then apply schema:
psql -h localhost -p 54322 -U postgres -f contracts/local/00_supabase_shim.sql
psql -h localhost -p 54322 -U postgres -f contracts/schema.sql
```

**Terminal 2 — Core Backend**:
```bash
cd backend
pip install -r requirements.txt
python scripts/seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 3 — Graph Service**:
```bash
cd graph-service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 4 — Biometrics**:
```bash
cd biometrics
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

**Terminal 5 — Frontend**:
```bash
cd frontend
npm ci
npm run dev -- -p 1111
```

---

## 🏗️ Feature Catalogue

### 1. Three-Tier Row Level Security (RLS)
Documents, health records, media, and properties are protected at the Postgres level by Supabase RLS policies enforcing three visibility tiers:
- `JOINT_CLAN` — shared across all households under the ancestral clan
- `NUCLEAR_HOUSEHOLD` — confined to a specific household unit
- `PRIVATE_STRICT` — owner + named trustees only

The FastAPI layer re-enforces the same policy in code so the service-role connection can never be misused.

### 2. Milestone-Locked Vault & Digital Will Engine
- Documents can be sealed with a future `time_capsule_unlock_at` timestamp
- Wills require a quorum of designated trustee signatures to release
- `POST /api/v1/vault/{id}/sign` — trustee signature (idempotent)
- `PATCH /api/v1/vault/{id}/unlock` — date/quorum release
- Real-time countdown UI with trustee progress bar

### 3. Emergency Red Alert Protocol
- `POST /api/v1/health/emergency-dossier/{user_id}` — compiles a tamper-proof SHA-256-hashed medical dossier in <50 ms
- `POST /api/v1/health/emergency-pass/{user_id}` — mints a signed 24-hour HMAC pass (QR-codeable link for first responders)
- Always-visible SOS button on every dashboard page triggers clan-wide alert broadcast

### 4. Biometric Smart Routing
- InsightFace RetinaFace + ArcFace pipeline generates 512D normalized embeddings
- **≥ 0.85 cosine similarity** → auto-published to member's Milestone Timeline
- **< 0.85** → routed to Media Inbox for household-head triage
- Non-image files (PDF, audio, DOCX) bypass detection → direct to Vault

### 5. Interactive Kinship Graph (Neo4j)
- Person nodes synced from Postgres with a single `GET /api/v1/users/sync/persons` call (service-role authenticated)
- Cypher shortest-path engine resolves complex Indian kinship labels (Chacha, Mama, Bua, Nani…)
- React Flow canvas with custom SVG nodes: Patriarch/Head, Ancestor, Living Members

### 6. Generational Lore Timeline
- Published media grouped by year — photos, audio notes, video clips
- Falls back to curated Vance clan offline demo data when backend is unreachable

---

## 🔐 Security Architecture

### Authentication Stack
| Path | Mechanism |
|---|---|
| Browser sessions | Supabase access tokens (HS256 / ES256 / RS256 via JWKS) |
| Service calls (graph-sync) | `X-API-Key` / `X-Service-Key` HMAC-compared |
| Emergency passes | Custom HMAC-SHA256 signed tokens, 24 h TTL |
| Local dev fallback | `DEBUG=True` → authenticated as "Runeet (Lead Admin)" |

### Audit Trail
Every sensitive action — emergency dossier access, trustee signatures, capsule releases, media triage — writes an immutable row to `audit_logs`, readable only by clan ADMINs.

---

## 🧪 Testing

```bash
# Backend unit + integration tests
cd backend && PYTHONPATH=. pytest -v

# Graph service tests
cd graph-service && PYTHONPATH=. pytest -v

# Cross-tenant RLS penetration tests (requires seeded DB)
cd tests && PYTHONPATH=.. pytest test_cross_tenant_pentest.py -v

# Frontend type-check + build
cd frontend && npm run build
```

CI runs automatically on push to `develop` and `main` via **GitHub Actions** (`.github/workflows/ci.yml`).

---

## 📁 Project Structure

```
FamilyVault/
├── .github/workflows/ci.yml     # CI — Postgres + pytest + Next.js build
├── contracts/
│   ├── schema.sql               # Authoritative Postgres schema + RLS policies
│   ├── local/00_supabase_shim.sql # auth.uid() shim for local/CI Postgres
│   ├── migrations/              # Additive schema migrations
│   └── graph-tree-response.json # React Flow contract (fallback)
├── backend/                     # FastAPI Core API (Python 3.11)
│   ├── app/
│   │   ├── api/v1/endpoints/    # health, vault, media, users, pets, properties
│   │   ├── core/                # config, database, security, audit
│   │   └── models/              # SQLAlchemy ORM models
│   └── scripts/
│       ├── seed.py              # Vance clan 3-generation deterministic seed
│       └── sync_postgres_to_neo4j.py
├── graph-service/               # Neo4j kinship engine (Python)
│   ├── main.py                  # FastAPI app + kinship routes
│   ├── kinship.py               # Cypher traversal + Indian kinship labelling
│   ├── auth.py                  # Caller scoping (jwt/off modes)
│   └── trustee.py               # Trustee governance graph queries
├── biometrics/                  # InsightFace pipeline (Python)
│   ├── main.py                  # Upload, recognition, smart routing
│   ├── face_processor.py        # RetinaFace + ArcFace 512D
│   └── media_store.py           # R2 + local-disk fallback
├── frontend/                    # Next.js 15 App Router (TypeScript)
│   ├── app/dashboard/           # All dashboard pages
│   ├── components/              # Reusable UI components
│   └── lib/                     # API clients, data layers
├── tests/                       # Cross-service security & integration tests
├── docker-compose.yml           # Full-stack local orchestration
└── .env.example                 # Environment variable template
```

---

## 🗺️ Canonical Vance Clan Benchmark (Seed Data)

| Gen | Name | Role | UUID |
|---|---|---|---|
| 1 | Arthur Vance | ADMIN / HEAD | `...000001` |
| 1 | Eleanor Vance | ADMIN / SPOUSE | `...000002` |
| 2 | David Vance | MEMBER / CHILD | `...000003` |
| 2 | Sarah Vance | MEMBER / SPOUSE | `...000004` |
| 2 | Michael Vance | MEMBER / CHILD | `...000005` |
| 2 | Clara Vance | MEMBER / SPOUSE | `...000006` |
| 2 | Robert Vance | MEMBER / CHILD | `...000007` |
| 3 | Lucas Vance | CHILD | `...000008` |
| 3 | Sophia Vance | CHILD | `...000009` |
| 3 | Emma Vance | VIEWER | `...000010` |

Clan ID: `11111111-1111-1111-1111-111111111111`  
Household A: `22222222-2222-2222-2222-222222222222`  
Household B: `33333333-3333-3333-3333-333333333333`

---

## 🌐 Deployment

### Recommended Stack
| Layer | Platform |
|---|---|
| Frontend | Vercel (automatic from `main`) |
| Core Backend | Railway / Render |
| Graph Service | Railway / Render |
| Biometrics | Railway (GPU optional) |
| Database | Supabase (PostgreSQL 15/16 + RLS built-in) |
| Graph DB | Neo4j AuraDB Free/Enterprise |
| Media Storage | Cloudflare R2 |

### Required Secrets (Production)
```
DATABASE_URL               # Supabase connection string
SUPABASE_URL               # https://your-project.supabase.co
SUPABASE_ANON_KEY          # Public anon key
SUPABASE_SERVICE_ROLE_KEY  # Private service key
SUPABASE_JWT_SECRET        # JWT signing secret (Settings > API)
R2_ACCOUNT_ID              # Cloudflare account ID
R2_ACCESS_KEY_ID           # R2 API key
R2_SECRET_ACCESS_KEY       # R2 API secret
R2_BUCKET_NAME             # e.g. familyvault-media
R2_PUBLIC_DOMAIN           # https://media.yourdomain.com
NEO4J_URI                  # bolt+s://your-aura.databases.neo4j.io
NEO4J_USERNAME             # neo4j
NEO4J_PASSWORD             # AuraDB generated password
```

---

## 👥 Team

| Role | Owner | Scope |
|---|---|---|
| Lead Architect / Core Backend | Runeet | Schema, API, auth, emergency protocol |
| Graph Service | Riya | Neo4j kinship engine, tree sync |
| Biometrics / Media | Ayushman | InsightFace pipeline, R2 storage |
| Frontend (Dashboard) | Raghuvendra | Nuclear family dashboard, Vault UI |
| Frontend (Tree / Auth) | Anushka | React Flow canvas, Living Character auth |
| Security / QA | Ayush | RLS penetration tests, audit |

---

## 📋 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch strategy, PR guidelines, and the API contract process.
