from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from db.models import UserRole


class UserBase(BaseModel):
    username: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class UserRead(UserBase):
    user_id: int
    last_login: datetime | None = None


class UserCreate(UserBase):
    password: str = Field(
        ...,
        min_length=8,
        description="User's new password (min 8 characters)",
    )


class UserRoleUpdate(BaseModel):
    role: UserRole
