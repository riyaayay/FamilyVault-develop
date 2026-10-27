"""
FamilyVault — 3-Generation Narrative Seed Script
Owner: Runeet (Lead / Backend & Database Architect)

Populates the single-source-of-truth 3-generation Vance family narrative
with deterministic UUIDs matching Neo4j AuraDB (contracts/graph-tree-response.json)
and testing-matrix.md personas.

Usage:
    cd backend
    python scripts/seed.py
"""

import sys
import os
from pathlib import Path

# Windows consoles default to cp1252 and choke on the status glyphs printed below
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
from uuid import UUID
from datetime import date, datetime, timezone
from decimal import Decimal

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import asyncio
from sqlalchemy.future import select
from sqlalchemy import delete
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.family import JointFamily, NuclearFamily, FamilyMembership
from app.models.user import User
from app.models.health import HealthRecord
from app.models.household import Pet, Property
from app.models.document import Document
from app.models.media import MediaContribution
from app.models.household import AuditLog


# ==============================================================================
# DETERMINISTIC UUID CONSTANTS (100% Parity with Neo4j & testing-matrix.md)
# ==============================================================================

JOINT_FAMILY_ID = UUID("11111111-1111-1111-1111-111111111111")
NUCLEAR_A_ID = UUID("22222222-2222-2222-2222-222222222222")
NUCLEAR_B_ID = UUID("33333333-3333-3333-3333-333333333333")

PERSON_IDS = {
    "arthur": UUID("00000000-0000-0000-0000-000000000001"),
    "eleanor": UUID("00000000-0000-0000-0000-000000000002"),
    "david": UUID("00000000-0000-0000-0000-000000000003"),
    "sarah": UUID("00000000-0000-0000-0000-000000000004"),
    "michael": UUID("00000000-0000-0000-0000-000000000005"),
    "clara": UUID("00000000-0000-0000-0000-000000000006"),
    "robert": UUID("00000000-0000-0000-0000-000000000007"),
    "lucas": UUID("00000000-0000-0000-0000-000000000008"),
    "sophia": UUID("00000000-0000-0000-0000-000000000009"),
    "emma": UUID("00000000-0000-0000-0000-000000000010"),
}


