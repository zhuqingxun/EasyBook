"""创建数据库表（开发环境快速建表，不使用 Alembic 迁移）

用法：
    uv run python -m etl.create_tables
"""

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database import Base
from app.models.book import Book  # noqa: F401


async def create_tables():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Tables created successfully")


if __name__ == "__main__":
    asyncio.run(create_tables())
