import asyncio
import logging
from pathlib import Path

import duckdb

from app.config import settings

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self):
        self.parquet_path: str = ""
        self._initialized: bool = False

    async def init(self):
        """验证 Parquet 文件存在"""
        self.parquet_path = settings.DUCKDB_PARQUET_PATH
        path = Path(self.parquet_path)
        if path.exists():
            count = await asyncio.to_thread(self._get_record_count)
            logger.info(
                "DuckDB 搜索服务初始化成功: parquet=%s, records=%d",
                self.parquet_path, count,
            )
            self._initialized = True
        else:
            logger.warning("Parquet 文件不存在: %s，搜索功能不可用", self.parquet_path)

    async def close(self):
        """无需清理（每次查询用独立连接）"""
        logger.info("DuckDB 搜索服务已关闭")

    async def search(self, query: str, page: int = 1, page_size: int = 20) -> dict:
        """搜索书籍，返回与原 Meilisearch 兼容的结果格式"""
        if not self._initialized:
            raise RuntimeError("SearchService not initialized, call init() first")

        logger.debug("搜索请求: query=%s, page=%d, page_size=%d", query, page, page_size)
        result = await asyncio.to_thread(self._sync_search, query, page, page_size)
        logger.info(
            "搜索完成: query=%s, total_hits=%d, page=%d",
            query, result["total_hits"], page,
        )
        return result

    def _sync_search(self, query: str, page: int, page_size: int) -> dict:
        """同步 DuckDB 查询（在线程中执行）"""
        offset = (page - 1) * page_size
        pattern = f"%{query}%"

        with duckdb.connect(config={
            "threads": str(settings.DUCKDB_THREADS),
            "memory_limit": settings.DUCKDB_MEMORY_LIMIT,
        }) as conn:
            count_sql = """
                SELECT COUNT(*) as cnt
                FROM read_parquet(?)
                WHERE title ILIKE ? OR author ILIKE ?
            """
            total_hits = conn.execute(
                count_sql, [self.parquet_path, pattern, pattern]
            ).fetchone()[0]

            search_sql = """
                SELECT md5 as id, title, author, extension, filesize,
                       language, year, publisher
                FROM read_parquet(?)
                WHERE title ILIKE ? OR author ILIKE ?
                ORDER BY
                    CASE
                        WHEN title ILIKE ? THEN 0
                        WHEN title ILIKE ? THEN 1
                        WHEN title ILIKE ? THEN 2
                        ELSE 3
                    END,
                    LENGTH(title)
                LIMIT ?
                OFFSET ?
            """
            exact = query
            starts = f"{query}%"
            rows = conn.execute(
                search_sql,
                [self.parquet_path, pattern, pattern,
                 exact, starts, pattern,
                 page_size, offset],
            ).fetchall()
            columns = [
                "id", "title", "author", "extension", "filesize",
                "language", "year", "publisher",
            ]
            hits = [dict(zip(columns, row)) for row in rows]

        return {
            "hits": hits,
            "total_hits": total_hits,
            "page": page,
            "page_size": page_size,
        }

    def _get_record_count(self) -> int:
        """获取 Parquet 文件的总记录数"""
        with duckdb.connect() as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM read_parquet(?)", [self.parquet_path]
            ).fetchone()
            return result[0] if result else 0


search_service = SearchService()
