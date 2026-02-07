import logging

from meilisearch_python_sdk import AsyncClient

from app.config import settings

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self):
        self.client: AsyncClient | None = None
        self.index_name = "books"

    async def init(self):
        logger.info("正在初始化 Meilisearch 客户端: url=%s", settings.MEILI_URL)
        self.client = AsyncClient(settings.MEILI_URL, settings.MEILI_MASTER_KEY)
        # 测试连接
        try:
            health = await self.client.health()
            logger.info("Meilisearch 健康检查通过: %s", health)
        except Exception as e:
            logger.error("Meilisearch 健康检查失败: %s", e)
            # 不抛异常，允许应用启动（Meilisearch 可能稍后可用）

    async def close(self):
        if self.client:
            await self.client.aclose()
            logger.info("Meilisearch 客户端已关闭")

    def _ensure_client(self) -> AsyncClient:
        if self.client is None:
            raise RuntimeError("SearchService not initialized, call init() first")
        return self.client

    async def search(self, query: str, page: int = 1, page_size: int = 20) -> dict:
        """搜索书籍，返回 Meilisearch 原始结果"""
        logger.debug("搜索请求: query=%s, page=%d, page_size=%d", query, page, page_size)
        index = self._ensure_client().index(self.index_name)
        result = await index.search(
            query,
            page=page,
            hits_per_page=page_size,
        )
        logger.info(
            "搜索完成: query=%s, total_hits=%s, page=%d",
            query, result.total_hits, page,
        )
        return {
            "hits": result.hits,
            "total_hits": result.total_hits,
            "page": page,
            "page_size": page_size,
        }

    async def configure_index(self):
        """配置 Meilisearch 索引属性（初始化时调用一次）"""
        logger.info("正在配置 Meilisearch 索引: %s", self.index_name)
        index = self._ensure_client().index(self.index_name)
        await index.update_searchable_attributes(["title", "author"])
        await index.update_filterable_attributes(["extension", "language"])
        await index.update_sortable_attributes(["filesize"])
        logger.info("Meilisearch 索引 %s 配置完成", self.index_name)


search_service = SearchService()
