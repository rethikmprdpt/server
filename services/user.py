# noqa: INP001
from sqlalchemy.orm import Session

from db.models import AuditLogActionType, User, UserRole
from schemas.user import UserRole as SchemaUserRole
from services.audit import create_audit_log


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
            action_type=str(AuditLogActionType.READ),
            description=f"User '{current_user.username}' fetched the complete user list.",
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        # We don't want to fail the whole request if logging fails
        print(f"Failed to create audit log for get_all_users: {e}")

    # 3. Return the data
    return users
