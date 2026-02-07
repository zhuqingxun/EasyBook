"""EasyBook API 入口模块"""

import os
import sys
import time

# === Boot 阶段（logging 未初始化，仅用 print）===
_start_time = time.time()
print(f"[BOOT] EasyBook API 启动中... Python {sys.version}", flush=True)

try:
    import asyncio
    import logging
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    from app.api.v1.router import api_router
    from app.config import settings
    from app.core.logging_config import setup_logging
    from app.database import close_db, init_db
    from app.services.gateway_service import gateway_service
    from app.services.scheduler_service import scheduler, setup_scheduler
    from app.services.search_service import search_service

except Exception as e:
    print(f"[BOOT][FATAL] 导入阶段失败: {type(e).__name__}: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

logger = logging.getLogger(__name__)
print(f"[BOOT] 模块加载完成，耗时: {time.time() - _start_time:.2f}s", flush=True)
# === Boot 阶段结束 ===


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动和关闭时的资源初始化/清理"""
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
    except Exception as e:
        logger.exception("数据库初始化失败")
        logger.warning("应用将继续启动，但数据库功能不可用")

    # 3. 初始化 Meilisearch 客户端
    try:
        logger.info("正在初始化 Meilisearch 客户端...")
        await search_service.init()
        logger.info("Meilisearch 客户端初始化成功")
    except Exception as e:
        logger.exception("Meilisearch 客户端初始化失败")

    # 4. 配置 Meilisearch 索引
    try:
        logger.info("正在配置 Meilisearch 索引...")
        await search_service.configure_index()
        logger.info("Meilisearch 索引配置完成")
    except Exception as e:
        logger.warning("Meilisearch 索引配置失败（索引可能不存在）: %s", e)

    # 5. 启动定时调度器
    try:
        logger.info("正在启动调度器...")
        setup_scheduler()
        scheduler.start()
        logger.info("调度器启动成功")
    except Exception as e:
        logger.exception("调度器启动失败")

    # 6. 异步执行首次网关健康检查
    health_check_task = None
    try:
        health_check_task = asyncio.create_task(gateway_service.check_all_gateways())
        logger.info("网关健康检查任务已创建")
    except Exception as e:
        logger.exception("创建网关健康检查任务失败")

    total_startup = time.time() - _start_time
    logger.info("EasyBook API 启动完成！总耗时: %.2fs，监听端口: %s",
                total_startup, os.environ.get("PORT", "8080"))

    yield

    # === 关闭阶段 ===
    logger.info("开始关闭 EasyBook API...")

    if health_check_task and not health_check_task.done():
        health_check_task.cancel()
        try:
            await health_check_task
        except asyncio.CancelledError:
            pass
        logger.info("网关健康检查任务已取消")

    try:
        scheduler.shutdown(wait=True)
        logger.info("调度器已关闭")
    except Exception as e:
        logger.exception("调度器关闭失败: %s", e)

    try:
        await search_service.close()
        logger.info("Meilisearch 客户端已关闭")
    except Exception as e:
        logger.exception("Meilisearch 关闭失败: %s", e)

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

# 路由
app.include_router(api_router, prefix="/api")
