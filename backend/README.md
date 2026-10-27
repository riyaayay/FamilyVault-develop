# FamilyVault — Core FastAPI Backend

**Lead Architect:** Runeet  
**Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), asyncpg, Supabase Auth  

## Core Architecture
- `app/core/config.py`: Environment settings with Pydantic Settings validation.
- `app/core/database.py`: Async SQLAlchemy session lifecycle management.
- `app/core/security.py`: JWT authentication, token verification, and tenant context extraction (`get_current_user`, `get_current_tenant`).
- `app/models/`: Declarative SQLAlchemy ORM models mirroring `contracts/schema.sql`.
- `app/schemas/`: Pydantic input/output schemas with serialization validation.
- `app/api/v1/`: Versioned API endpoints (Health, Emergency Red Alert Dossier, Document Vault, User Directory).

## Local Development Setup
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```
4. Run the development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
5. Open interactive API documentation at: `http://localhost:8000/docs`
