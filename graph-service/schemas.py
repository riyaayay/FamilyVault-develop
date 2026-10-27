from typing import Optional
from pydantic import BaseModel, Field


class PersonIn(BaseModel):
    """Body for POST /api/graph/person. Every field except person_id and
    full_name is optional with a sensible default, so partially-seeded
    or legacy test data still produces a complete, contract-shaped
    'data' object on read."""

    person_id: str = Field(..., description="Same UUID as users.id in Postgres.")
    full_name: str

    role: str = "MEMBER"                  # e.g. ADMIN | MEMBER | VIEWER | CHILD
    relation_to_head: str = "EXTENDED"    # e.g. HEAD | SPOUSE | CHILD | EXTENDED
    generation: int = 1
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    is_living: bool = True
    avatar_url: Optional[str] = None
    nuclear_household: Optional[str] = None
    gotra: Optional[str] = None  # patrilineal clan lineage -- Sprint 3

    # Every person in the same joint family should be seeded with the
    # same clan_id/clan_name -- the tree endpoint reads these off
    # whichever nodes have them set.
    clan_id: Optional[str] = None
    clan_name: Optional[str] = None

    # Optional explicit React Flow canvas position. Leave both unset to
    # let the tree endpoint auto-layout by generation/sibling order.
    position_x: Optional[float] = None
    position_y: Optional[float] = None