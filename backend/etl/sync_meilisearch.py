"""PostgreSQL → Meilisearch 索引同步脚本

支持滑动窗口并发提交、断点续传、实时进度展示。

用法：
    uv run python -m etl.sync_meilisearch
    uv run python -m etl.sync_meilisearch --batch-size 50000 --max-pending 5
    uv run python -m etl.sync_meilisearch --no-resume   # 禁用断点续传，从头开始
"""

import argparse
import logging
import time
from collections import deque
from pathlib import Path

from meilisearch_python_sdk import Client
from sqlalchemy import create_engine, text

from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

INDEX_NAME = "books"
DEFAULT_BATCH_SIZE = 50000
DEFAULT_MAX_PENDING = 5
DEFAULT_CHECKPOINT_FILE = "data/sync_meilisearch.checkpoint"
TASK_TIMEOUT_MS = 600_000  # 单个任务等待超时 10 分钟


def _save_checkpoint(checkpoint_path: Path, last_id: int) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(str(last_id), encoding="utf-8")


def _load_checkpoint(checkpoint_path: Path) -> int:
    if checkpoint_path.exists():
        try:
            return int(checkpoint_path.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            logger.warning("无法读取 checkpoint 文件，将从头开始同步")
    return 0


def _format_duration(seconds: float) -> str:
    """格式化秒数为 HH:MM:SS。"""
    h, remainder = divmod(int(seconds), 3600)
    m, s = divmod(remainder, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _format_number(n: int) -> str:
    """格式化数字为千分位分隔。"""
    return f"{n:,}"


def sync(
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_pending: int = DEFAULT_MAX_PENDING,
    resume: bool = True,
    checkpoint_file: str = DEFAULT_CHECKPOINT_FILE,
) -> None:
    checkpoint_path = Path(checkpoint_file)

    # 断点续传
    last_id = _load_checkpoint(checkpoint_path) if resume else 0
    if last_id > 0:
        logger.info("从断点续传: last_id = %d", last_id)

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

    # 查询总记录数（用于进度计算）
    with engine.connect() as conn:
        total_count = conn.execute(text("SELECT COUNT(*) FROM books")).scalar()
        if last_id > 0:
            remaining_count = conn.execute(
                text("SELECT COUNT(*) FROM books WHERE id > :last_id"),
                {"last_id": last_id},
            ).scalar()
        else:
            remaining_count = total_count

    logger.info(
        "总记录数: %s, 待同步: %s",
        _format_number(total_count),
        _format_number(remaining_count),
    )

    total_synced = 0
    start_time = time.monotonic()

    # 滑动窗口：存储 (task_uid, batch_last_id, batch_doc_count)
    pending_tasks: deque[tuple[int, int, int]] = deque()

    def _drain_oldest() -> None:
        """等待并处理窗口中最早的任务。"""
        nonlocal total_synced
        task_uid, task_last_id, doc_count = pending_tasks.popleft()
        result = meili_client.wait_for_task(
            task_uid,
            timeout_in_ms=TASK_TIMEOUT_MS,
            raise_for_status=True,
        )
        if result.status != "succeeded":
            logger.error(
                "任务 %d 失败: status=%s, error=%s",
                task_uid, result.status, result.error,
            )
            raise RuntimeError(f"Meilisearch 任务 {task_uid} 失败: {result.error}")

        total_synced += doc_count
        # 更新 checkpoint 为最早完成任务的 last_id
        _save_checkpoint(checkpoint_path, task_last_id)
        _print_progress(total_synced, remaining_count, start_time)

    def _print_progress(synced: int, total: int, t_start: float) -> None:
        elapsed = time.monotonic() - t_start
        if elapsed < 0.1:
            return
        pct = synced / total * 100 if total > 0 else 100.0
        speed = synced / elapsed
        eta = (total - synced) / speed if speed > 0 else 0
        logger.info(
            "进度: %s / %s (%.2f%%) | 速度: %s docs/s | 已用: %s | 剩余: ~%s",
            _format_number(synced),
            _format_number(total),
            pct,
            _format_number(int(speed)),
            _format_duration(elapsed),
            _format_duration(eta),
        )

    with engine.connect() as conn:
        while True:
            result = conn.execute(
                text(
                    "SELECT id, title, author, extension, filesize, language, "
                    "md5, year, publisher FROM books "
                    "WHERE id > :last_id ORDER BY id LIMIT :limit"
                ),
                {"last_id": last_id, "limit": batch_size},
            )
            rows = result.fetchall()
            if not rows:
                break

            documents = [
                {
                    "id": row.md5,
                    "title": row.title,
                    "author": row.author or "",
                    "extension": row.extension,
                    "filesize": row.filesize or 0,
                    "language": row.language or "",
                    "year": row.year or "",
                    "publisher": row.publisher or "",
                }
                for row in rows
            ]

            # 滑动窗口满时，先等待最早的任务完成
            if len(pending_tasks) >= max_pending:
                _drain_oldest()

            # 提交批次，不等待
            task_info = index.add_documents(
                documents, primary_key="id", compress=True,
            )
            batch_last_id = rows[-1].id
            pending_tasks.append((task_info.task_uid, batch_last_id, len(documents)))
            last_id = batch_last_id

    # 排空剩余的待处理任务
    while pending_tasks:
        _drain_oldest()

    engine.dispose()

    elapsed = time.monotonic() - start_time
    logger.info(
        "Meilisearch 同步完成: %s 条文档, 耗时 %s",
        _format_number(total_synced),
        _format_duration(elapsed),
    )

    # 同步成功完成，删除 checkpoint 文件
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        logger.info("已清理 checkpoint 文件")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="同步 PostgreSQL 数据到 Meilisearch",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"每批文档数（默认 {DEFAULT_BATCH_SIZE}）",
    )
    parser.add_argument(
        "--max-pending",
        type=int,
        default=DEFAULT_MAX_PENDING,
        help=f"滑动窗口大小，最大并发任务数（默认 {DEFAULT_MAX_PENDING}）",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否启用断点续传（默认启用，--no-resume 禁用）",
    )
    parser.add_argument(
        "--checkpoint-file",
        type=str,
        default=DEFAULT_CHECKPOINT_FILE,
        help=f"checkpoint 文件路径（默认 {DEFAULT_CHECKPOINT_FILE}）",
    )
    args = parser.parse_args()

    sync(
        batch_size=args.batch_size,
        max_pending=args.max_pending,
        resume=args.resume,
        checkpoint_file=args.checkpoint_file,
    )


if __name__ == "__main__":
    main()
