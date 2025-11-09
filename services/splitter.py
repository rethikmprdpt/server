from sqlalchemy.orm import Session  # noqa: INP001

from db.models import AuditLogActionType, Port, User
from services.audit import create_audit_log


def get_ports_for_splitter(
    db: Session,
    splitter_id: int,
    current_user: User,  # <-- 1. Accept the user
) -> list[Port]:
    # 1. Fetch the data
    ports = db.query(Port).filter(Port.splitter_id == splitter_id).all()

    # 2. Create the audit log
    # This is a separate transaction, which is fine for a READ
    try:
        create_audit_log(
            db=db,
            user=current_user,
            action_type=AuditLogActionType.READ,
            description=f"User '{current_user.username}' viewed all {len(ports)} ports for splitter ID {splitter_id}.",
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        # Log the error but don't fail the main request
        print(f"Failed to create audit log for get_ports_for_splitter: {e}")

    # 3. Return the data
    return ports
