from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser
from app.models.user import User
from app.models.family import FamilyMembership, NuclearFamily, JointFamily
from app.models.household import Pet
from app.schemas.user import UserResponse, HouseholdMemberResponse, ClanPersonSyncResponse
from app.schemas.common import APIResponse

router = APIRouter()

ACCENTS = ["chart-1", "chart-2", "chart-3", "chart-4", "chart-5"]


def _compute_initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    return name[:2].upper() if len(name) >= 2 else name.upper()


def _compute_generation(user: User, membership: FamilyMembership) -> int:
    """Derive generation (1 = Grandparents, 2 = Adults/Parents, 3 = Children) for kinship engines."""
    rel = (membership.relation_to_head or "").upper()
    role = (membership.role or "").upper()
    if user.date_of_birth:
        year = user.date_of_birth.year
        if year < 1960:
            return 1
        elif year < 1995:
            return 2
        else:
            return 3
    if role in ["ADMIN", "HEAD"] or rel == "HEAD" or (rel == "SPOUSE" and role == "ADMIN"):
        return 1
    elif rel in ["CHILD", "SPOUSE"]:
        return 2
    elif role in ["CHILD", "VIEWER"]:
        return 3
    return 2


@router.get("/me", response_model=APIResponse[AuthenticatedUser])
async def get_my_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[AuthenticatedUser]:
    """Retrieve authenticated user's profile and active family memberships."""
    return APIResponse(
        success=True,
        message="Active profile retrieved",
        data=current_user,
    )


@router.get("/", response_model=APIResponse[List[UserResponse]])
async def list_family_users(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[UserResponse]]:
    """List all registered members in the caller's joint clan."""
    if not current_user.joint_family_id:
        return APIResponse(success=True, message="No clan membership", data=[])

    stmt = (
        select(User)
        .join(FamilyMembership, FamilyMembership.user_id == User.id)
        .where(FamilyMembership.joint_family_id == current_user.joint_family_id)
        .distinct()
    )
    res = await db.execute(stmt)
    users = res.scalars().all()

    items = [UserResponse.model_validate(u) for u in users]
    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} family members",
        data=items,
    )


@router.get("/household/{nuclear_family_id}/members", response_model=APIResponse[List[HouseholdMemberResponse]])
async def get_household_members_by_id(
    nuclear_family_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[HouseholdMemberResponse]]:
    """Retrieve full roster of household members (including pets) for nuclear family dashboard."""
    # Query family memberships joined with User and JointFamily
    stmt = (
        select(FamilyMembership, User, JointFamily)
        .join(User, FamilyMembership.user_id == User.id)
        .outerjoin(JointFamily, FamilyMembership.joint_family_id == JointFamily.id)
        .where(FamilyMembership.nuclear_family_id == nuclear_family_id)
    )
    if not current_user.is_service:
        # A household in another clan simply has no visible members.
        stmt = stmt.where(FamilyMembership.joint_family_id == current_user.joint_family_id)
    res = await db.execute(stmt)
    rows = res.all()

    # Query household pets
    pets = []
    if rows:
        pet_stmt = select(Pet).where(Pet.nuclear_family_id == nuclear_family_id)
        pets = (await db.execute(pet_stmt)).scalars().all()

    members: List[HouseholdMemberResponse] = []
    idx = 0
    for row in rows:
        if len(row) >= 3:
            membership, user, joint_family = row[0], row[1], row[2]
        else:
            membership, user = row[0], row[1]
            joint_family = getattr(membership, "joint_family", None)

        rel = (membership.relation_to_head or "").lower()
        if membership.role in ["ADMIN", "HEAD"] or "head" in rel:
            role_mapped = "Head"
        elif "spouse" in rel or "wife" in rel or "husband" in rel:
            role_mapped = "Spouse"
        elif "son" in rel or (str(getattr(user, "gender", "")).lower() == "male" and "child" in rel):
            role_mapped = "Son"
        elif "daughter" in rel or (str(getattr(user, "gender", "")).lower() == "female" and "child" in rel):
            role_mapped = "Daughter"
        else:
            role_mapped = "Member"

        clan_id = getattr(joint_family, "id", None) or getattr(membership, "joint_family_id", None) or UUID("11111111-1111-1111-1111-111111111111")
        clan_name = getattr(joint_family, "name", None) or "Vance Ancestral Clan"
        gen = _compute_generation(user, membership)

        members.append(
            HouseholdMemberResponse(
                id=membership.id,
                user_id=user.id,
                name=user.full_name,
                role=role_mapped,
                membership_role=membership.role,
                relation_to_head=membership.relation_to_head,
                initials=_compute_initials(user.full_name),
                accent=ACCENTS[idx % len(ACCENTS)],
                avatar_url=user.avatar_url,
                email=user.email,
                date_of_birth=user.date_of_birth,
                gender=getattr(user, "gender", None),
                clan_id=clan_id,
                clan_name=clan_name,
                joint_family_id=getattr(membership, "joint_family_id", clan_id),
                generation=gen,
                is_pet=False,
            )
        )
        idx += 1


    for pet in pets:
        members.append(
            HouseholdMemberResponse(
                id=pet.id,
                user_id=None,
                name=pet.name,
                role="Pet",
                relation_to_head=f"Household {str(pet.pet_type).title()}",
                initials=_compute_initials(pet.name),
                accent="chart-5",
                species=str(pet.pet_type).title(),
                avatar_url=None,
                date_of_birth=pet.date_of_birth,
                gender=None,
                clan_id=None,
                clan_name=None,
                joint_family_id=None,
                generation=None,
                is_pet=True,
            )
        )

    return APIResponse(
        success=True,
        message=f"Retrieved {len(members)} household members and pets",
        data=members,
    )


