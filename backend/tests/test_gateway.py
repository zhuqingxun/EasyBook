"""IPFS 网关服务测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.gateway_service import GatewayService


class TestGatewayService:
    """网关 Service 测试"""

    @pytest.mark.asyncio
    async def test_check_single_gateway_success(self):
        """网关检测成功场景"""
        service = GatewayService()

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_response)

        gateway, available, response_time = await service.check_single_gateway(
            "ipfs.io", mock_client
        )

        assert gateway == "ipfs.io"
        assert available is True
        assert response_time is not None
        assert response_time > 0

    @pytest.mark.asyncio
    async def test_check_single_gateway_non_200_unavailable(self):
        """非 200 状态码标记为不可用（follow_redirects=True 下不会收到 3xx）"""
        service = GatewayService()

        for status in [301, 403, 404, 500]:
            mock_response = MagicMock()
            mock_response.status_code = status

            mock_client = AsyncMock()
            mock_client.head = AsyncMock(return_value=mock_response)

            gateway, available, _ = await service.check_single_gateway(
                "test.gateway", mock_client
            )
            assert available is False, f"Status {status} should be treated as unavailable"

    @pytest.mark.asyncio
    async def test_check_single_gateway_timeout(self):
        """网关超时标记为不可用"""
        service = GatewayService()

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        gateway, available, response_time = await service.check_single_gateway(
            "slow.gateway", mock_client
        )

        assert gateway == "slow.gateway"
        assert available is False
        assert response_time is None

    @pytest.mark.asyncio
    async def test_check_single_gateway_rate_limited(self):
        """429 限流标记为不可用"""
        service = GatewayService()

        mock_response = MagicMock()
        mock_response.status_code = 429

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_response)

        gateway, available, response_time = await service.check_single_gateway(
            "limited.gateway", mock_client
        )

        assert available is False
        assert response_time is None

    def test_build_download_url(self):
        """构建下载 URL"""
        service = GatewayService()
        url = service.build_download_url("QmTest123", "ipfs.io")
        assert url == "https://ipfs.io/ipfs/QmTest123"

    @pytest.mark.asyncio
    async def test_get_best_gateway_fallback(self):
        """无健康检查记录时回退到配置列表第一个"""
        service = GatewayService()
        # 模拟 async_session_maker 为 None（DB 未初始化）
        with patch("app.database.async_session_maker", None):
            result = await service.get_best_gateway()
            assert result == service.gateways[0]

    @pytest.mark.asyncio
    async def test_get_alternatives_without_db(self):
        """无 DB 时从配置列表返回备用网关"""
        service = GatewayService()
        with patch("app.database.async_session_maker", None):
            alternatives = await service.get_alternatives("QmTest123", "ipfs.io")
            assert len(alternatives) <= 3
            assert all("ipfs.io" not in url for url in alternatives)


class TestETLCleansing:
    """ETL 数据清洗逻辑测试"""

    def test_is_zh_or_en(self):
        """语言过滤逻辑"""
        from etl.import_annas import is_zh_or_en

        # 中文
        assert is_zh_or_en("zh") is True
        assert is_zh_or_en("Chinese") is True
        assert is_zh_or_en("chi") is True
        # 英文
        assert is_zh_or_en("en") is True
        assert is_zh_or_en("English") is True
        assert is_zh_or_en("eng") is True
        # 空值（保留）
        assert is_zh_or_en(None) is True
        assert is_zh_or_en("") is True
        # 其他语言（过滤）
        assert is_zh_or_en("de") is False
        assert is_zh_or_en("Japanese") is False

    def test_extract_year(self):
        """年份提取"""
        from etl.import_annas import extract_year

        assert extract_year("2024") == "2024"
        assert extract_year("Published in 2020") == "2020"
        assert extract_year(None) is None
        assert extract_year("") is None
        assert extract_year("no year") is None

    def test_parse_record_filters_extension(self):
        """过滤非电子书格式"""
        import opencc

        from etl.import_annas import parse_record

        converter = opencc.OpenCC("t2s")

        record = {
            "title": "Test",
            "extension": "jpg",
            "md5": "abc123",
        }
        assert parse_record(record, converter) is None

    def test_parse_record_valid(self):
        """正常解析记录"""
        import opencc

        from etl.import_annas import parse_record

        converter = opencc.OpenCC("t2s")

        record = {
            "title": "Test Book",
            "author": "Author",
            "extension": "epub",
            "md5_reported": "ABC123DEF456",
            "filesize_reported": 1024,
            "language": "en",
            "ipfs_cid": "QmTest",
            "year": "2024",
            "publisher": "Publisher",
        }
        result = parse_record(record, converter)
        assert result is not None
        assert result["title"] == "Test Book"
        assert result["md5"] == "abc123def456"  # 小写
        assert result["extension"] == "epub"

    def test_parse_record_nested_structure(self):
        """自适应嵌套结构 JSONL"""
        import opencc

        from etl.import_annas import parse_record

        converter = opencc.OpenCC("t2s")

        record = {
            "aacid": "test123",
            "metadata": {
                "title": "Nested Book",
                "extension": "pdf",
                "md5": "def456",
            },
        }
        result = parse_record(record, converter)
        assert result is not None
        assert result["title"] == "Nested Book"

    def test_parse_record_traditional_to_simplified(self):
        """繁体转简体"""
        import opencc

        from etl.import_annas import parse_record

        converter = opencc.OpenCC("t2s")

        record = {
            "title": "電腦程式設計",
            "extension": "pdf",
            "md5": "test123",
        }
        result = parse_record(record, converter)
        assert result is not None
        assert "电脑" in result["title"]  # 繁体 → 简体