async def seed():
    print("\n=======================================================")
    print("FamilyVault — Initializing 3-Generation Narrative Seed")
    print("=======================================================\n")

    async with AsyncSessionLocal() as session:
        # 1. Clean existing seed data (idempotent seed run)
        print("[1/7] Cleaning existing tenant data...")
        await session.execute(delete(AuditLog).where(AuditLog.joint_family_id == JOINT_FAMILY_ID))
        await session.execute(delete(MediaContribution).where(MediaContribution.joint_family_id == JOINT_FAMILY_ID))
        await session.execute(delete(FamilyMembership))
        await session.execute(delete(HealthRecord))
        await session.execute(delete(Pet))
        await session.execute(delete(Property))
        await session.execute(delete(Document))
        await session.execute(delete(User).where(User.id.in_(list(PERSON_IDS.values()))))
        await session.execute(delete(NuclearFamily).where(NuclearFamily.id.in_([NUCLEAR_A_ID, NUCLEAR_B_ID])))
        await session.execute(delete(JointFamily).where(JointFamily.id == JOINT_FAMILY_ID))
        await session.flush()

        # 2. Seed Joint Family & Nuclear Households
        print("[2/7] Seeding Clan & Nuclear Households...")
        joint_family = JointFamily(
            id=JOINT_FAMILY_ID,
            name="Vance Ancestral Clan",
            ancestral_origin="Varanasi / Old Delhi",
            motto="Knowledge, Legacy, and Resilience",
        )
        session.add(joint_family)
        await session.flush()

        nuclear_a = NuclearFamily(
            id=NUCLEAR_A_ID,
            joint_family_id=JOINT_FAMILY_ID,
            household_name="David & Sarah Household (Nuclear A)",
            current_city="South Delhi",
        )
        nuclear_b = NuclearFamily(
            id=NUCLEAR_B_ID,
            joint_family_id=JOINT_FAMILY_ID,
            household_name="Michael & Clara Household (Nuclear B)",
            current_city="Bengaluru",
        )
        session.add_all([nuclear_a, nuclear_b])
        await session.flush()

        # 3. Seed 10 Personas (3 Generations)
        print("[3/7] Seeding 10 Personas across 3 Generations...")
        users_data = [
            # Gen 1 (Grandparents)
            User(id=PERSON_IDS["arthur"], email="arthur@familyvault.app", phone_number="+91-98100-11001", full_name="Arthur Vance", preferred_name="Dadaji", date_of_birth=date(1948, 3, 15), gender="male"),
            User(id=PERSON_IDS["eleanor"], email="eleanor@familyvault.app", phone_number="+91-98100-11002", full_name="Eleanor Vance", preferred_name="Dadiji", date_of_birth=date(1952, 8, 22), gender="female"),
            # Gen 2 (Adults)
            User(id=PERSON_IDS["david"], email="david@familyvault.app", phone_number="+91-98100-11003", full_name="David Vance", preferred_name="David", date_of_birth=date(1975, 11, 10), gender="male"),
            User(id=PERSON_IDS["sarah"], email="sarah@familyvault.app", phone_number="+91-98100-11004", full_name="Sarah Vance", preferred_name="Sarah", date_of_birth=date(1978, 5, 18), gender="female"),
            User(id=PERSON_IDS["michael"], email="michael@familyvault.app", phone_number="+91-98450-22005", full_name="Michael Vance", preferred_name="Mike", date_of_birth=date(1980, 2, 14), gender="male"),
            User(id=PERSON_IDS["clara"], email="clara@familyvault.app", phone_number="+91-98450-22006", full_name="Clara Vance", preferred_name="Clara", date_of_birth=date(1982, 9, 30), gender="female"),
            User(id=PERSON_IDS["robert"], email="robert@familyvault.app", full_name="Robert Vance", preferred_name="Rob Chacha", date_of_birth=date(1985, 7, 4), gender="male"),
            # Gen 3 (Children)
            User(id=PERSON_IDS["lucas"], email="lucas@familyvault.app", full_name="Lucas Vance", preferred_name="Luke", date_of_birth=date(2005, 6, 12), gender="male"),
            User(id=PERSON_IDS["sophia"], email="sophia@familyvault.app", full_name="Sophia Vance", preferred_name="Soph", date_of_birth=date(2008, 11, 20), gender="female"),
            User(id=PERSON_IDS["emma"], email="emma@familyvault.app", full_name="Emma Vance", preferred_name="Emmy", date_of_birth=date(2012, 1, 8), gender="female"),
        ]
        session.add_all(users_data)
        await session.flush()

        # 4. Seed Family Memberships & Roles
        print("[4/7] Seeding Family Memberships & Multi-Tier Roles...")
        memberships_data = [
            FamilyMembership(user_id=PERSON_IDS["arthur"], joint_family_id=JOINT_FAMILY_ID, nuclear_family_id=NUCLEAR_A_ID, role="ADMIN", relation_to_head="HEAD", is_emergency_contact=True),
            FamilyMembership(user_id=PERSON_IDS["eleanor"], joint_family_id=JOINT_FAMILY_ID, nuclear_family_id=NUCLEAR_A_ID, role="ADMIN", relation_to_head="SPOUSE", is_emergency_contact=True),
            FamilyMembership(user_id=PERSON_IDS["david"], joint_family_id=JOINT_FAMILY_ID, nuclear_family_id=NUCLEAR_A_ID, role="MEMBER", relation_to_head="CHILD", is_emergency_contact=True),
            FamilyMembership(user_id=PERSON_IDS["sarah"], joint_family_id=JOINT_FAMILY_ID, nuclear_family_id=NUCLEAR_A_ID, role="MEMBER", relation_to_head="SPOUSE", is_emergency_contact=True),
            FamilyMembership(user_id=PERSON_IDS["michael"], joint_family_id=JOINT_FAMILY_ID, nuclear_family_id=NUCLEAR_B_ID, role="MEMBER", relation_to_head="CHILD", is_emergency_contact=True),
            FamilyMembership(user_id=PERSON_IDS["clara"], joint_family_id=JOINT_FAMILY_ID, nuclear_family_id=NUCLEAR_B_ID, role="MEMBER", relation_to_head="SPOUSE", is_emergency_contact=True),
            FamilyMembership(user_id=PERSON_IDS["robert"], joint_family_id=JOINT_FAMILY_ID, nuclear_family_id=NUCLEAR_A_ID, role="MEMBER", relation_to_head="CHILD", is_emergency_contact=False),
            FamilyMembership(user_id=PERSON_IDS["lucas"], joint_family_id=JOINT_FAMILY_ID, nuclear_family_id=NUCLEAR_A_ID, role="CHILD", relation_to_head="EXTENDED", is_emergency_contact=False),
            FamilyMembership(user_id=PERSON_IDS["sophia"], joint_family_id=JOINT_FAMILY_ID, nuclear_family_id=NUCLEAR_B_ID, role="CHILD", relation_to_head="EXTENDED", is_emergency_contact=False),
            FamilyMembership(user_id=PERSON_IDS["emma"], joint_family_id=JOINT_FAMILY_ID, nuclear_family_id=NUCLEAR_B_ID, role="VIEWER", relation_to_head="EXTENDED", is_emergency_contact=False),
        ]
        session.add_all(memberships_data)
        await session.flush()

        # 5. Seed Health Records (including Eleanor's Emergency Medical Profile)
        print("[5/7] Seeding Health Records & Emergency Medical Profiles...")
        health_records_data = [
            HealthRecord(
                user_id=PERSON_IDS["eleanor"],
                nuclear_family_id=NUCLEAR_A_ID,
                blood_group="O+",
                allergies=["Penicillin", "Sulfa drugs"],
                chronic_conditions=["Hypertension", "Arrhythmia"],
                current_medications=[
                    {"name": "Amlodipine", "dosage": "5mg", "frequency": "Once daily, morning"},
                    {"name": "Aspirin", "dosage": "75mg", "frequency": "Post dinner"},
                ],
                emergency_notes="Cardiac pacemaker installed Nov 2024. Primary physician Dr. A. Sen at AIIMS.",
                insurance_policy_number="HDFC-ERGO-CARDIO-882194",
                primary_physician_contact="+91-98110-22334 (Dr. Sen)",
                is_emergency_visible=True,
            ),
            HealthRecord(
                user_id=PERSON_IDS["arthur"],
                nuclear_family_id=NUCLEAR_A_ID,
                blood_group="B+",
                allergies=["Dust mites"],
                chronic_conditions=["Mild Arthritis"],
                current_medications=[{"name": "Glucosamine", "dosage": "500mg", "frequency": "Daily"}],
                emergency_notes="Requires walking stick assistance for prolonged travel.",
                insurance_policy_number="HDFC-ERGO-SR-77312",
                primary_physician_contact="+91-98110-22334 (Dr. Sen)",
                is_emergency_visible=True,
            ),
            HealthRecord(
                user_id=PERSON_IDS["lucas"],
                nuclear_family_id=NUCLEAR_A_ID,
                blood_group="O+",
                allergies=["Peanuts", "Shellfish"],
                chronic_conditions=[],
                current_medications=[],
                emergency_notes="EpiPen prescribed; carries in school backpack.",
                is_emergency_visible=True,
            ),
        ]
        session.add_all(health_records_data)
        await session.flush()

        # 6. Seed Household Assets (Pets & Properties)
        print("[6/7] Seeding Household Assets (Pets & Real Estate Properties)...")
        pet = Pet(
            nuclear_family_id=NUCLEAR_A_ID,
            name="Barnaby",
            pet_type="DOG",
            breed="Golden Retriever",
            date_of_birth=date(2021, 4, 10),
            microchip_number="985141002345678",
            vaccination_schedule=[
                {"vaccine": "Rabies Booster", "administered_on": "2024-03-12", "next_due": "2025-03-12"},
                {"vaccine": "DHPP 7-in-1", "administered_on": "2024-03-12", "next_due": "2025-03-12"},
            ],
        )
        session.add(pet)

        estate_prop = Property(
            joint_family_id=JOINT_FAMILY_ID,
            nuclear_family_id=NUCLEAR_A_ID,
            title="Vance Ancestral Haveli & Estate",
            property_type="Ancestral Land & Residence",
            survey_number="DL-KSP-1972-88B",
            address="Plot 14, Civil Lines Heritage Sector, Delhi 110054",
            estimated_valuation=Decimal("45000000.00"),
            ownership_breakdown=[
                {"user_id": str(PERSON_IDS["arthur"]), "share_percentage": 50},
                {"user_id": str(PERSON_IDS["david"]), "share_percentage": 25},
                {"user_id": str(PERSON_IDS["michael"]), "share_percentage": 25},
            ],
        )
        apt_prop = Property(
            joint_family_id=JOINT_FAMILY_ID,
            nuclear_family_id=NUCLEAR_B_ID,
            title="Whitefield High-Rise Residence",
            property_type="Apartment",
            survey_number="BLR-WTF-2018-04",
            address="Apt 1204, Prestige Ozone, Whitefield, Bengaluru 560066",
            estimated_valuation=Decimal("18000000.00"),
            ownership_breakdown=[
                {"user_id": str(PERSON_IDS["michael"]), "share_percentage": 50},
                {"user_id": str(PERSON_IDS["clara"]), "share_percentage": 50},
            ],
        )
        session.add_all([estate_prop, apt_prop])
        await session.flush()

        # 7. Seed Vault Documents (Three-Tier RLS + Time Capsule Lock)
        print("[7/7] Seeding Vault Documents & Milestone Locks...")
        docs_data = [
            Document(
                joint_family_id=JOINT_FAMILY_ID,
                uploader_id=PERSON_IDS["arthur"],
                title="1972 Ancestral Land Deed & Survey",
                description="Original registered title deed and cadastre map for Vance Heritage Estate.",
                category="PROPERTY",
                visibility_tier="JOINT_CLAN",
                r2_storage_key="vault/1972-ancestral-deed.pdf",
                file_size_bytes=4289100,
                mime_type="application/pdf",
                checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                capsule_status="ACTIVE",
            ),
            Document(
                joint_family_id=JOINT_FAMILY_ID,
                nuclear_family_id=NUCLEAR_A_ID,
                uploader_id=PERSON_IDS["david"],
                title="Household A Medical Insurance Policy 2026",
                description="HDFC ERGO Optima Secure family floater policy for David, Sarah, and Lucas.",
                category="FINANCIAL",
                visibility_tier="NUCLEAR_HOUSEHOLD",
                r2_storage_key="vault/household-a-insurance-2026.pdf",
                file_size_bytes=1845200,
                mime_type="application/pdf",
                checksum_sha256="8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
                capsule_status="ACTIVE",
            ),
            Document(
                joint_family_id=JOINT_FAMILY_ID,
                uploader_id=PERSON_IDS["arthur"],
                title="Arthur Vance Living Will & Succession Trust",
                description="Authoritative generational trust distribution, milestone locked until 2030 or 2 trustee signatures.",
                category="LEGACY_WILL",
                visibility_tier="PRIVATE_STRICT",
                r2_storage_key="vault/arthur-vance-living-will.pdf",
                file_size_bytes=5621000,
                mime_type="application/pdf",
                checksum_sha256="b5d4045c3f466fa91fe2cc6abe79232a1a57cdf104f7a26e716e0a1e2789df78",
                capsule_status="LOCKED",
                time_capsule_unlock_at=datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                trustee_approvals_required=2,
                trustee_approvals_received=[],
                # 2-of-3 quorum: David, Michael and Sarah are the named trustees
                designated_trustee_ids=[str(PERSON_IDS["david"]), str(PERSON_IDS["michael"]), str(PERSON_IDS["sarah"])],
                target_unlock_recipient_id=PERSON_IDS["david"],
            ),
            Document(
                joint_family_id=JOINT_FAMILY_ID,
                nuclear_family_id=NUCLEAR_B_ID,
                uploader_id=PERSON_IDS["clara"],
                title="Letter for Sophia's 21st Birthday",
                description="A time capsule from Mum, sealed until Sophia turns 21.",
                category="MEMORABILIA",
                visibility_tier="PRIVATE_STRICT",
                r2_storage_key="vault/sophia-21st-letter.pdf",
                file_size_bytes=182000,
                mime_type="application/pdf",
                capsule_status="LOCKED",
                time_capsule_unlock_at=datetime(2029, 11, 20, 0, 0, 0, tzinfo=timezone.utc),
                target_unlock_recipient_id=PERSON_IDS["sophia"],
            ),
        ]
        session.add_all(docs_data)
        await session.flush()

        # Media: published memories for the Lore timeline plus items awaiting
        # review. "demo/" keys are served from the frontend's public/ folder.
        published_at = datetime(2026, 8, 15, tzinfo=timezone.utc)
        media_data = [
            MediaContribution(
                joint_family_id=JOINT_FAMILY_ID, uploader_id=PERSON_IDS["david"],
                media_title="Diwali at the Haveli", media_type="image/jpeg",
                r2_storage_key="demo/intro/03.jpg", status="AUTO_PUBLISHED",
                matched_face_ids=[str(PERSON_IDS["arthur"])], confidence_scores={str(PERSON_IDS["arthur"]): 0.93},
                approval_timestamp=published_at, created_at=datetime(2025, 10, 20, tzinfo=timezone.utc),
            ),
            MediaContribution(
                joint_family_id=JOINT_FAMILY_ID, uploader_id=PERSON_IDS["eleanor"],
                media_title="Dadi's recipe: kadhi chawal (voice note)", media_type="audio/mpeg",
                r2_storage_key="", status="AUTO_PUBLISHED",  # metadata-only demo memory: no audio file shipped
                approved_by=PERSON_IDS["arthur"], approval_timestamp=published_at,
                created_at=datetime(2026, 1, 14, tzinfo=timezone.utc),
            ),
            MediaContribution(
                joint_family_id=JOINT_FAMILY_ID, uploader_id=PERSON_IDS["michael"],
                media_title="Sophia's school annual day", media_type="image/jpeg",
                r2_storage_key="demo/intro/08.jpg", status="AUTO_PUBLISHED",
                matched_face_ids=[str(PERSON_IDS["sophia"])], confidence_scores={str(PERSON_IDS["sophia"]): 0.9},
                approval_timestamp=published_at, created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
            ),
            MediaContribution(
                joint_family_id=JOINT_FAMILY_ID, uploader_id=PERSON_IDS["david"],
                media_title="Cousins reunion", media_type="image/jpeg",
                r2_storage_key="demo/group1.jpg", status="PENDING_INBOX",
                matched_face_ids=[str(PERSON_IDS["david"]), str(PERSON_IDS["robert"])],
                confidence_scores={str(PERSON_IDS["david"]): 0.92, str(PERSON_IDS["robert"]): 0.78},
                created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
            ),
            MediaContribution(
                joint_family_id=JOINT_FAMILY_ID, uploader_id=PERSON_IDS["robert"],
                media_title="Old Delhi walk (audio)", media_type="audio/mpeg",
                r2_storage_key="", status="PENDING_INBOX",  # metadata-only demo memory: no audio file shipped
                created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
            ),
            MediaContribution(
                joint_family_id=JOINT_FAMILY_ID, uploader_id=PERSON_IDS["sarah"],
                media_title="Blurry rooftop selfie", media_type="image/jpeg",
                r2_storage_key="demo/group2.jpg", status="REJECTED",
                approved_by=PERSON_IDS["david"], approval_timestamp=published_at,
                rejection_reason="Duplicate of an existing photo",
                created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            ),
        ]
        session.add_all(media_data)
        await session.commit()

        print("\n=======================================================")
        print("✓ [Success] 3-Generation Vance Narrative Seed Complete!")
        print(f"  • Joint Clan ID: {JOINT_FAMILY_ID}")
        print(f"  • Nuclear A ID:  {NUCLEAR_A_ID} (David & Sarah)")
        print(f"  • Nuclear B ID:  {NUCLEAR_B_ID} (Michael & Clara)")
        print(f"  • 10 Personas Seeded (Arthur Vance ...0001 -> Emma Vance ...0010)")
        print(f"  • Pets, Properties, Health & Locked Time Capsules Ready")
        print(f"  • Will trustees: David, Michael, Sarah (2-of-3); 6 media items (3 published, 2 inbox, 1 rejected)")
        print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(seed())
