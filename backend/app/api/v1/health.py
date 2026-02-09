import logging
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.database import async_session_maker
from app.schemas.search import HealthResponse

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

    # 检查 DuckDB Parquet 文件
    parquet_path = Path(settings.DUCKDB_PARQUET_PATH)
    if not parquet_path.exists():
        duckdb_status = "error"
        logger.error("Parquet file not found: %s", parquet_path)

    overall = "ok" if db_status == "ok" and duckdb_status == "ok" else "degraded"
    logger.info("健康检查: overall=%s, db=%s, duckdb=%s", overall, db_status, duckdb_status)

    return HealthResponse(
        status=overall,
        database=db_status,
        duckdb=duckdb_status,
    )
