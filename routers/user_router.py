from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User
from routers.auth_router import get_current_user
from schemas.user import UserCreate, UserRead, UserRole, UserRoleUpdate
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


# --- 2. NEW ENDPOINT: Create User ---


@user_router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
def create_new_user(
    user_data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # --- Role-Based Security Check ---
    if current_user.role != UserRole.Admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create new users.",
        )

    try:
        new_user = user_service.create_user(
            db=db,
            user_data=user_data,
            current_user=current_user,
        )
    except HTTPException as e:
        raise e  # noqa: TRY201
    except Exception as e:  # noqa: BLE001
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    else:
        return new_user


# --- 3. NEW ENDPOINT: Update User Role ---


@user_router.patch(
    "/{user_id}/role",
    response_model=UserRead,
    summary="Update a user's role",
)
def update_user_role_endpoint(
    user_id: int,
    role_data: UserRoleUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # --- Role-Based Security Check ---
    if current_user.role != UserRole.Admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to change user roles.",
        )

    try:
        updated_user = user_service.update_user_role(
            db=db,
            user_id_to_update=user_id,
            role_data=role_data,
            current_user=current_user,
        )
    except HTTPException as e:
        raise e  # noqa: TRY201
    except Exception as e:  # noqa: BLE001
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    else:
        return updated_user
