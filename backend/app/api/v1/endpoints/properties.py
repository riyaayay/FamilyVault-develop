from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser
from app.models.household import Property
from app.schemas.household import PropertyCreate, PropertyUpdate, PropertyResponse
from app.schemas.common import APIResponse

router = APIRouter()


@router.get("/", response_model=APIResponse[List[PropertyResponse]])
async def list_properties(
    household_id: Optional[UUID] = Query(None, description="Filter by nuclear household"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[PropertyResponse]]:
    """List properties belonging to the user's joint clan (optional household filter)."""
    joint_family_id = current_user.joint_family_id or UUID("11111111-1111-1111-1111-111111111111")
    stmt = select(Property).where(Property.joint_family_id == joint_family_id)

    if household_id:
        stmt = stmt.where(Property.nuclear_family_id == household_id)

    res = await db.execute(stmt)
    props = res.scalars().all()

    items = [PropertyResponse.model_validate(p) for p in props]
    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} clan properties",
        data=items,
    )


@router.post("/", response_model=APIResponse[PropertyResponse], status_code=status.HTTP_201_CREATED)
async def create_property(
    prop_in: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[PropertyResponse]:
    """Register a new ancestral or household real estate asset."""
    if current_user.role not in ("ADMIN", "MEMBER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{current_user.role}' is not authorized to register property records",
        )

    joint_family_id = current_user.joint_family_id or UUID("11111111-1111-1111-1111-111111111111")
    nuclear_family_id = prop_in.nuclear_family_id or current_user.nuclear_family_id

    new_prop = Property(
        joint_family_id=joint_family_id,
        nuclear_family_id=nuclear_family_id,
        title=prop_in.title,
        property_type=prop_in.property_type,
        survey_number=prop_in.survey_number,
        address=prop_in.address,
        estimated_valuation=prop_in.estimated_valuation,
        ownership_breakdown=prop_in.ownership_breakdown,
        deed_document_id=prop_in.deed_document_id,
    )

    db.add(new_prop)
    await db.flush()
    await db.refresh(new_prop)

    return APIResponse(
        success=True,
        message=f"Property '{new_prop.title}' registered successfully",
        data=PropertyResponse.model_validate(new_prop),
    )


@router.get("/{prop_id}", response_model=APIResponse[PropertyResponse])
async def get_property(
    prop_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[PropertyResponse]:
    """Retrieve details for a specific clan real estate asset."""
    joint_family_id = current_user.joint_family_id or UUID("11111111-1111-1111-1111-111111111111")
    stmt = select(Property).where(Property.id == prop_id, Property.joint_family_id == joint_family_id)

    res = await db.execute(stmt)
    prop = res.scalars().first()

    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property with ID '{prop_id}' not found in clan assets",
        )

    return APIResponse(
        success=True,
        message=f"Property '{prop.title}' retrieved successfully",
        data=PropertyResponse.model_validate(prop),
    )


@router.put("/{prop_id}", response_model=APIResponse[PropertyResponse])
async def update_property(
    prop_id: UUID,
    prop_in: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[PropertyResponse]:
    """Update property details, valuation, or ownership breakdown."""
    if current_user.role not in ("ADMIN", "MEMBER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{current_user.role}' is not authorized to update property records",
        )

    joint_family_id = current_user.joint_family_id or UUID("11111111-1111-1111-1111-111111111111")
    stmt = select(Property).where(Property.id == prop_id, Property.joint_family_id == joint_family_id)

    res = await db.execute(stmt)
    prop = res.scalars().first()

    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property with ID '{prop_id}' not found in clan assets",
        )

    update_data = prop_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prop, field, value)

    await db.flush()
    await db.refresh(prop)

    return APIResponse(
        success=True,
        message=f"Property '{prop.title}' updated successfully",
        data=PropertyResponse.model_validate(prop),
    )


@router.delete("/{prop_id}", response_model=APIResponse[dict])
async def delete_property(
    prop_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Delete a property record from clan assets."""
    if current_user.role not in ("ADMIN", "MEMBER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{current_user.role}' is not authorized to delete property records",
        )

    joint_family_id = current_user.joint_family_id or UUID("11111111-1111-1111-1111-111111111111")
    stmt = select(Property).where(Property.id == prop_id, Property.joint_family_id == joint_family_id)

    res = await db.execute(stmt)
    prop = res.scalars().first()

    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property with ID '{prop_id}' not found in clan assets",
        )

    await db.delete(prop)
    await db.flush()

    return APIResponse(
        success=True,
        message=f"Property '{prop.title}' removed successfully",
        data={"deleted_id": str(prop_id)},
    )
