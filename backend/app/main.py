"""EasyBook API 入口模块"""

import asyncio
import os
import sys
import time

# === Boot 阶段（logging 未初始化，仅用 print）===
_start_time = time.time()
print(f"[BOOT] EasyBook API 启动中... Python {sys.version}", flush=True)

try:
    import logging
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    from app.api.v1.router import api_router
    from app.config import settings
    from app.core.logging_config import setup_logging
    from app.database import close_db, init_db
    from app.services.cache_service import search_cache
    from app.services.search_service import search_service
    from app.services.stats_service import stats_service

except Exception as e:
    print(f"[BOOT][FATAL] 导入阶段失败: {type(e).__name__}: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

logger = logging.getLogger(__name__)
print(f"[BOOT] 模块加载完成，耗时: {time.time() - _start_time:.2f}s", flush=True)
# === Boot 阶段结束 ===

# 后台统计保存任务引用
_stats_save_task: asyncio.Task | None = None


async def _periodic_stats_save():
    """每 5 分钟保存一次统计数据"""
    while True:
        await asyncio.sleep(300)
        try:
            stats_service.save_to_file(settings.STATS_FILE_PATH)
        except Exception:
            logger.exception("定时保存统计数据失败")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动和关闭时的资源初始化/清理"""
    global _stats_save_task

    # 1. 初始化日志系统
    try:
        setup_logging()
        logger.info("日志系统初始化完成")
    except Exception as e:
        print(f"[LIFESPAN][FATAL] 日志初始化失败: {e}", flush=True)

    # 2. 初始化数据库
    try:
        logger.info("正在初始化数据库连接...")
        await init_db()
        logger.info("数据库连接池初始化成功")
    except Exception:
        logger.exception("数据库初始化失败")
        logger.warning("应用将继续启动，但数据库功能不可用")

    # 3. 初始化 DuckDB 搜索服务
    try:
        logger.info("正在初始化 DuckDB 搜索服务...")
        await search_service.init()
        logger.info("DuckDB 搜索服务初始化成功")
    except Exception:
        logger.exception("DuckDB 搜索服务初始化失败")

    # 4. 初始化缓存大小
    if settings.CACHE_MAX_SIZE != search_cache._max_size:
        search_cache._max_size = settings.CACHE_MAX_SIZE
        logger.info("缓存大小设置为: %d", settings.CACHE_MAX_SIZE)

    # 5. 加载统计数据
    try:
        stats_service.load_from_file(settings.STATS_FILE_PATH)
    except Exception:
        logger.exception("加载统计数据失败")

    # 6. 启动定时保存任务
    _stats_save_task = asyncio.create_task(_periodic_stats_save())

    total_startup = time.time() - _start_time
    logger.info("EasyBook API 启动完成！总耗时: %.2fs，监听端口: %s",
                total_startup, os.environ.get("PORT", "8080"))

    yield

    # === 关闭阶段 ===
    logger.info("开始关闭 EasyBook API...")

    # 取消定时保存任务
    if _stats_save_task:
        _stats_save_task.cancel()
        try:
            await _stats_save_task
        except asyncio.CancelledError:
            pass

    # 最终保存统计数据
    try:
        stats_service.save_to_file(settings.STATS_FILE_PATH)
        logger.info("统计数据最终保存完成")
    except Exception:
        logger.exception("统计数据最终保存失败")

    try:
        await search_service.close()
        logger.info("DuckDB 搜索服务已关闭")
    except Exception as e:
        logger.exception("DuckDB 搜索服务关闭失败: %s", e)

    try:
        await close_db()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.exception("数据库关闭失败: %s", e)

    logger.info("EasyBook API 已完全关闭")


app = FastAPI(
    title="EasyBook API",
    description="电子书聚合搜索平台 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 限流（内存存储）
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def stats_middleware(request: Request, call_next):
    """记录每次请求的 PV/UV 统计"""
    client_ip = request.client.host if request.client else "unknown"
    stats_service.record_request(client_ip)
    response = await call_next(request)
    return response


# 路由
app.include_router(api_router, prefix="/api")
