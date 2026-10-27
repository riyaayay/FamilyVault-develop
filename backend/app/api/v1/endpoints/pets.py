from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser
from app.models.household import Pet
from app.schemas.household import PetCreate, PetUpdate, PetResponse
from app.schemas.common import APIResponse

router = APIRouter()


@router.get("/", response_model=APIResponse[List[PetResponse]])
async def list_pets(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[PetResponse]]:
    """List pets belonging strictly to the current user's nuclear household."""
    if not current_user.nuclear_family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have an active nuclear household assigned",
        )

    stmt = select(Pet).where(Pet.nuclear_family_id == current_user.nuclear_family_id)
    res = await db.execute(stmt)
    pets = res.scalars().all()

    items = [PetResponse.model_validate(p) for p in pets]
    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} pets for household",
        data=items,
    )


@router.post("/", response_model=APIResponse[PetResponse], status_code=status.HTTP_201_CREATED)
async def create_pet(
    pet_in: PetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[PetResponse]:
    """Register a new pet under the user's nuclear household."""
    if current_user.role not in ("ADMIN", "MEMBER", "SERVICE_ROLE"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{current_user.role}' is not authorized to register pets",
        )
    if not current_user.nuclear_family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have an active nuclear household assigned",
        )
    nuclear_family_id = current_user.nuclear_family_id

    new_pet = Pet(
        nuclear_family_id=nuclear_family_id,
        name=pet_in.name,
        pet_type=pet_in.pet_type,
        breed=pet_in.breed,
        date_of_birth=pet_in.date_of_birth,
        microchip_number=pet_in.microchip_number,
        vaccination_schedule=pet_in.vaccination_schedule,
    )

    db.add(new_pet)
    await db.flush()
    await db.refresh(new_pet)

    return APIResponse(
        success=True,
        message=f"Pet '{new_pet.name}' registered successfully",
        data=PetResponse.model_validate(new_pet),
    )


@router.get("/{pet_id}", response_model=APIResponse[PetResponse])
async def get_pet(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[PetResponse]:
    """Retrieve details for a specific pet within the user's household."""
    stmt = select(Pet).where(Pet.id == pet_id)
    # A user without a household matches no pets (never every household's pets).
    stmt = stmt.where(Pet.nuclear_family_id == current_user.nuclear_family_id)

    res = await db.execute(stmt)
    pet = res.scalars().first()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pet with ID '{pet_id}' not found in household",
        )

    return APIResponse(
        success=True,
        message=f"Pet '{pet.name}' retrieved successfully",
        data=PetResponse.model_validate(pet),
    )


@router.put("/{pet_id}", response_model=APIResponse[PetResponse])
async def update_pet(
    pet_id: UUID,
    pet_in: PetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[PetResponse]:
    """Update pet details (vaccination log, breed, microchip)."""
    stmt = select(Pet).where(Pet.id == pet_id)
    # A user without a household matches no pets (never every household's pets).
    stmt = stmt.where(Pet.nuclear_family_id == current_user.nuclear_family_id)

    res = await db.execute(stmt)
    pet = res.scalars().first()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pet with ID '{pet_id}' not found in household",
        )

    update_data = pet_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pet, field, value)

    await db.flush()
    await db.refresh(pet)

    return APIResponse(
        success=True,
        message=f"Pet '{pet.name}' updated successfully",
        data=PetResponse.model_validate(pet),
    )


@router.delete("/{pet_id}", response_model=APIResponse[dict])
async def delete_pet(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Delete a pet record from household assets."""
    stmt = select(Pet).where(Pet.id == pet_id)
    # A user without a household matches no pets (never every household's pets).
    stmt = stmt.where(Pet.nuclear_family_id == current_user.nuclear_family_id)

    res = await db.execute(stmt)
    pet = res.scalars().first()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pet with ID '{pet_id}' not found in household",
        )

    await db.delete(pet)
    await db.flush()

    return APIResponse(
        success=True,
        message=f"Pet '{pet.name}' removed successfully",
        data={"deleted_id": str(pet_id)},
    )
