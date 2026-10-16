from fastapi import APIRouter

from app.api.v1.routers import admin, analytics, auth, documents, search

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(search.router)
api_router.include_router(documents.router)
api_router.include_router(analytics.router)
api_router.include_router(admin.router)
