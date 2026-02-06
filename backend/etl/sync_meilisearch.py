"""PostgreSQL → Meilisearch 索引同步脚本

用法：
    uv run python -m etl.sync_meilisearch
"""

import logging

from meilisearch_python_sdk import Client
from sqlalchemy import create_engine, text

from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 5000
INDEX_NAME = "books"


def sync():
    logger.info("Starting Meilisearch sync")

    # 初始化 Meilisearch 同步客户端
    meili_client = Client(settings.MEILI_URL, settings.MEILI_MASTER_KEY)
    index = meili_client.index(INDEX_NAME)

    # 配置索引属性
    index.update_searchable_attributes(["title", "author"])
    index.update_filterable_attributes(["extension", "language"])
    index.update_sortable_attributes(["filesize"])
    logger.info("Index attributes configured")

    # 初始化数据库
    engine = create_engine(settings.sync_database_url)

    total_synced = 0
    last_id = 0

    with engine.connect() as conn:
        while True:
            result = conn.execute(
                text(
                    "SELECT id, title, author, extension, filesize, language, "
                    "md5, ipfs_cid, year, publisher FROM books "
                    "WHERE id > :last_id ORDER BY id LIMIT :limit"
                ),
                {"last_id": last_id, "limit": BATCH_SIZE},
            )
            rows = result.fetchall()
            if not rows:
                break

            documents = []
            for row in rows:
                documents.append(
                    {
                        "id": row.md5,
                        "title": row.title,
                        "author": row.author or "",
                        "extension": row.extension,
                        "filesize": row.filesize or 0,
                        "language": row.language or "",
                        "ipfs_cid": row.ipfs_cid or "",
                        "year": row.year or "",
                        "publisher": row.publisher or "",
                    }
                )

            index.add_documents(documents, primary_key="id")
            total_synced += len(documents)
            last_id = rows[-1].id
            logger.info("Synced %d documents (total: %d)", len(documents), total_synced)

    engine.dispose()
    logger.info("Meilisearch sync completed: %d documents", total_synced)


if __name__ == "__main__":
    sync()
