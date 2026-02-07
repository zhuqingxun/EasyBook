import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """提供数据库 session，不自动 commit。读操作无需额外处理，写操作由调用方显式 commit。"""
    if async_session_maker is None:
        logger.error("数据库未初始化，无法提供 session")
        raise RuntimeError("Database not initialized")
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    global engine, async_session_maker

    # 脱敏打印连接信息
    db_url = settings.DATABASE_URL
    if "@" in db_url:
        safe_url = db_url.split("@")[0].split("://")[0] + "://***@" + db_url.split("@")[1]
    else:
        safe_url = db_url
    logger.info("正在连接数据库: %s", safe_url)

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    logger.info("数据库连接池已创建 (pool_size=10, max_overflow=20)")

    # 测试连接
    try:
        from sqlalchemy import text
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        logger.info("数据库连接测试成功")
    except Exception as e:
        logger.error("数据库连接测试失败: %s", e)
        raise


async def close_db() -> None:
    if engine:
        await engine.dispose()
        logger.info("数据库连接池已关闭")
