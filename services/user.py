# noqa: INP001
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models import AuditLogActionType, User, UserRole
from schemas.user import UserCreate, UserRoleUpdate
from schemas.user import UserRole as SchemaUserRole
from services.audit import create_audit_log
from utils.auth import get_password_hash


def get_users_by_role(db: Session, role: SchemaUserRole) -> list[User]:
    # Convert Pydantic/FastAPI enum to SQLAlchemy model enum
    model_role_enum = UserRole[role.value]

    return db.query(User).filter(User.role == model_role_enum).all()


def get_all_users(db: Session, current_user: User) -> list[User]:
    users = db.query(User).order_by(User.username).all()

    try:
        create_audit_log(
            db=db,
            user=current_user,
            action_type=AuditLogActionType.READ,
            description=f"User '{current_user.username}' fetched the complete user list.",
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        # We don't want to fail the whole request if logging fails
        print(f"Failed to create audit log for get_all_users: {e}")

    # 3. Return the data
    return users


# --- 2. NEW FUNCTION: Create User ---


def create_user(db: Session, user_data: UserCreate, current_user: User) -> User:
    # 1. Check if user already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user_data.username}' already exists.",
        )

    try:
        # 2. Hash the password
        hashed_password = get_password_hash(user_data.password)

        # 3. Create new user model
        new_user = User(
            username=user_data.username,
            password_hash=hashed_password,
            role=SchemaUserRole[user_data.role.value],  # Convert from Pydantic enum
        )

        db.add(new_user)
        db.flush()  # Flush to get the new_user.user_id

        # 4. Create the audit log
        create_audit_log(
            db=db,
            user=current_user,
            action_type=AuditLogActionType.CREATE,
            description=f"Admin '{current_user.username}' created new user '{new_user.username}' (ID: {new_user.user_id}) with role '{new_user.role.value}'.",
        )

        # 5. Commit transaction (saves user and log)
        db.commit()
        db.refresh(new_user)

    except Exception as e:  # noqa: BLE001
        db.rollback()
        print(f"Error during user creation: {e}")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}",
        )
    else:
        return new_user


# --- 3. NEW FUNCTION: Update User Role ---


def update_user_role(
    db: Session,
    user_id_to_update: int,
    role_data: UserRoleUpdate,
    current_user: User,
) -> User:
    # 1. Find the user to update
    user_to_update = db.get(User, user_id_to_update)
    if not user_to_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id_to_update} not found.",
        )

    # 2. CRITICAL: Add safety check
    if user_to_update.user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot change their own role. This must be done by another Admin.",
        )

    try:
        # 3. Apply the update
        old_role = user_to_update.role.value
        new_role_enum = SchemaUserRole[role_data.role.value]

        # Only update if the role is actually different
        if user_to_update.role == new_role_enum:
            return user_to_update  # Nothing to do

        user_to_update.role = new_role_enum

        # 4. Create the audit log
        create_audit_log(
            db=db,
            user=current_user,
            action_type=AuditLogActionType.UPDATE,
            description=f"Admin '{current_user.username}' changed role for user '{user_to_update.username}' (ID: {user_to_update.user_id}) from '{old_role}' to '{new_role_enum.value}'.",
        )

        # 5. Commit transaction
        db.commit()
        db.refresh(user_to_update)

    except Exception as e:  # noqa: BLE001
        db.rollback()
        print(f"Error during role update: {e}")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}",
        )
    else:
        return user_to_update
