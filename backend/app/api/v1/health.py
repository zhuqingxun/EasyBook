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
    duckdb_status = "ok"

    # 检查 PostgreSQL（保留用于 ETL 场景，生产可忽略）
    try:
        if async_session_maker:
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        db_status = "error"

    # 检查 DuckDB 搜索服务（支持本地和远程模式）
    if not search_service._initialized:
        duckdb_status = "error"
        logger.error("DuckDB search service not initialized")

    overall = "ok" if db_status == "ok" and duckdb_status == "ok" else "degraded"
    logger.info("健康检查: overall=%s, db=%s, duckdb=%s", overall, db_status, duckdb_status)

    return HealthResponse(
        status=overall,
        database=db_status,
        duckdb=duckdb_status,
    )
