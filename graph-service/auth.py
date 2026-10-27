"""Caller identity & clan scoping for the graph service.

Row Level Security protects PostgreSQL only, so every Neo4j read must be
scoped to the caller's clan explicitly (report 3.3.3).

GRAPH_AUTH_MODE
  off (default, local dev)  no token needed; reads may still be scoped with
                            an explicit ?clan_id= query parameter.
  jwt (production)          reads need the user's Supabase access token; the
                            caller's clan is the clan_id on their own
                            (:Person {id: sub}) node, so one clan can never
                            read another's tree. Writes need GRAPH_SERVICE_KEY
                            (sent by backend/scripts/sync_postgres_to_neo4j.py).
"""

import hmac
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import jwt
from fastapi import Header, HTTPException, Query

from db import NEO4J_DATABASE, get_driver

AUTH_MODE = os.getenv("GRAPH_AUTH_MODE", "off").strip().lower()
SERVICE_KEY = os.getenv("GRAPH_SERVICE_KEY", "")
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
JWKS_URL = os.getenv("SUPABASE_JWKS_URL") or (
    f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else ""
)


@dataclass
class Caller:
    person_id: Optional[str] = None
    clan_id: Optional[str] = None
    is_service: bool = False


@lru_cache(maxsize=1)
def _jwks_client():
    return jwt.PyJWKClient(JWKS_URL, cache_keys=True)


def _decode(token: str) -> dict:
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        key = JWT_SECRET
    elif alg in ("ES256", "RS256") and JWKS_URL:
        key = _jwks_client().get_signing_key_from_jwt(token).key
    else:
        raise jwt.InvalidAlgorithmError(f"Unsupported token algorithm: {alg}")
    return jwt.decode(token, key, algorithms=[alg], options={"verify_aud": False})


def _clan_of(person_id: str) -> Optional[str]:
    def _read(tx):
        record = tx.run("MATCH (p:Person {id: $id}) RETURN p.clan_id AS clan_id", id=person_id).single()
        return record["clan_id"] if record else None

    with get_driver().session(database=NEO4J_DATABASE) as session:
        return session.execute_read(_read)


def _is_service_key(key: Optional[str]) -> bool:
    return bool(SERVICE_KEY and key and hmac.compare_digest(key, SERVICE_KEY))


def get_caller(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
    clan_id: Optional[str] = Query(default=None, description="Scope reads to one clan (dev mode)"),
) -> Caller:
    """Resolves who is calling and which clan their reads are limited to."""
    if _is_service_key(x_api_key):
        return Caller(clan_id=clan_id, is_service=True)

    if AUTH_MODE != "jwt":
        return Caller(clan_id=clan_id)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        person_id = _decode(authorization.split(" ", 1)[1]).get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if not person_id:
        raise HTTPException(status_code=401, detail="Token has no subject")

    caller_clan = _clan_of(person_id)
    if not caller_clan:
        raise HTTPException(status_code=403, detail="You are not part of any family graph yet")
    if clan_id and clan_id != caller_clan:
        raise HTTPException(status_code=404, detail="Clan not found")
    return Caller(person_id=person_id, clan_id=caller_clan)


def require_writer(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Graph mutations come from the sync pipeline, never straight from browsers."""
    if AUTH_MODE == "jwt" and not _is_service_key(x_api_key):
        raise HTTPException(status_code=401, detail="Graph writes require the service API key")


def assert_in_clan(person_ids: list, clan_id: Optional[str]) -> None:
    """404 unless every person exists in `clan_id` (no-op when unscoped)."""
    if not clan_id:
        return

    def _count(tx):
        return tx.run(
            "MATCH (p:Person) WHERE p.id IN $ids AND p.clan_id = $clan RETURN count(DISTINCT p) AS n",
            ids=list(set(person_ids)),
            clan=clan_id,
        ).single()["n"]

    with get_driver().session(database=NEO4J_DATABASE) as session:
        if session.execute_read(_count) != len(set(person_ids)):
            raise HTTPException(status_code=404, detail="Person not found in your family graph")
