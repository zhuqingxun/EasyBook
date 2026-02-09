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
        self._use_remote: bool = False

    async def init(self):
        """初始化搜索服务：优先本地文件，否则尝试远程 OBS"""
        self.parquet_path = settings.DUCKDB_PARQUET_PATH
        local_path = Path(self.parquet_path)

        if local_path.exists():
            # 本地文件模式
            count = await asyncio.to_thread(self._get_record_count)
            logger.info(
                "DuckDB 搜索服务初始化成功（本地）: parquet=%s, records=%d",
                self.parquet_path, count,
            )
            self._initialized = True
        elif settings.OBS_ACCESS_KEY_ID and settings.OBS_SECRET_ACCESS_KEY:
            # 远程 OBS 模式
            self._use_remote = True
            self.parquet_path = (
                f"s3://{settings.OBS_BUCKET}/{settings.OBS_PARQUET_KEY}"
            )
            try:
                count = await asyncio.to_thread(self._get_record_count)
                logger.info(
                    "DuckDB 搜索服务初始化成功（远程 OBS）: parquet=%s, records=%d",
                    self.parquet_path, count,
                )
                self._initialized = True
            except Exception as e:
                logger.error("远程 OBS Parquet 初始化失败: %s", e)
        else:
            logger.warning(
                "Parquet 文件不存在且未配置 OBS 凭证，搜索功能不可用"
            )

    def _create_connection(self) -> duckdb.DuckDBPyConnection:
        """创建 DuckDB 连接，远程模式下加载 httpfs 并配置 S3"""
        conn = duckdb.connect(config={
            "threads": str(settings.DUCKDB_THREADS),
            "memory_limit": settings.DUCKDB_MEMORY_LIMIT,
        })
        if self._use_remote:
            conn.install_extension("httpfs")
            conn.load_extension("httpfs")
            conn.execute(f"SET s3_endpoint='{settings.OBS_ENDPOINT}'")
            conn.execute(f"SET s3_access_key_id='{settings.OBS_ACCESS_KEY_ID}'")
            conn.execute(
                f"SET s3_secret_access_key='{settings.OBS_SECRET_ACCESS_KEY}'"
            )
            conn.execute("SET s3_url_style='vhost'")
            conn.execute("SET s3_region='ap-southeast-3'")
        return conn

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
        pattern = f"%{query}%"
        fetch_limit = max(page_size * 10, 200)

        with self._create_connection() as conn:
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
                LIMIT ?
            """
            rows = conn.execute(
                search_sql,
                [self.parquet_path, pattern, pattern, fetch_limit],
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
        with self._create_connection() as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM read_parquet(?)", [self.parquet_path]
            ).fetchone()
            return result[0] if result else 0


search_service = SearchService()
