from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.user import UserRead, UserRole
from services import user as user_service

user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.get("/", response_model=list[UserRead], summary="Get users by role")
def get_users_by_role_endpoint(
    db: Annotated[Session, Depends(get_db)],
    role: Annotated[
        UserRole,
        Query(
            ...,  # Make the parameter required
            description="Filter users by their role (e.g., Technician)",
        ),
    ],
):
    try:
        users = user_service.get_users_by_role(db=db, role=role)
    except Exception as e:  # noqa: BLE001
        # Handle cases where enum conversion might fail, though FastAPI usually catches this
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch users: {e!s}",
        )
    else:
        return users
