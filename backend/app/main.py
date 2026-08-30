import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import AppException

setup_logging()
log = get_logger("main")

DEFAULT_USERS = (
    ("admin", "admin123", "admin"),
    ("expert", "expert123", "expert"),
    ("auditor", "auditor123", "auditor"),
    ("user", "user123", "user"),
)


def seed_default_users() -> None:
    """Создаёт учётные записи по умолчанию, если их ещё нет в БД."""
    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.models.sqlalchemy.all_models import User

    db = SessionLocal()
    try:
        for username, default_password, role in DEFAULT_USERS:
            if db.query(User).filter(User.username == username).first():
                continue
            password = os.getenv(f"INITIAL_{username.upper()}_PASSWORD", default_password)
            db.add(User(
                username=username,
                hashed_password=hash_password(password),
                role=role,
                is_active=True,
            ))
            log.info("Seeded default user '%s' (role=%s)", username, role)
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("MTR-RAG-System starting up")

    seed_default_users()
    log.info("Default users ensured")

    yield
    log.info("MTR-RAG-System shutting down")


app = FastAPI(
    title="MTR RAG System",
    description="Система интеллектуального подбора МТР",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )


from app.api.v1.router import api_router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
