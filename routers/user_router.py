from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User
from routers.auth_router import get_current_user
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


@user_router.get("/all", response_model=list[UserRead], summary="Get all users")
def get_all_users_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # --- Role-Based Security Check ---
    if current_user.role not in [UserRole.Admin, UserRole.Planner]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )

    users = user_service.get_all_users(db=db, current_user=current_user)
    return users
