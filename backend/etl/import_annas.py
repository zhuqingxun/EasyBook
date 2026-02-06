"""Anna's Archive JSONL.zst 数据导入脚本

用法：
    uv run python -m etl.import_annas <path_to_jsonl_zst>
    uv run python -m etl.import_annas <path_to_jsonl_zst> --dry-run
"""

import argparse
import io
import json
import logging
import re
import sys
from pathlib import Path

import opencc
import zstandard as zstd
from sqlalchemy import create_engine, text

from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"epub", "pdf", "mobi", "azw3"}
YEAR_PATTERN = re.compile(r"\b(\d{4})\b")
BATCH_SIZE = 1000
PROGRESS_INTERVAL = 10000


def is_zh_or_en(language: str | None) -> bool:
    """判断是否为中文或英文记录（空值也保留）"""
    if not language:
        return True
    lang_lower = language.lower()
    return any(
        k in lang_lower for k in ["zh", "chi", "chinese", "en", "eng", "english"]
    )


def extract_year(year_str: str | None) -> str | None:
    """从年份字段提取四位数字"""
    if not year_str:
        return None
    match = YEAR_PATTERN.search(str(year_str))
    return match.group(1) if match else None


def parse_record(data: dict, converter: opencc.OpenCC) -> dict | None:
    """解析单条 JSONL 记录，返回清洗后的字典或 None（过滤掉）"""
    # 自适应 JSONL 解析：嵌套结构 vs 扁平结构
    fields = data.get("metadata", data)

    title = (fields.get("title") or "").strip()
    if not title:
        return None

    extension = (fields.get("extension") or "").lower().strip()
    if extension not in ALLOWED_EXTENSIONS:
        return None

    md5 = (fields.get("md5_reported") or fields.get("md5") or "").strip().lower()
    if not md5:
        return None

    language = fields.get("language")
    if not is_zh_or_en(language):
        return None

    author = (fields.get("author") or "").strip()

    # 简繁体转换
    title = converter.convert(title)
    if author:
        author = converter.convert(author)

    filesize = fields.get("filesize_reported") or fields.get("filesize")
    if filesize is not None:
        try:
            filesize = int(filesize)
        except (ValueError, TypeError):
            filesize = None

    return {
        "title": title,
        "author": author or None,
        "extension": extension,
        "filesize": filesize,
        "language": (language or "").strip()[:20] or None,
        "md5": md5,
        "ipfs_cid": (fields.get("ipfs_cid") or "").strip() or None,
        "year": extract_year(fields.get("year")),
        "publisher": (fields.get("publisher") or "").strip()[:255] or None,
    }


def import_data(file_path: str, dry_run: bool = False) -> None:
    path = Path(file_path)
    if not path.exists():
        logger.error("File not found: %s", file_path)
        sys.exit(1)

    converter = opencc.OpenCC("t2s")
    logger.info("Starting import from %s (dry_run=%s)", file_path, dry_run)

    engine = None if dry_run else create_engine(settings.sync_database_url)

    total_read = 0
    total_imported = 0
    total_filtered = 0
    batch = []

    dctx = zstd.ZstdDecompressor(max_window_size=2**31)

    with open(path, "rb") as fh:
        with dctx.stream_reader(fh) as reader:
            text_reader = io.TextIOWrapper(reader, encoding="utf-8")
            for line in text_reader:
                total_read += 1
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON at line %d", total_read)
                    continue

                record = parse_record(data, converter)
                if record is None:
                    total_filtered += 1
                    continue

                batch.append(record)

                if len(batch) >= BATCH_SIZE:
                    if engine is not None:
                        _insert_batch(engine, batch)
                    total_imported += len(batch)
                    batch.clear()

                if total_read % PROGRESS_INTERVAL == 0:
                    logger.info(
                        "Progress: read=%d imported=%d filtered=%d",
                        total_read,
                        total_imported,
                        total_filtered,
                    )

    # 处理剩余批次
    if batch:
        if engine is not None:
            _insert_batch(engine, batch)
        total_imported += len(batch)

    logger.info(
        "Import completed: total_read=%d imported=%d filtered=%d",
        total_read,
        total_imported,
        total_filtered,
    )

    if engine is not None:
        engine.dispose()


def _insert_batch(engine, batch: list[dict]) -> None:
    """批量插入，ON CONFLICT (md5) DO NOTHING 去重"""
    insert_sql = text("""
        INSERT INTO books (title, author, extension, filesize, language, md5, ipfs_cid, year, publisher)
        VALUES (:title, :author, :extension, :filesize, :language, :md5, :ipfs_cid, :year, :publisher)
        ON CONFLICT (md5) DO NOTHING
    """)
    with engine.begin() as conn:
        conn.execute(insert_sql, batch)


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
