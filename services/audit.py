from sqlalchemy.orm import Session  # noqa: INP001

from db.models import AuditLog, User


def create_audit_log(db: Session, user: User, action_type: str, description: str):
    new_log = AuditLog(
        user_id=user.user_id,
        action_type=action_type,
        description=description,
        # The 'timestamp' is set by the database model's default
    )
    db.add(new_log)
