from datetime import datetime, timedelta, timezone  # noqa: INP001

from sqlalchemy.orm import Session, joinedload

from db.models import AuditLog, User


def create_audit_log(db: Session, user: User, action_type: str, description: str):
    new_log = AuditLog(
        user_id=user.user_id,
        action_type=action_type,
        description=description,
        # The 'timestamp' is set by the database model's default
    )
    db.add(new_log)


def get_audit_logs(
    db: Session,
    user_id: int | None = None,
    days_ago: int | None = None,
) -> list[AuditLog]:
    # Start the base query and join the 'user' relationship
    # This is crucial for performance.
    query = db.query(AuditLog).options(joinedload(AuditLog.user))

    # 1. Filter by User ID (if provided)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    # 2. Filter by Date Range (if provided)
    if days_ago:
        # Calculate the cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
        query = query.filter(AuditLog.timestamp >= cutoff_date)

    # 3. Order by newest first
    query = query.order_by(AuditLog.timestamp.desc())

    # Execute and return all matching logs
    return query.all()
