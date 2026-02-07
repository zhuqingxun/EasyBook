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

BATCH_SIZE = 20000
INDEX_NAME = "books"
TASK_TIMEOUT_S = 300  # 等待 Meilisearch 任务完成的超时时间（秒）


def sync():
    logger.info("开始 Meilisearch 同步")

    # 初始化 Meilisearch 同步客户端
    meili_client = Client(settings.MEILI_URL, settings.MEILI_MASTER_KEY)
    index = meili_client.index(INDEX_NAME)

    # 配置索引属性
    index.update_searchable_attributes(["title", "author"])
    index.update_filterable_attributes(["extension", "language"])
    index.update_sortable_attributes(["filesize"])
    logger.info("索引属性已配置")

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

            task_info = index.add_documents(documents, primary_key="id")
            # 等待 Meilisearch 任务完成，确认索引成功
            meili_client.wait_for_task(task_info.task_uid, timeout_in_ms=TASK_TIMEOUT_S * 1000)

            total_synced += len(documents)
            last_id = rows[-1].id
            logger.info("已同步 %d 条文档 (总计: %d)", len(documents), total_synced)

    engine.dispose()
    logger.info("Meilisearch 同步完成: %d 条文档", total_synced)


if __name__ == "__main__":
    sync()
