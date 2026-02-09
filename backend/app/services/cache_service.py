"""LRU 搜索缓存服务"""

import logging
from collections import OrderedDict
from threading import Lock

logger = logging.getLogger(__name__)


class SearchCache:
    """基于 OrderedDict 的 LRU 搜索缓存"""

    def __init__(self, max_size: int = 500):
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._max_size = max_size
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    def _make_key(self, title: str, author: str, page: int, page_size: int) -> str:
        return f"t:{title.lower().strip()}|a:{author.lower().strip()}:{page}:{page_size}"

    def get(self, title: str, author: str, page: int, page_size: int) -> dict | None:
        key = self._make_key(title, author, page, page_size)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self.hits += 1
                logger.debug("缓存命中: key=%s", key)
                return self._cache[key]
            self.misses += 1
            return None

    def put(self, title: str, author: str, page: int, page_size: int, result: dict) -> None:
        key = self._make_key(title, author, page, page_size)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._max_size:
                    evicted_key, _ = self._cache.popitem(last=False)
                    logger.debug("缓存淘汰: key=%s", evicted_key)
                self._cache[key] = result
            logger.debug("缓存写入: key=%s, size=%d", key, len(self._cache))

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0
        logger.info("缓存已清空")

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 4) if total > 0 else 0,
        }


search_cache = SearchCache()
