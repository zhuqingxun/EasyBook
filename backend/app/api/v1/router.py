from fastapi import APIRouter

from app.api.v1 import download, health, search

api_router = APIRouter()
api_router.include_router(search.router, tags=["Search"])
api_router.include_router(download.router, tags=["Download"])
api_router.include_router(health.router, tags=["Health"])
