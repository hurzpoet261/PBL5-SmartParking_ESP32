from datetime import datetime

from pydantic import BaseModel

from app.models.enums import StaffRole, UserStatus
from app.schemas.common import ORMBaseSchema


class LoginRequest(BaseModel):
    username: str
    password: str


class StaffUserResponse(ORMBaseSchema):
    user_id: int
    lot_id: int | None
    full_name: str
    username: str
    role: StaffRole
    phone: str | None
    email: str | None
    status: UserStatus
    created_at: datetime
    updated_at: datetime
