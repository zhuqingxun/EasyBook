import logging

from fastapi import APIRouter
from sqlalchemy import func, select, text

from app.database import async_session_maker
from app.models.gateway_health import GatewayHealth
from app.schemas.search import HealthResponse
from app.services.search_service import search_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """系统健康检查"""
    db_status = "ok"
    meili_status = "ok"
    last_health_check = None

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

    # 获取最近一次网关健康检查时间
    try:
        if async_session_maker:
            async with async_session_maker() as session:
                stmt = select(func.max(GatewayHealth.last_checked_at))
                result = await session.execute(stmt)
                last_check = result.scalar()
                if last_check:
                    last_health_check = last_check.isoformat()
    except Exception as e:
        logger.error("Failed to get last health check time: %s", e)

    overall = "ok" if db_status == "ok" and meili_status == "ok" else "degraded"
    logger.info(
        "健康检查: overall=%s, db=%s, meili=%s",
        overall, db_status, meili_status,
    )

    return HealthResponse(
        status=overall,
        database=db_status,
        meilisearch=meili_status,
        last_health_check=last_health_check,
    )
