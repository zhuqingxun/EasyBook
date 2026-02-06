"""EasyBook API 入口模块

早期启动阶段使用 print() 直接输出到 stdout，确保即使 logging 未初始化也能看到日志。
"""

import os
import sys
import time

# === 最早期启动日志（在任何 import 之前）===
_start_time = time.time()
print(f"[BOOT] EasyBook API 启动中... Python {sys.version}", flush=True)
print(f"[BOOT] 工作目录: {os.getcwd()}", flush=True)
print("[BOOT] 环境变量:", flush=True)
print(f"[BOOT]   PORT={os.environ.get('PORT', '(未设置)')}", flush=True)

# 安全打印环境变量（脱敏处理）
_db_url = os.environ.get("DATABASE_URL", "")
_meili_url = os.environ.get("MEILI_URL", "")
if _db_url:
    # 只显示协议和主机部分，隐藏密码
    _safe_db = _db_url.split("@")[-1] if "@" in _db_url else _db_url[:40]
    print(f"[BOOT]   DATABASE_URL=已设置 (host: {_safe_db})", flush=True)
else:
    print("[BOOT]   DATABASE_URL=未设置，将使用默认值 (localhost)", flush=True)

print(f"[BOOT]   MEILI_URL={_meili_url or '未设置，将使用默认值'}", flush=True)
print(f"[BOOT]   MEILI_MASTER_KEY={'已设置' if os.environ.get('MEILI_MASTER_KEY') else '未设置'}", flush=True)
print(f"[BOOT]   CORS_ORIGINS={os.environ.get('CORS_ORIGINS', '(未设置)')}", flush=True)
print(f"[BOOT]   LOG_LEVEL={os.environ.get('LOG_LEVEL', '(未设置)')}", flush=True)
print(f"[BOOT]   DEBUG={os.environ.get('DEBUG', '(未设置)')}", flush=True)
print(f"[BOOT]   IPFS_GATEWAYS={os.environ.get('IPFS_GATEWAYS', '(未设置)')}", flush=True)

# === 开始导入依赖 ===
print("[BOOT] 开始导入依赖...", flush=True)

try:
    import asyncio
    import logging
    from contextlib import asynccontextmanager

    print("[BOOT] 标准库导入完成", flush=True)

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    print("[BOOT] FastAPI 导入完成", flush=True)

    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    print("[BOOT] SlowAPI 导入完成", flush=True)

    from app.api.v1.router import api_router

    print("[BOOT] API 路由导入完成", flush=True)

    from app.config import settings

    print(f"[BOOT] 配置加载完成: DEBUG={settings.DEBUG}, LOG_LEVEL={settings.LOG_LEVEL}", flush=True)
    print(f"[BOOT]   DATABASE_URL 前缀: {settings.DATABASE_URL[:50]}...", flush=True)
    print(f"[BOOT]   MEILI_URL: {settings.MEILI_URL}", flush=True)
    print(f"[BOOT]   CORS_ORIGINS: {settings.CORS_ORIGINS}", flush=True)
    print(f"[BOOT]   IPFS 网关数量: {len(settings.ipfs_gateway_list)}", flush=True)

    from app.core.logging_config import setup_logging
    from app.database import close_db, init_db
    from app.services.gateway_service import gateway_service
    from app.services.scheduler_service import scheduler, setup_scheduler
    from app.services.search_service import search_service

    print("[BOOT] 所有模块导入完成", flush=True)

