from pydantic import BaseModel, ConfigDict


class BookFormat(BaseModel):
    extension: str
    filesize: int | None = None
    download_url: str
    md5: str = ""
    model_config = ConfigDict(from_attributes=True)


class BookResult(BaseModel):
    id: str  # MD5 作为唯一标识
    title: str
    author: str | None = None
    formats: list[BookFormat]
    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    total: int  # Meilisearch 原始命中记录数
    page: int
    page_size: int
    results: list[BookResult]
    total_books: int  # 合并后的书籍数（同 title+author 合并多格式）


class HealthResponse(BaseModel):
    status: str
    database: str
    meilisearch: str
