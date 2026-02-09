"""搜索服务和多格式合并逻辑测试"""

from unittest.mock import patch

import pytest

from app.schemas.search import BookFormat, BookResult


class TestFormatMerge:
    """测试搜索结果中同一本书多格式合并"""

    def test_merge_same_book_formats(self, sample_search_hits):
        """同 title+author 的多条记录合并为 formats 列表"""
        hits = sample_search_hits

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

    def test_download_url_is_empty_string(self, sample_search_hits):
        """download_url 始终为空字符串（前端自行构建 Anna's Archive URL）"""
        for hit in sample_search_hits:
            fmt = BookFormat(
                extension=hit["extension"],
                filesize=hit.get("filesize"),
                download_url="",
            )
            assert fmt.download_url == ""


class TestSearchService:
    """搜索 Service 测试"""

    @pytest.mark.asyncio
    async def test_search_returns_correct_format(self):
        """验证搜索通过 DuckDB 返回正确格式"""
        from app.services.search_service import SearchService

        service = SearchService()
        service._initialized = True
        service.parquet_path = "dummy.parquet"

        mock_result = {
            "hits": [{"id": "test", "title": "Test Book", "author": "Author",
                       "extension": "epub", "filesize": 1000,
                       "language": "en", "year": "2024", "publisher": "Pub"}],
            "total_hits": 1,
            "page": 1,
            "page_size": 20,
        }

        with patch.object(service, "_sync_search", return_value=mock_result):
            result = await service.search("test")

        assert result["hits"] == mock_result["hits"]
        assert result["total_hits"] == 1
        assert result["page"] == 1
        assert result["page_size"] == 20

    @pytest.mark.asyncio
    async def test_search_pagination(self):
        """验证分页参数正确传递"""
        from app.services.search_service import SearchService

        service = SearchService()
        service._initialized = True
        service.parquet_path = "dummy.parquet"

        mock_result = {
            "hits": [],
            "total_hits": 0,
            "page": 3,
            "page_size": 10,
        }

        with patch.object(service, "_sync_search", return_value=mock_result) as mock_sync:
            result = await service.search("python", page=3, page_size=10)

        mock_sync.assert_called_once_with("python", 3, 10, None, None)
        assert result["page"] == 3
        assert result["page_size"] == 10

    @pytest.mark.asyncio
    async def test_search_not_initialized_raises(self):
        """未初始化时搜索抛出 RuntimeError"""
        from app.services.search_service import SearchService

        service = SearchService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await service.search("test")
