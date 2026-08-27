from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.core.constants import UserRole
def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> dict:
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Invalid authorization header format")

    token = authorization[7:]
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedError("Invalid or expired token")

    from app.models.sqlalchemy.all_models import User
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if user is None:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise UnauthorizedError("User is inactive")

    return {"id": user.id, "username": user.username, "role": user.role}


def require_role(*roles: str):
    def dependency(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in roles:
            raise ForbiddenError(f"Required role: {', '.join(roles)}")
        return current_user
    return dependency
