"""管理面板 API 端点"""

import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import settings
from app.services.cache_service import search_cache
from app.services.search_service import search_service
from app.services.stats_service import stats_service

logger = logging.getLogger(__name__)

router = APIRouter()

# 内存 token 存储（重启失效）
_active_tokens: set[str] = set()


def _require_admin(authorization: str | None = Header(default=None)) -> str:
    """验证管理员 token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证信息")
    token = authorization.removeprefix("Bearer ").strip()
    if token not in _active_tokens:
        raise HTTPException(status_code=401, detail="无效或过期的 token")
    return token


@router.post("/login")
async def admin_login(body: dict):
    """管理员登录，验证密码返回 token"""
    if not settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="管理面板未启用（未设置 ADMIN_PASSWORD）")

    password = body.get("password", "")
    if password != settings.ADMIN_PASSWORD:
        logger.warning("管理面板登录失败: 密码错误")
        raise HTTPException(status_code=401, detail="密码错误")

    token = uuid.uuid4().hex
    _active_tokens.add(token)
    logger.info("管理面板登录成功")
    return {"token": token}


@router.get("/stats")
async def get_stats(_: str = Depends(_require_admin)):
    """获取搜索统计 + 访问量统计"""
    return stats_service.get_stats()


@router.get("/system")
async def get_system_status(_: str = Depends(_require_admin)):
    """获取系统状态：DuckDB、OBS 连接、缓存等"""
    import os
    import psutil

    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()

    return {
        "duckdb": {
            "initialized": search_service._initialized,
            "mode": "remote_obs" if search_service._use_remote else "local",
            "parquet_path": search_service.parquet_path,
        },
        "cache": search_cache.stats(),
        "memory": {
            "rss_mb": round(mem_info.rss / 1024 / 1024, 1),
            "vms_mb": round(mem_info.vms / 1024 / 1024, 1),
        },
    }


@router.get("/cache")
async def get_cache_stats(_: str = Depends(_require_admin)):
    """获取缓存统计"""
    return search_cache.stats()


@router.delete("/cache")
async def clear_cache(_: str = Depends(_require_admin)):
    """清空搜索缓存"""
    search_cache.clear()
    logger.info("管理员清空了搜索缓存")
    return {"message": "缓存已清空"}
