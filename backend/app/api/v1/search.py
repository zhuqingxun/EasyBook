import logging
import time

from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas.search import BookFormat, BookResult, SearchResponse
from app.services.cache_service import search_cache
from app.services.search_service import search_service
from app.services.stats_service import stats_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search_books(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """搜索电子书"""
    logger.info("收到搜索请求: q=%s, page=%d, page_size=%d", q, page, page_size)
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    # 检查缓存
    cached = search_cache.get(q, page, page_size)
    if cached is not None:
        elapsed = time.time() - start_time
        stats_service.record_search(q, elapsed, client_ip)
        logger.info("搜索缓存命中: q=%s, elapsed=%.3fs", q, elapsed)
        return cached

    # 未命中，查询 DuckDB
    try:
        result = await search_service.search(q, page, page_size)
    except (RuntimeError, OSError) as e:
        logger.error("搜索服务不可用: query=%s, error=%s: %s", q, type(e).__name__, e)
        raise HTTPException(status_code=503, detail="搜索服务暂时不可用，请稍后重试")
    except Exception:
        logger.exception("搜索时发生未预期错误: query=%s", q)
        raise HTTPException(status_code=500, detail="Internal search error")

    hits = result["hits"]

    # 按 title+author 合并多格式
    merged: dict[str, dict] = {}
    for hit in hits:
        title = (hit.get("title") or "").strip()
        author = (hit.get("author") or "").strip()
        merge_key = (title.lower(), author.lower())

        extension = hit.get("extension", "")
        filesize = hit.get("filesize")

        fmt = BookFormat(
            extension=extension,
            filesize=filesize if filesize else None,
            download_url="",
            md5=hit.get("id", ""),
        )

        if merge_key not in merged:
            merged[merge_key] = {
                "id": hit.get("id", ""),
                "title": title,
                "author": author or None,
                "formats": [fmt],
            }
        else:
            merged[merge_key]["formats"].append(fmt)

    q_lower = q.strip().lower()

    def relevance_key(item: dict) -> tuple:
        title = (item.get("title") or "").lower()
        if title == q_lower:
            rank = 0
        elif title.startswith(q_lower):
            rank = 1
        elif q_lower in title:
            rank = 2
        else:
            rank = 3
        return (rank, len(title))

    sorted_items = sorted(merged.values(), key=relevance_key)

    # 在 Python 层分页（因为 SQL 获取了较大批次用于排序）
    start = (page - 1) * page_size
    page_items = sorted_items[start:start + page_size]
    results = [BookResult(**item) for item in page_items]

    response = SearchResponse(
        total=result["total_hits"],
        page=page,
        page_size=page_size,
        results=results,
        total_books=len(results),
    )

    # 写入缓存（存序列化后的 dict 以便直接返回）
    response_dict = response.model_dump()
    search_cache.put(q, page, page_size, response_dict)

    elapsed = time.time() - start_time
    stats_service.record_search(q, elapsed, client_ip)

    logger.info(
        "搜索响应: q=%s, total=%d, total_books=%d, page=%d, elapsed=%.2fs",
        q, response.total, response.total_books, response.page, elapsed,
    )
    return response
