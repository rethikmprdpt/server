import enum
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

# Import related schemas
from .customer import CustomerRead
from .user import UserRead


# Enum from your models (import or redefine)
class DeploymentTaskStatus(str, enum.Enum):
    Scheduled = "Scheduled"
    InProgress = "InProgress"
    Completed = "Completed"
    Failed = "Failed"


# --- Base Schema ---
# Common fields
class DeploymentTaskBase(BaseModel):
    scheduled_date: date  # <-- CHANGE: from datetime to date
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Create Schema ---
# Used for the 'assign technician' POST request
class DeploymentTaskCreate(DeploymentTaskBase):
    customer_id: int  # ID of the customer
    user_id: int  # ID of the technician to assign


# --- Read Schema ---
class DeploymentTaskRead(DeploymentTaskBase):
    task_id: int
    status: DeploymentTaskStatus
    created_at: datetime
    updated_at: datetime

    # --- OVERRIDE: Ensure output is datetime ---
    scheduled_date: datetime

    # --- ADD THESE NEW FIELDS ---
    step_1: bool
    step_2: bool
    step_3: bool
    # --- END OF NEW FIELDS ---

    # Nest the full customer and user objects
    customer: CustomerRead
    user: UserRead  # The assigned technician


# --- ADD THIS NEW SCHEMA ---
# This is the schema for the PATCH request
# when a technician updates the checklist.
class DeploymentTaskChecklistUpdate(BaseModel):
    step_1: bool
    step_2: bool
    step_3: bool
