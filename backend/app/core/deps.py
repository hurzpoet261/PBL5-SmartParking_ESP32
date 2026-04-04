from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_access_token
from app.models import StaffUser
from app.models.enums import StaffRole, UserStatus


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> StaffUser:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise UnauthorizedException("Invalid or expired token")

    user = db.execute(
        select(StaffUser).where(StaffUser.user_id == int(payload["sub"]))
    ).scalar_one_or_none()
    if not user or user.status != UserStatus.ACTIVE:
        raise UnauthorizedException("User is inactive or not found")
    return user


def require_admin(current_user: StaffUser = Depends(get_current_user)) -> StaffUser:
    if current_user.role != StaffRole.ADMIN:
        raise UnauthorizedException("Admin permission required")
    return current_user
