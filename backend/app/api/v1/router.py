from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.search import router as search_router
from app.api.v1.passport import router as passport_router
from app.api.v1.component import router as component_router
from app.api.v1.compare import router as compare_router
from app.api.v1.norms import router as norms_router
from app.api.v1.expert import router as expert_router
from app.api.v1.audit import router as audit_router
from app.api.v1.admin import router as admin_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(passport_router, prefix="/passport", tags=["passport"])
api_router.include_router(component_router, prefix="/component", tags=["component"])
api_router.include_router(compare_router, prefix="/compare", tags=["compare"])
api_router.include_router(norms_router, prefix="/norms", tags=["norms"])
api_router.include_router(expert_router, prefix="/expert", tags=["expert"])
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
