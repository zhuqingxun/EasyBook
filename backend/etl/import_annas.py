"""Anna's Archive JSONL.zst 数据导入脚本

用法：
    uv run python -m etl.import_annas <path_to_jsonl_zst>
    uv run python -m etl.import_annas <path_to_jsonl_zst> --dry-run
"""

import argparse
import io
import logging
import re
import sys
import threading
from pathlib import Path
from queue import Queue

import opencc
import orjson
import zstandard as zstd
from psycopg2.extras import execute_values
from sqlalchemy import create_engine

from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"epub", "pdf", "mobi", "azw3"}
YEAR_PATTERN = re.compile(r"\b(\d{4})\b")
CJK_PATTERN = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff"
    r"\U00020000-\U0002a6df\U0002a700-\U0002ebef]"
)
BATCH_SIZE = 5000
PROGRESS_INTERVAL = 50000
SENTINEL = None  # 队列结束标记


ALLOWED_LANGUAGES = {
    "zh", "chi", "chinese", "traditional chinese",
    "en", "eng", "english",
}


def is_zh_or_en(language: str | None) -> bool:
    """判断是否为中文或英文记录（空值也保留）"""
    if not language:
        return True
    return language.lower().strip() in ALLOWED_LANGUAGES


def extract_year(year_str: str | None) -> str | None:
    """从年份字段提取四位数字"""
    if not year_str:
        return None
    match = YEAR_PATTERN.search(str(year_str))
    return match.group(1) if match else None


def _clean_str(s: str) -> str:
    """移除 PostgreSQL 不接受的 NUL 字符"""
    return s.replace("\x00", "")


def _needs_t2s(text: str) -> bool:
    """检查文本是否包含 CJK 字符，用于决定是否需要 OpenCC 转换"""
    return bool(CJK_PATTERN.search(text))


def parse_record(data: dict, converter: opencc.OpenCC) -> dict | None:
    """解析单条 JSONL 记录，返回清洗后的字典或 None（过滤掉）"""
    # 自适应 JSONL 解析：嵌套结构 vs 扁平结构
    fields = data.get("metadata", data)

    title = _clean_str((fields.get("title") or "").strip())[:512]
    if not title:
        return None

    extension = (fields.get("extension") or "").lower().strip()
    if extension not in ALLOWED_EXTENSIONS:
        return None

    md5 = (fields.get("md5_reported") or fields.get("md5") or "").strip().lower()[:32]
    if not md5:
        return None

    language = fields.get("language")
    if not is_zh_or_en(language):
        return None

    author = _clean_str((fields.get("author") or "").strip())[:512]

    # 简繁体转换：仅对含 CJK 字符的文本执行
    if _needs_t2s(title):
        title = converter.convert(title)
    if author and _needs_t2s(author):
        author = converter.convert(author)

    filesize = fields.get("filesize_reported") or fields.get("filesize")
    if filesize is not None:
        try:
            filesize = int(filesize)
        except (ValueError, TypeError):
            filesize = None

    publisher = _clean_str((fields.get("publisher") or "").strip()[:255])

    return {
        "title": title,
        "author": author or None,
        "extension": extension,
        "filesize": filesize,
        "language": (language or "").strip()[:20] or None,
        "md5": md5,
        "year": extract_year(fields.get("year")),
        "publisher": publisher or None,
    }


def _save_checkpoint(checkpoint_path: Path, line_number: int) -> None:
    """保存断点续传检查点"""
    checkpoint_path.write_text(str(line_number), encoding="utf-8")