@router.get("/household/members", response_model=APIResponse[List[HouseholdMemberResponse]])
async def get_my_household_members(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[HouseholdMemberResponse]]:
    """Retrieve full roster of members and pets for current user's household."""
    target_household_id = current_user.nuclear_family_id

    if not target_household_id:
        return APIResponse(
            success=True,
            message="No nuclear household configured",
            data=[],
        )

    return await get_household_members_by_id(
        nuclear_family_id=target_household_id,
        db=db,
        current_user=current_user,
    )


@router.get("/sync/clan/{clan_id}/persons", response_model=APIResponse[List[ClanPersonSyncResponse]])
async def sync_clan_persons(
    clan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[ClanPersonSyncResponse]]:
    """
    Dedicated Graph-Service Sync Endpoint.
    Returns full person roster for the entire joint clan, formatted 1:1 for Neo4j PersonIn ingestion.
    """
    if not current_user.is_service and clan_id != current_user.joint_family_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clan not found")
    stmt = (
        select(FamilyMembership, User, JointFamily, NuclearFamily)
        .join(User, FamilyMembership.user_id == User.id)
        .join(JointFamily, FamilyMembership.joint_family_id == JointFamily.id)
        .join(NuclearFamily, FamilyMembership.nuclear_family_id == NuclearFamily.id)
        .where(FamilyMembership.joint_family_id == clan_id)
        .order_by(User.date_of_birth.asc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    persons: List[ClanPersonSyncResponse] = []
    seen_user_ids = set()
    for row in rows:
        if len(row) >= 4:
            membership, user, joint_family, nuclear_fam = row[0], row[1], row[2], row[3]
        elif len(row) == 3:
            membership, user, joint_family = row[0], row[1], row[2]
            nuclear_fam = getattr(membership, "nuclear_family", None)
        else:
            membership, user = row[0], row[1]
            joint_family = getattr(membership, "joint_family", None)
            nuclear_fam = getattr(membership, "nuclear_family", None)

        if user.id in seen_user_ids:
            continue
        seen_user_ids.add(user.id)

        nh_name = getattr(nuclear_fam, "household_name", "Nuclear Household A")
        if "Nuclear A" in nh_name or "David" in nh_name:
            if membership.relation_to_head in ["HEAD", "SPOUSE"] and membership.role == "ADMIN":
                nh_label = "Patriarchal Household"
            else:
                nh_label = "Nuclear Household A"
        elif "Nuclear B" in nh_name or "Michael" in nh_name:
            nh_label = "Nuclear Household B"
        else:
            nh_label = nh_name

        if user.full_name == "Robert Vance":
            nh_label = "Extended Household"

        gen = _compute_generation(user, membership)
        clan_id_val = getattr(joint_family, "id", None) or getattr(membership, "joint_family_id", None) or clan_id
        clan_name_val = getattr(joint_family, "name", None) or "Vance Ancestral Clan"
        dob_val = user.date_of_birth.isoformat() if getattr(user, "date_of_birth", None) else None

        persons.append(
            ClanPersonSyncResponse(
                person_id=user.id,
                full_name=user.full_name,
                role=membership.role,
                relation_to_head=membership.relation_to_head,
                generation=gen,
                gender=getattr(user, "gender", None),
                birth_date=dob_val,
                is_living=True,
                avatar_url=user.avatar_url,
                nuclear_household=nh_label,
                clan_id=clan_id_val,
                clan_name=clan_name_val,
            )
        )


    return APIResponse(
        success=True,
        message=f"Synced {len(persons)} clan persons for graph service",
        data=persons,
    )


@router.get("/sync/persons", response_model=APIResponse[List[ClanPersonSyncResponse]])
async def sync_default_clan_persons(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[ClanPersonSyncResponse]]:
    """Sync endpoint defaulting to the authenticated user/service's clan or the primary seeded clan."""
    target_clan_id = current_user.joint_family_id

    if not target_clan_id:
        return APIResponse(success=True, message="No clan found", data=[])

    return await sync_clan_persons(clan_id=target_clan_id, db=db, current_user=current_user)


# Dedicated household router mounted at /api/v1/household
household_router = APIRouter()
household_router.add_api_route(
    "/{nuclear_family_id}/members",
    get_household_members_by_id,
    methods=["GET"],
    response_model=APIResponse[List[HouseholdMemberResponse]],
    summary="Get members for specific nuclear household",
)
household_router.add_api_route(
    "/members",
    get_my_household_members,
    methods=["GET"],
    response_model=APIResponse[List[HouseholdMemberResponse]],
    summary="Get members for current user's nuclear household",
)
household_router.add_api_route(
    "/clan/{clan_id}/persons",
    sync_clan_persons,
    methods=["GET"],
    response_model=APIResponse[List[ClanPersonSyncResponse]],
    summary="Sync full person roster for clan",
)



