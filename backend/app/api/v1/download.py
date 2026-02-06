import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.book import Book
from app.schemas.search import DownloadResponse
from app.services.gateway_service import gateway_service

logger = logging.getLogger(__name__)

router = APIRouter()

MD5_PATTERN = re.compile(r"^[a-f0-9]{32}$")


async def _lookup_book(md5: str, db: AsyncSession) -> Book:
    """查找书籍，不存在则抛出 404"""
    if not MD5_PATTERN.match(md5.lower()):
        raise HTTPException(status_code=400, detail="Invalid MD5 format")
    stmt = select(Book).where(Book.md5 == md5.lower())
    result = await db.execute(stmt)
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if not book.ipfs_cid:
        raise HTTPException(status_code=404, detail="No IPFS CID available for this book")
    return book


@router.get("/download/{md5}", response_model=DownloadResponse)
async def get_download_url(
    md5: str = Path(..., description="书籍 MD5 哈希"),
    db: AsyncSession = Depends(get_db),
):
    """获取电子书下载链接"""
    book = await _lookup_book(md5, db)

    best_gateway = await gateway_service.get_best_gateway()
    if best_gateway is None:
        raise HTTPException(status_code=503, detail="No IPFS gateway available")

    download_url = gateway_service.build_download_url(book.ipfs_cid, best_gateway)
    alternatives = await gateway_service.get_alternatives(book.ipfs_cid, best_gateway)

    return DownloadResponse(
        download_url=download_url,
        gateway=best_gateway,
        alternatives=alternatives,
    )
