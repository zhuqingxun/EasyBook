"""ETL 数据清洗逻辑测试"""

import pytest


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
        # 繁体中文
        assert is_zh_or_en("traditional chinese") is True
        # 其他语言（过滤）——曾因子串匹配误放行
        assert is_zh_or_en("de") is False
        assert is_zh_or_en("Japanese") is False
        assert is_zh_or_en("french") is False
        assert is_zh_or_en("bengali") is False
        assert is_zh_or_en("slovenian") is False
        assert is_zh_or_en("zhuang") is False
        assert is_zh_or_en("chichewa") is False

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
