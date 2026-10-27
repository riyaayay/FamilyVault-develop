import pytest
import pytest_asyncio
import asyncpg
import json

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

ARTHUR_ID  = "00000000-0000-0000-0000-000000000001"  # Admin / Head
MICHAEL_ID = "00000000-0000-0000-0000-000000000005"  # Household B
LUCAS_ID   = "00000000-0000-0000-0000-000000000008"  # Child (Household A)

@pytest_asyncio.fixture
async def rls_conn():
    conn = await asyncpg.connect(DATABASE_URL)
    yield conn
    await conn.close()

async def impersonate(conn, user_id: str, email: str, role: str = "authenticated"):
    claims = json.dumps({"sub": user_id, "email": email, "role": role})
    await conn.execute(f"SET ROLE {role};")
    await conn.execute(f"SELECT set_config('request.jwt.claims', '{claims}', false);")
    await conn.execute(f"SELECT set_config('request.jwt.claim.sub', '{user_id}', false);")

@pytest.mark.asyncio
async def test_rls_household_isolation(rls_conn):
    """Verify Household B cannot access Household A private records."""
    await impersonate(rls_conn, MICHAEL_ID, "michael@familyvault.app")
    docs = await rls_conn.fetch("""
        SELECT title FROM documents 
        WHERE nuclear_family_id = '22222222-2222-2222-2222-222222222222'::uuid;
    """)
    assert len(docs) == 0

@pytest.mark.asyncio
async def test_rls_child_restriction(rls_conn):
    """Verify child persona cannot access private property deeds."""
    await impersonate(rls_conn, LUCAS_ID, "lucas@familyvault.app")
    deeds = await rls_conn.fetch("""
        SELECT * FROM documents 
        WHERE category = 'PROPERTY' AND visibility_tier = 'PRIVATE_STRICT';
    """)
    assert len(deeds) == 0

@pytest.mark.asyncio
async def test_rls_head_of_clan_access(rls_conn):
    """Verify Arthur (Admin & uploader) can view the joint clan document."""
    await impersonate(rls_conn, ARTHUR_ID, "arthur@familyvault.app")
    clan_docs = await rls_conn.fetch("""
        SELECT * FROM documents 
        WHERE joint_family_id = '11111111-1111-1111-1111-111111111111'::uuid
        AND visibility_tier = 'JOINT_CLAN';
    """)
    assert len(clan_docs) >= 1
    assert clan_docs[0]["title"] == "1972 Ancestral Land Deed & Survey"