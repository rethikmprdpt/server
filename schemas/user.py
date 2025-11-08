from datetime import datetime

from pydantic import BaseModel, ConfigDict

from db.models import UserRole


class UserBase(BaseModel):
    username: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class UserRead(UserBase):
    user_id: int
    last_login: datetime | None = None
