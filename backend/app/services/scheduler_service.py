import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


def setup_scheduler():
    from app.services.gateway_service import gateway_service

    scheduler.add_job(
        gateway_service.check_all_gateways,
        "interval",
        hours=settings.HEALTH_CHECK_INTERVAL_HOURS,
        id="ipfs_health_check",
        replace_existing=True,
    )
    logger.info(
        "Scheduler configured: health check every %dh",
        settings.HEALTH_CHECK_INTERVAL_HOURS,
    )
