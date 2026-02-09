"""PostgreSQL → Parquet 导出脚本

用法:
    cd backend
    uv run python -m etl.export_parquet [--output ./data/books.parquet]

将本地 PostgreSQL 中的 books 表导出为 DuckDB 可直接查询的 Parquet 文件。
"""

import argparse
import logging
import time
from pathlib import Path

import duckdb

from app.config import settings

logger = logging.getLogger(__name__)


def export_to_parquet(output_path: str) -> int:
    """将 PostgreSQL books 表导出为 Parquet 文件，返回导出记录数"""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    pg_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    start = time.time()
    logger.info("开始导出: PG → %s", output_path)

    with duckdb.connect() as conn:
        conn.install_extension("postgres")
        conn.load_extension("postgres")

        conn.execute(f"ATTACH '{pg_url}' AS pg (TYPE POSTGRES, READ_ONLY)")

        conn.execute(f"""
            COPY (
                SELECT md5, title, author, extension, filesize,
                       language, year, publisher
                FROM pg.public.books
                WHERE md5 IS NOT NULL AND md5 != ''
                  AND title IS NOT NULL AND title != ''
            ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION SNAPPY, ROW_GROUP_SIZE 100000)
        """)

        count = conn.execute(
            f"SELECT COUNT(*) FROM read_parquet('{output_path}')"
        ).fetchone()[0]

    elapsed = time.time() - start
    logger.info(
        "导出完成: %d 条记录, 耗时 %.1f 秒, 文件: %s",
        count, elapsed, output_path,
    )
    return count


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="PostgreSQL → Parquet 导出")
    parser.add_argument(
        "--output", "-o",
        default="./data/books.parquet",
        help="输出 Parquet 文件路径 (默认: ./data/books.parquet)",
    )
    args = parser.parse_args()
    export_to_parquet(args.output)


if __name__ == "__main__":
    main()
