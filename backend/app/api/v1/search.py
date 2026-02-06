import logging

from fastapi import APIRouter, HTTPException, Query
from meilisearch_python_sdk.errors import MeilisearchError

from app.schemas.search import BookFormat, BookResult, SearchResponse
from app.services.gateway_service import gateway_service
from app.services.search_service import search_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search_books(
    q: str = Query(..., min_length=1, max_length=200, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """搜索电子书"""
    try:
        result = await search_service.search(q, page, page_size)
    except (MeilisearchError, ConnectionError, TimeoutError) as e:
        logger.error("Search failed for query=%s: %s", q, e)
        raise HTTPException(status_code=503, detail="Search service unavailable")

    hits = result["hits"]
    best_gateway = await gateway_service.get_best_gateway()

    # 按 title+author 合并多格式
    merged: dict[str, dict] = {}
    for hit in hits:
        title = (hit.get("title") or "").strip()
        author = (hit.get("author") or "").strip()
        merge_key = (title.lower(), author.lower())

        ipfs_cid = hit.get("ipfs_cid") or ""
        extension = hit.get("extension", "")
        filesize = hit.get("filesize")

        if ipfs_cid and best_gateway:
            download_url = gateway_service.build_download_url(ipfs_cid, best_gateway)
        else:
            download_url = ""

        fmt = BookFormat(
            extension=extension,
            filesize=filesize if filesize else None,
            download_url=download_url,
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

    results = [BookResult(**item) for item in merged.values()]

    return SearchResponse(
        total=result["total_hits"],
        page=result["page"],
        page_size=result["page_size"],
        results=results,
        total_books=len(results),
    )
