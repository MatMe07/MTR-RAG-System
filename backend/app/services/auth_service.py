from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError, ConflictError, NotFoundError
from app.core.security import hash_password, verify_password, create_access_token
from app.models.sqlalchemy.all_models import User


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def login(self, username: str, password: str) -> dict[str, Any]:
        user = self.db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid username or password")
        if not user.is_active:
            raise UnauthorizedError("Account is disabled")

        token = create_access_token(data={"sub": str(user.id), "role": user.role})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
            },
        }

    def register(self, username: str, password: str, role: str = "user") -> dict[str, Any]:
        existing = self.db.query(User).filter(User.username == username).first()
        if existing:
            raise ConflictError(f"User '{username}' already exists")

        user = User(
            username=username,
            hashed_password=hash_password(password),
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

    def get_current_user(self, user_id: int) -> dict[str, Any]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
