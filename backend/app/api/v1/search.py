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
    q: str | None = Query(None, max_length=200, description="搜索关键词（旧版兼容）"),
    title: str | None = Query(None, max_length=200, description="书名搜索"),
    author: str | None = Query(None, max_length=200, description="作者搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """搜索电子书：支持 title/author 分字段搜索（AND 关系），兼容旧版 q 参数"""
    # 至少需要提供一个搜索条件
    if not q and not title and not author:
        raise HTTPException(status_code=400, detail="至少需要提供 q、title、author 中的一个搜索条件")

    # 确定实际搜索参数：优先使用 title/author，否则回退到 q
    search_title = title.strip() if title else ""
    search_author = author.strip() if author else ""
    search_q: str | None = None
    if not search_title and not search_author:
        search_q = q.strip() if q else None

    logger.info(
        "收到搜索请求: q=%s, title=%s, author=%s, page=%d, page_size=%d",
        search_q, search_title, search_author, page, page_size,
    )
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    # 缓存 key 使用 title/author（旧版 q 统一映射到 title）
    cache_title = search_title or (search_q or "")
    cache_author = search_author

    # 检查缓存
    cached = search_cache.get(cache_title, cache_author, page, page_size)
    if cached is not None:
        elapsed = time.time() - start_time
        stats_label = " | ".join(filter(None, [search_title, search_author, search_q or ""]))
        stats_service.record_search(stats_label, elapsed, client_ip)
        logger.info("搜索缓存命中: title=%s, author=%s, elapsed=%.3fs", cache_title, cache_author, elapsed)
        return cached

    # 未命中，查询 DuckDB
    try:
        result = await search_service.search(
            search_q, page, page_size,
            title=search_title or None,
            author=search_author or None,
        )
    except (RuntimeError, OSError) as e:
        logger.error(
            "搜索服务不可用: title=%s, author=%s, q=%s, error=%s: %s",
            search_title, search_author, search_q, type(e).__name__, e,
        )
        raise HTTPException(status_code=503, detail="搜索服务暂时不可用，请稍后重试")
    except Exception:
        logger.exception("搜索时发生未预期错误: title=%s, author=%s, q=%s", search_title, search_author, search_q)
        raise HTTPException(status_code=500, detail="Internal search error")

    hits = result["hits"]

    # 按 title+author 合并多格式
    merged: dict[str, dict] = {}
    for hit in hits:
        hit_title = (hit.get("title") or "").strip()
        hit_author = (hit.get("author") or "").strip()
        merge_key = (hit_title.lower(), hit_author.lower())

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
                "title": hit_title,
                "author": hit_author or None,
                "formats": [fmt],
            }
        else:
            merged[merge_key]["formats"].append(fmt)

    # 相关性排序：基于 title 字段（分字段搜索用 search_title，旧版用 q）
    sort_term = (search_title or search_q or "").strip().lower()

    def relevance_key(item: dict) -> tuple:
        t = (item.get("title") or "").lower()
        if t == sort_term:
            rank = 0
        elif t.startswith(sort_term):
            rank = 1
        elif sort_term in t:
            rank = 2
        else:
            rank = 3
        return (rank, len(t))

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

    # 写入缓存
    response_dict = response.model_dump()
    search_cache.put(cache_title, cache_author, page, page_size, response_dict)

    elapsed = time.time() - start_time
    stats_label = " | ".join(filter(None, [search_title, search_author, search_q or ""]))
    stats_service.record_search(stats_label, elapsed, client_ip)

    logger.info(
        "搜索响应: title=%s, author=%s, q=%s, total=%d, total_books=%d, page=%d, elapsed=%.2fs",
        search_title, search_author, search_q, response.total, response.total_books, response.page, elapsed,
    )
    return response
