import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.database import async_session_maker
from app.schemas.search import HealthResponse
from app.services.search_service import search_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """系统健康检查"""
    db_status = "ok"
    meili_status = "ok"

    # 检查 PostgreSQL
    try:
        if async_session_maker:
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        db_status = "error"

    # 检查 Meilisearch
    try:
        if search_service.client:
            await search_service.client.health()
    except Exception as e:
        logger.error("Meilisearch health check failed: %s", e)
        meili_status = "error"

    overall = "ok" if db_status == "ok" and meili_status == "ok" else "degraded"
    logger.info(
        "健康检查: overall=%s, db=%s, meili=%s",
        overall, db_status, meili_status,
    )

    return HealthResponse(
        status=overall,
        database=db_status,
        meilisearch=meili_status,
    )
