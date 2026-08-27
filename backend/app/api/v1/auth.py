from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps.auth import get_current_user
from app.core.exceptions import AppException
from app.services.auth_service import AuthService

router = APIRouter()


class LoginRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    password: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    user: dict


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    is_active: bool
    created_at: str | None = None


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    try:
        svc = AuthService(db)
        return svc.login(body.username, body.password)
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Login failed: {e}")


@router.get("/me", response_model=UserInfo)
def me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        svc = AuthService(db)
        return svc.get_current_user(current_user["id"])
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to get user info: {e}")
