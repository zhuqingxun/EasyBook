"""数据库迁移：移除 IPFS 相关字段和表

用法：
    uv run python -m etl.migrate_remove_ipfs
    uv run python -m etl.migrate_remove_ipfs --dry-run
"""

import argparse
import logging

from sqlalchemy import create_engine, text

from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

MIGRATIONS = [
    ("删除 books.ipfs_cid 列", "ALTER TABLE books DROP COLUMN IF EXISTS ipfs_cid"),
    ("删除 gateway_health 表", "DROP TABLE IF EXISTS gateway_health"),
]


def migrate(dry_run: bool = False) -> None:
    engine = create_engine(settings.sync_database_url)

    with engine.begin() as conn:
        for desc, sql in MIGRATIONS:
            logger.info("执行迁移: %s", desc)
            if dry_run:
                logger.info("  [DRY RUN] SQL: %s", sql)
            else:
                conn.execute(text(sql))
                logger.info("  完成")

    engine.dispose()
    logger.info("迁移%s完成", "预览" if dry_run else "")


def main() -> None:
    parser = argparse.ArgumentParser(description="移除 IPFS 相关数据库字段和表")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
