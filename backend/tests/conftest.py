import pytest


@pytest.fixture
def sample_search_hits():
    """模拟搜索返回的 hits（DuckDB 和 Meilisearch 共用格式）"""
    return [
        {
            "id": "abc123def456",
            "title": "Python Programming",
            "author": "John Doe",
            "extension": "epub",
            "filesize": 5242880,
            "language": "en",
            "year": "2024",
            "publisher": "Test Publisher",
        },
        {
            "id": "abc123def789",
            "title": "Python Programming",
            "author": "John Doe",
            "extension": "pdf",
            "filesize": 10485760,
            "language": "en",
            "year": "2024",
            "publisher": "Test Publisher",
        },
        {
            "id": "xyz789abc123",
            "title": "三体",
            "author": "刘慈欣",
            "extension": "epub",
            "filesize": 1048576,
            "language": "zh",
            "year": "2008",
            "publisher": "",
        },
    ]


# 向后兼容别名
@pytest.fixture
def sample_meilisearch_hits(sample_search_hits):
    return sample_search_hits
