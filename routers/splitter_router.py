from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

# Import all necessary components
from db.database import get_db
from db.models import User, UserRole
from routers.auth_router import get_current_user
from schemas.asset import PortRead  # <-- Use the correct Port schema
from services import splitter as splitter_service

splitter_router = APIRouter(prefix="/splitters", tags=["Splitters"])


@splitter_router.get(
    "/{splitter_id}/ports",
    response_model=list[PortRead],
    summary="Get all ports for a splitter",
)
def get_ports_for_splitter_endpoint(
    splitter_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # --- Role-Based Security Check ---
    if current_user.role not in [UserRole.Admin, UserRole.Planner]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this information.",
        )

    ports = splitter_service.get_ports_for_splitter(
        db=db,
        splitter_id=splitter_id,
        current_user=current_user,  # <-- 2. Pass the user to the service
    )
    return ports
