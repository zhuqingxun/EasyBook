import logging

from meilisearch_python_sdk import AsyncClient

from app.config import settings

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self):
        self.client: AsyncClient | None = None
        self.index_name = "books"

    async def init(self):
        self.client = AsyncClient(settings.MEILI_URL, settings.MEILI_MASTER_KEY)
        logger.info("Meilisearch client initialized")

    async def close(self):
        if self.client:
            await self.client.aclose()

    def _ensure_client(self) -> AsyncClient:
        if self.client is None:
            raise RuntimeError("SearchService not initialized, call init() first")
        return self.client

    async def search(self, query: str, page: int = 1, page_size: int = 20) -> dict:
        """搜索书籍，返回 Meilisearch 原始结果"""
        index = self._ensure_client().index(self.index_name)
        result = await index.search(
            query,
            page=page,
            hits_per_page=page_size,
        )
        return {
            "hits": result.hits,
            "total_hits": result.total_hits,
            "page": page,
            "page_size": page_size,
        }

    async def configure_index(self):
        """配置 Meilisearch 索引属性（初始化时调用一次）"""
        index = self._ensure_client().index(self.index_name)
        await index.update_searchable_attributes(["title", "author"])
        await index.update_filterable_attributes(["extension", "language"])
        await index.update_sortable_attributes(["filesize"])
        logger.info("Meilisearch index configured")


search_service = SearchService()
