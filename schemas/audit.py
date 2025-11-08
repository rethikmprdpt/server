from datetime import datetime

from pydantic import BaseModel, ConfigDict

from db.models import AuditLogActionType

# We'll import your UserRead schema to nest it
from .user import UserRead


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    log_id: int
    action_type: AuditLogActionType
    description: str | None
    timestamp: datetime

    # Nested user data
    user: UserRead | None  # Use | None in case user is deleted
