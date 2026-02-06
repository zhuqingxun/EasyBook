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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    setup_logging()
    logger.info("Starting EasyBook API")
    await init_db()
    await search_service.init()
    try:
        await search_service.configure_index()
    except Exception as e:
        logger.warning("Failed to configure Meilisearch index (may not exist yet): %s", e)
    setup_scheduler()
    scheduler.start()
    # 首次启动时异步执行一次网关健康检查，保持强引用防止 GC 回收
    health_check_task = asyncio.create_task(gateway_service.check_all_gateways())
    logger.info("EasyBook API started")
    yield
    # 关闭
    logger.info("Shutting down EasyBook API")
    if not health_check_task.done():
        health_check_task.cancel()
        try:
            await health_check_task
        except asyncio.CancelledError:
            pass
    scheduler.shutdown(wait=True)
    await search_service.close()
    await close_db()


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
