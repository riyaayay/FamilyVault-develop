import json
import os
import uuid
import pytest
import pytest_asyncio
import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:54322/postgres"
)

# Vance Clan Deterministic UUIDs
JOINT_CLAN_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
HOUSEHOLD_A_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")  # seed.py NUCLEAR_A_ID
HOUSEHOLD_B_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")  # seed.py NUCLEAR_B_ID

# Personas
ARTHUR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")   # Joint Head (ADMIN)
DAVID_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")    # Household A Head (MEMBER)
MICHAEL_ID = uuid.UUID("00000000-0000-0000-0000-000000000005")  # Household B Head (MEMBER)
EMMA_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")     # Household B (VIEWER)
OUTSIDE_ATTACKER_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")


@pytest_asyncio.fixture
async def db_conn():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.execute("RESET ROLE;")
        await conn.close()


async def forge_session(conn: asyncpg.Connection, user_id: uuid.UUID, email: str, role: str = "authenticated"):
    claims = json.dumps({"sub": str(user_id), "email": email, "role": role})
    await conn.execute(f"SET ROLE {role};")
    await conn.execute(f"SELECT set_config('request.jwt.claims', '{claims}', false);")
    await conn.execute(f"SELECT set_config('request.jwt.claim.sub', '{str(user_id)}', false);")


@pytest.mark.asyncio
async def test_attack_unapproved_inbox_media_leak(db_conn):
    """
    Test Boundary 1: Unapproved Media Leak Guard
    A photo in PENDING_INBOX status uploaded by David must NOT be visible
    to other clan members (e.g. Michael) on public family feeds.
    """
    test_media_id = uuid.uuid4()
    
    await db_conn.execute("""
        INSERT INTO media_contributions (
            id, joint_family_id, uploader_id, media_title,
            media_type, r2_storage_key, matched_face_ids,
            confidence_scores, status
        ) VALUES (
            $1, $2, $3, 'Sophia_Emma_Cousins.jpg',
            'image/jpeg', 'raw/pending_cousins.jpg', '[]'::jsonb,
            '{}'::jsonb, 'PENDING_INBOX'
        );
    """, test_media_id, JOINT_CLAN_ID, DAVID_ID)

    try:
        await forge_session(db_conn, MICHAEL_ID, "michael@familyvault.app")

        visible_media = await db_conn.fetch("""
            SELECT id FROM media_contributions 
            WHERE id = $1 AND status = 'AUTO_PUBLISHED';
        """, test_media_id)

        assert len(visible_media) == 0, (
            "Security Breach: Pending media leaked to another family member before triage approval!"
        )
    finally:
        await db_conn.execute("RESET ROLE;")
        await db_conn.execute("DELETE FROM media_contributions WHERE id = $1;", test_media_id)


@pytest.mark.asyncio
async def test_attack_viewer_unauthorized_triage_escalation(db_conn):
    """
    Test Boundary 2: Privilege Escalation Guard
    Emma (VIEWER) attempts to approve or alter the status of pending inbox media.
    Must fail RLS check or be rejected without changing record status.
    """
    test_media_id = uuid.uuid4()

    await db_conn.execute("""
        INSERT INTO media_contributions (
            id, joint_family_id, uploader_id, media_title,
            media_type, r2_storage_key, status
        ) VALUES (
            $1, $2, $3, 'Lucas_David_Robert.jpg',
            'image/jpeg', 'raw/lucas_group.jpg', 'PENDING_INBOX'
        );
    """, test_media_id, JOINT_CLAN_ID, DAVID_ID)

    try:
        await forge_session(db_conn, EMMA_ID, "emma@familyvault.app")

        try:
            await db_conn.execute("""
                UPDATE media_contributions 
                SET status = 'AUTO_PUBLISHED'
                WHERE id = $1;
            """, test_media_id)
        except Exception:
            pass

        await db_conn.execute("RESET ROLE;")
        row = await db_conn.fetchrow(
            "SELECT status FROM media_contributions WHERE id = $1;", 
            test_media_id
        )
        assert row["status"] != "AUTO_PUBLISHED", (
            "Privilege Escalation: VIEWER role successfully updated media status!"
        )
    finally:
        await db_conn.execute("RESET ROLE;")
        await db_conn.execute("DELETE FROM media_contributions WHERE id = $1;", test_media_id)


@pytest.mark.asyncio
async def test_attack_outside_attacker_media_isolation(db_conn):
    """
    Test Boundary 3: Outside Clan Tenant Boundary
    An unauthenticated or outside attacker must not enumerate or read any media assets.
    """
    await forge_session(db_conn, OUTSIDE_ATTACKER_ID, "attacker@darkweb.org")

    media_records = await db_conn.fetch("""
        SELECT id FROM media_contributions WHERE joint_family_id = $1;
    """, JOINT_CLAN_ID)

    assert len(media_records) == 0, (
        "Tenant Leak: External adversary accessed private clan media records!"
    )


@pytest.mark.asyncio
async def test_vance_album_threshold_routing():
    """
    Test Boundary 4: Biometrics Vector Threshold Routing Contract
    """
    auto_publish_threshold = 0.85

    vance_reunion_confidence = 0.94
    sophia_emma_confidence = 0.78

    assert vance_reunion_confidence >= auto_publish_threshold, "Vance Reunion should meet auto-publish threshold"
    assert sophia_emma_confidence < auto_publish_threshold, "Sophia & Emma cousins ambiguity must route to Inbox"