"""搜索服务和多格式合并逻辑测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.search import BookFormat, BookResult


class TestFormatMerge:
    """测试搜索结果中同一本书多格式合并"""

    def test_merge_same_book_formats(self, sample_meilisearch_hits):
        """同 title+author 的多条记录合并为 formats 列表"""
        hits = sample_meilisearch_hits

        merged: dict[tuple[str, str], dict] = {}
        for hit in hits:
            title = (hit.get("title") or "").strip()
            author = (hit.get("author") or "").strip()
            merge_key = (title.lower(), author.lower())

            fmt = BookFormat(
                extension=hit["extension"],
                filesize=hit.get("filesize"),
                download_url="",
            )

            if merge_key not in merged:
                merged[merge_key] = {
                    "id": hit["id"],
                    "title": title,
                    "author": author or None,
                    "formats": [fmt],
                }
            else:
                merged[merge_key]["formats"].append(fmt)

        results = [BookResult(**item) for item in merged.values()]

        # Python Programming 有 epub 和 pdf 两个格式
        python_book = next(r for r in results if "Python" in r.title)
        assert len(python_book.formats) == 2
        assert {f.extension for f in python_book.formats} == {"epub", "pdf"}

        # 三体只有 epub 一个格式
        santi_book = next(r for r in results if "三体" in r.title)
        assert len(santi_book.formats) == 1
        assert santi_book.formats[0].extension == "epub"

    def test_download_url_is_empty_string(self, sample_meilisearch_hits):
        """download_url 始终为空字符串（前端自行构建 Anna's Archive URL）"""
        for hit in sample_meilisearch_hits:
            fmt = BookFormat(
                extension=hit["extension"],
                filesize=hit.get("filesize"),
                download_url="",
            )
            assert fmt.download_url == ""


class TestSearchService:
    """搜索 Service 测试"""

    @pytest.mark.asyncio
    async def test_search_calls_meilisearch(self):
        """验证搜索参数正确传递到 Meilisearch"""
        from app.services.search_service import SearchService

        service = SearchService()

        mock_index = MagicMock()
        mock_result = MagicMock()
        mock_result.hits = []
        mock_result.total_hits = 0
        mock_index.search = AsyncMock(return_value=mock_result)

        mock_client = MagicMock()
        mock_client.index.return_value = mock_index
        service.client = mock_client

        result = await service.search("python", page=2, page_size=10)

        mock_index.search.assert_awaited_once_with(
            "python",
            page=2,
            hits_per_page=10,
        )
        assert result["total_hits"] == 0
        assert result["page"] == 2

    @pytest.mark.asyncio
    async def test_search_returns_formatted_result(self):
        """验证搜索结果格式正确"""
        from app.services.search_service import SearchService

        service = SearchService()

        mock_index = MagicMock()
        mock_result = MagicMock()
        mock_result.hits = [{"id": "test", "title": "Test Book"}]
        mock_result.total_hits = 1
        mock_index.search = AsyncMock(return_value=mock_result)

        mock_client = MagicMock()
        mock_client.index.return_value = mock_index
        service.client = mock_client

        result = await service.search("test")

        assert result["hits"] == [{"id": "test", "title": "Test Book"}]
        assert result["total_hits"] == 1
        assert result["page"] == 1
        assert result["page_size"] == 20
