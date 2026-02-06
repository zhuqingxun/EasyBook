import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.models.gateway_health import GatewayHealth

logger = logging.getLogger(__name__)

# IPFS 白皮书 CID，用于健康检查测试
TEST_CID = "QmR7GSQM93Cx5eAg6a6yRzNde1FQv7uL6X1o4k7zrJa3LX"


class GatewayService:
    def __init__(self):
        self.gateways = settings.ipfs_gateway_list

    async def check_single_gateway(
        self, gateway: str, client: httpx.AsyncClient
    ) -> tuple[str, bool, float | None]:
        """检测单个网关可用性，返回 (gateway, available, response_time_ms)"""
        url = f"https://{gateway}/ipfs/{TEST_CID}"
        start = time.monotonic()
        try:
            response = await client.head(url, follow_redirects=True)
            elapsed_ms = (time.monotonic() - start) * 1000
            if response.status_code == 429:
                logger.warning("Gateway %s returned 429 rate limit", gateway)
                return gateway, False, None
            available = response.status_code == 200
            return gateway, available, elapsed_ms if available else None
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning("Gateway %s check failed: %s", gateway, e)
            return gateway, False, None

    async def check_all_gateways(self) -> None:
        """并发检测所有网关，更新数据库"""
        if async_session_maker is None:
            logger.error("数据库未初始化，跳过网关健康检查")
            print("[GATEWAY] 数据库未初始化，跳过健康检查", flush=True)
            return

        logger.info("开始 IPFS 网关健康检查，共 %d 个网关", len(self.gateways))
        print(f"[GATEWAY] 开始检查 {len(self.gateways)} 个网关...", flush=True)
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            tasks = [self.check_single_gateway(gw, client) for gw in self.gateways]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        async with async_session_maker() as session:
            for result in results:
                if isinstance(result, Exception):
                    logger.error("Unexpected error during gateway check: %s", result, exc_info=result)
                    continue

                gateway, available, response_time_ms = result
                stmt = select(GatewayHealth).where(GatewayHealth.gateway_url == gateway)
                db_result = await session.execute(stmt)
                health = db_result.scalar_one_or_none()

                if health is None:
                    health = GatewayHealth(gateway_url=gateway)
                    session.add(health)

                health.last_checked_at = datetime.now(timezone.utc)
                if available:
                    health.available = True
                    health.response_time_ms = response_time_ms
                    health.consecutive_failures = 0
                    logger.info("Gateway %s OK (%.0fms)", gateway, response_time_ms)
                else:
                    health.consecutive_failures += 1
                    if health.consecutive_failures >= settings.HEALTH_CHECK_FAIL_THRESHOLD:
                        health.available = False
                        logger.warning(
                            "Gateway %s marked unavailable after %d failures",
                            gateway,
                            health.consecutive_failures,
                        )

            await session.commit()
        logger.info("网关健康检查完成")
        print("[GATEWAY] 健康检查完成", flush=True)

    async def get_best_gateway(self) -> str | None:
        """返回响应时间最快的可用网关"""
        if async_session_maker is None:
            return self.gateways[0] if self.gateways else None

        async with async_session_maker() as session:
            stmt = (
                select(GatewayHealth)
                .where(GatewayHealth.available.is_(True))
                .order_by(GatewayHealth.response_time_ms.asc().nulls_last())
                .limit(1)
            )
            result = await session.execute(stmt)
            health = result.scalar_one_or_none()

        if health:
            return health.gateway_url
        # 如果没有健康检查记录，返回配置列表中第一个
        return self.gateways[0] if self.gateways else None

    def build_download_url(self, cid: str, gateway: str) -> str:
        """拼接 IPFS 下载 URL"""
        return f"https://{gateway}/ipfs/{cid}"

    async def get_alternatives(self, cid: str, exclude_gateway: str) -> list[str]:
        """返回备用网关 URL 列表"""
        if async_session_maker is None:
            alternatives = [gw for gw in self.gateways if gw != exclude_gateway]
            return [self.build_download_url(cid, gw) for gw in alternatives[:3]]

        async with async_session_maker() as session:
            stmt = (
                select(GatewayHealth)
                .where(
                    GatewayHealth.available.is_(True),
                    GatewayHealth.gateway_url != exclude_gateway,
                )
                .order_by(GatewayHealth.response_time_ms.asc().nulls_last())
                .limit(3)
            )
            result = await session.execute(stmt)
            healths = result.scalars().all()

        return [self.build_download_url(cid, h.gateway_url) for h in healths]


gateway_service = GatewayService()
