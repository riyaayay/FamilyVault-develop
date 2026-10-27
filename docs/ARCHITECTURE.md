# FamilyVault — System Architecture

This document defines the polyglot service architecture, cross-service contracts, and data synchronization patterns for the FamilyVault ecosystem.

---

## 1. High-Level System Architecture

```
                               ┌────────────────────────────────────────┐
                               │               Next.js App              │
                               │     (Frontend / App Router / Vercel)   │
                               │  Raghuvendra (Dashboard) & Anushka (Tree) │
                               └──────────────────┬─────────────────────┘
                                                  │
                                                  ▼
                        ┌──────────────────────────────────────────────────┐
                        │             API Gateway / Routing Layer          │
                        └────────┬─────────────────┬─────────────────┬─────┘
                                 │                 │                 │
                                 ▼                 ▼                 ▼
             ┌─────────────────────────┐  ┌──────────────────┐  ┌─────────────────────────┐
             │       FastAPI Core      │  │  Graph Service   │  │   Biometrics Service    │
             │   (Backend / Python)    │  │ (Neo4j / Cypher) │  │  (InsightFace / Cloudflare)│
             │     Runeet (Lead)       │  │   Riya (Graph)   │  │   Ayushman (Biometrics) │
             └────────────┬────────────┘  └────────┬─────────┘  └────────────┬────────────┘
                          │                        │                         │
                          ▼                        ▼                         ▼
             ┌─────────────────────────┐  ┌──────────────────┐  ┌─────────────────────────┐
             │   Supabase PostgreSQL   │  │  Neo4j AuraDB    │  │      Cloudflare R2      │
             │  (Multi-Tier RLS Vault) │  │ (Kinship Graph)  │  │   (Encrypted Media S3)  │
             └─────────────────────────┘  └──────────────────┘  └─────────────────────────┘
```

---

## 2. Cross-Service Single Source of Truth: UUID Sync

To avoid ID drift across heterogeneous databases, all services adhere to a strict invariant:

1. **User / Person Entity**:
   - `users.id` is generated **once** in PostgreSQL as a UUIDv4 (linked to Supabase Auth).
   - Neo4j creates `(:Person {id: "<UUID>"})` using the **exact same string value**.
   - Biometric embedding records store the **same UUID string** in `matched_face_ids`.
   - Under no circumstances does Neo4j or the biometrics service generate a separate independent ID for a person.

```
PostgreSQL users.id (UUIDv4)
   ├──> Neo4j (:Person {id: users.id})
   └──> Biometrics media_contributions.matched_face_ids [users.id]
```

---

## 3. Security & Three-Tier Row Level Security (RLS)

PostgreSQL implements three distinct visibility tiers enforced directly at the database engine via Supabase RLS:

| Visibility Tier | Access Scope | Examples |
| :--- | :--- | :--- |
| `JOINT_CLAN` | All nuclear families belonging to the top-level `joint_families` tenant. | Ancestral property deeds, shared tree, family folklore, public photos. |
| `NUCLEAR_HOUSEHOLD` | Only authenticated members belonging to that specific `nuclear_families` unit. | Personal tax documents, private medical reports, household bank records. |
| `PRIVATE_STRICT` | Only the document creator and explicitly approved trustees. | Digital wills, emergency unlock capsules, personal notes. |

---

## 4. Contracts-First Interface Directory

All shared contracts are versioned under `/contracts`:
- `contracts/schema.sql`: Authoritative PostgreSQL schema and RLS policies.
- `contracts/MATCH_CONSTANTS.json`: Shared biometric thresholds (`MATCH_THRESHOLD = 0.85`, vector dimension `512`).
- `contracts/graph-tree-response.json`: Neo4j tree endpoint payload schema.
- `contracts/media-match-response.json`: Biometric match and media inbox schema.
