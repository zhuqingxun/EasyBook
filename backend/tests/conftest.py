import pytest


@pytest.fixture
def sample_meilisearch_hits():
    """模拟 Meilisearch 搜索返回的 hits"""
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