except Exception as e:
    print(f"[BOOT][FATAL] 导入阶段失败: {type(e).__name__}: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

logger = logging.getLogger(__name__)

_elapsed = time.time() - _start_time
print(f"[BOOT] 模块加载耗时: {_elapsed:.2f}s", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动和关闭时的资源初始化/清理"""
    print("[LIFESPAN] 进入 lifespan 上下文...", flush=True)

    # 1. 初始化日志系统
    try:
        setup_logging()
        logger.info("[LIFESPAN] 日志系统初始化完成")
    except Exception as e:
        print(f"[LIFESPAN][ERROR] 日志初始化失败: {e}", flush=True)
        # 继续执行，至少 print 能工作

    # 2. 初始化数据库
    try:
        logger.info("[LIFESPAN] 正在初始化数据库连接...")
        print("[LIFESPAN] 正在初始化数据库连接...", flush=True)
        await init_db()
        logger.info("[LIFESPAN] 数据库连接池初始化成功")
        print("[LIFESPAN] 数据库连接池初始化成功", flush=True)
    except Exception as e:
        logger.exception("[LIFESPAN] 数据库初始化失败")
        print(f"[LIFESPAN][ERROR] 数据库初始化失败: {type(e).__name__}: {e}", flush=True)
        print("[LIFESPAN] 应用将继续启动，但数据库功能不可用", flush=True)

    # 3. 初始化 Meilisearch 客户端
    try:
        logger.info("[LIFESPAN] 正在初始化 Meilisearch 客户端...")
        print("[LIFESPAN] 正在初始化 Meilisearch 客户端...", flush=True)
        await search_service.init()
        logger.info("[LIFESPAN] Meilisearch 客户端初始化成功")
        print("[LIFESPAN] Meilisearch 客户端初始化成功", flush=True)
    except Exception as e:
        logger.exception("[LIFESPAN] Meilisearch 客户端初始化失败")
        print(f"[LIFESPAN][ERROR] Meilisearch 初始化失败: {type(e).__name__}: {e}", flush=True)

    # 4. 配置 Meilisearch 索引
    try:
        logger.info("[LIFESPAN] 正在配置 Meilisearch 索引...")
        await search_service.configure_index()
        logger.info("[LIFESPAN] Meilisearch 索引配置完成")
        print("[LIFESPAN] Meilisearch 索引配置完成", flush=True)
    except Exception as e:
        logger.warning("[LIFESPAN] Meilisearch 索引配置失败（索引可能不存在）: %s", e)
        print(f"[LIFESPAN][WARN] Meilisearch 索引配置失败: {e}", flush=True)

    # 5. 启动定时调度器
    try:
        logger.info("[LIFESPAN] 正在启动调度器...")
        setup_scheduler()
        scheduler.start()
        logger.info("[LIFESPAN] 调度器启动成功")
        print("[LIFESPAN] 调度器启动成功", flush=True)
    except Exception as e:
        logger.exception("[LIFESPAN] 调度器启动失败")
        print(f"[LIFESPAN][ERROR] 调度器启动失败: {type(e).__name__}: {e}", flush=True)

    # 6. 异步执行首次网关健康检查
    health_check_task = None
    try:
        health_check_task = asyncio.create_task(gateway_service.check_all_gateways())
        logger.info("[LIFESPAN] 网关健康检查任务已创建")
        print("[LIFESPAN] 网关健康检查任务已创建", flush=True)
    except Exception as e:
        logger.exception("[LIFESPAN] 创建网关健康检查任务失败")
        print(f"[LIFESPAN][ERROR] 网关健康检查任务创建失败: {e}", flush=True)

    total_startup = time.time() - _start_time
    logger.info("[LIFESPAN] EasyBook API 启动完成！总耗时: %.2fs", total_startup)
    print(f"[LIFESPAN] EasyBook API 启动完成！总耗时: {total_startup:.2f}s", flush=True)
    print(f"[LIFESPAN] 监听端口: {os.environ.get('PORT', '8080')}", flush=True)

    yield

    # === 关闭阶段 ===
    logger.info("[LIFESPAN] 开始关闭 EasyBook API...")
    print("[LIFESPAN] 开始关闭 EasyBook API...", flush=True)

    if health_check_task and not health_check_task.done():
        health_check_task.cancel()
        try:
            await health_check_task
        except asyncio.CancelledError:
            pass
        logger.info("[LIFESPAN] 网关健康检查任务已取消")

    try:
        scheduler.shutdown(wait=True)
        logger.info("[LIFESPAN] 调度器已关闭")
    except Exception as e:
        logger.exception("[LIFESPAN] 调度器关闭失败: %s", e)

    try:
        await search_service.close()
        logger.info("[LIFESPAN] Meilisearch 客户端已关闭")
    except Exception as e:
        logger.exception("[LIFESPAN] Meilisearch 关闭失败: %s", e)

    try:
        await close_db()
        logger.info("[LIFESPAN] 数据库连接已关闭")
    except Exception as e:
        logger.exception("[LIFESPAN] 数据库关闭失败: %s", e)

    logger.info("[LIFESPAN] EasyBook API 已完全关闭")
    print("[LIFESPAN] EasyBook API 已完全关闭", flush=True)


print("[BOOT] 正在创建 FastAPI 应用...", flush=True)

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

print("[BOOT] FastAPI 应用创建完成，等待 uvicorn 启动...", flush=True)