def _load_checkpoint(checkpoint_path: Path) -> int:
    """加载断点续传检查点，返回已处理的行号（0 表示从头开始）"""
    if checkpoint_path.exists():
        try:
            return int(checkpoint_path.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            logger.warning("无法读取 checkpoint 文件，将从头开始导入")
    return 0


INSERT_SQL = """
    INSERT INTO books (title, author, extension, filesize, language, md5, year, publisher)
    VALUES %s
    ON CONFLICT (md5) DO NOTHING
"""

COLUMNS = ("title", "author", "extension", "filesize", "language", "md5", "year", "publisher")


def _db_writer(engine, queue: Queue, stats: dict) -> None:
    """消费者线程：从队列取批次写入数据库"""
    while True:
        item = queue.get()
        if item is SENTINEL:
            queue.task_done()
            break

        batch, batch_line_number, checkpoint_path = item
        try:
            raw_conn = engine.raw_connection()
            try:
                cursor = raw_conn.cursor()
                values = [tuple(record[col] for col in COLUMNS) for record in batch]
                execute_values(cursor, INSERT_SQL, values, page_size=len(values))
                raw_conn.commit()
                cursor.close()
            finally:
                raw_conn.close()

            # 写入 checkpoint
            if checkpoint_path:
                _save_checkpoint(checkpoint_path, batch_line_number)
        except Exception:
            logger.exception("批量插入失败 (batch_size=%d)，跳过该批次", len(batch))
            stats["skipped"] += len(batch)
        finally:
            queue.task_done()


def import_data(file_path: str, dry_run: bool = False) -> None:
    path = Path(file_path)
    if not path.exists():
        logger.error("文件不存在: %s", file_path)
        sys.exit(1)

    converter = opencc.OpenCC("t2s")

    # 断点续传：checkpoint 文件与源文件同目录
    checkpoint_path = path.with_suffix(".checkpoint")
    start_line = _load_checkpoint(checkpoint_path)
    if start_line > 0:
        logger.info("检测到断点续传，从第 %d 行继续", start_line + 1)

    logger.info("开始导入 %s (dry_run=%s)", file_path, dry_run)

    engine = None if dry_run else create_engine(settings.sync_database_url)

    total_read = 0
    total_imported = 0
    total_filtered = 0
    stats = {"skipped": 0}  # 可变对象供写入线程共享
    batch: list[dict] = []

    # 生产者-消费者队列（最多缓冲 2 个批次，防止内存爆炸）
    queue: Queue = Queue(maxsize=2)
    writer_thread = None

    if engine is not None:
        writer_thread = threading.Thread(
            target=_db_writer, args=(engine, queue, stats), daemon=True
        )
        writer_thread.start()

    dctx = zstd.ZstdDecompressor(max_window_size=2**31)

    try:
        with open(path, "rb") as fh:
            with dctx.stream_reader(fh) as reader:
                text_reader = io.TextIOWrapper(reader, encoding="utf-8")
                for line in text_reader:
                    total_read += 1

                    # 断点续传：跳过已处理的行
                    if total_read <= start_line:
                        continue

                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = orjson.loads(line)
                    except orjson.JSONDecodeError:
                        logger.warning("无效 JSON，行号 %d", total_read)
                        continue

                    record = parse_record(data, converter)
                    if record is None:
                        total_filtered += 1
                        continue

                    batch.append(record)

                    if len(batch) >= BATCH_SIZE:
                        if engine is not None:
                            queue.put((batch.copy(), total_read, checkpoint_path))
                        total_imported += len(batch)
                        batch.clear()

                    if total_read % PROGRESS_INTERVAL == 0:
                        logger.info(
                            "进度: read=%d imported=%d filtered=%d skipped=%d",
                            total_read,
                            total_imported,
                            total_filtered,
                            stats["skipped"],
                        )

        # 处理剩余批次
        if batch:
            if engine is not None:
                queue.put((batch.copy(), total_read, checkpoint_path))
            total_imported += len(batch)

    finally:
        # 等待写入线程完成
        if writer_thread is not None:
            queue.put(SENTINEL)
            queue.join()
            writer_thread.join()

    # 导入成功完成，删除 checkpoint 文件
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        logger.info("导入完成，已清理 checkpoint 文件")

    logger.info(
        "导入完成: total_read=%d imported=%d filtered=%d skipped=%d",
        total_read,
        total_imported,
        total_filtered,
        stats["skipped"],
    )

    if engine is not None:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Import Anna's Archive JSONL.zst data")
    parser.add_argument("file", help="Path to JSONL.zst file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse only, do not write to database",
    )
    args = parser.parse_args()
    import_data(args.file, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
