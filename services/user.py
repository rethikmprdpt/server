# noqa: INP001
from sqlalchemy.orm import Session

from db.models import User, UserRole
from schemas.user import UserRole as SchemaUserRole


def get_users_by_role(db: Session, role: SchemaUserRole) -> list[User]:
    # Convert Pydantic/FastAPI enum to SQLAlchemy model enum
    model_role_enum = UserRole[role.value]

    return db.query(User).filter(User.role == model_role_enum).all()
