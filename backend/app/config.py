import json
import sys
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://easybook:easybook@localhost:5432/easybook"
    # DuckDB
    DUCKDB_PARQUET_PATH: str = "./data/books.parquet"
    DUCKDB_MEMORY_LIMIT: str = "256MB"
    DUCKDB_THREADS: int = 2
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    # 应用配置
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    @property
    def sync_database_url(self) -> str:
        """ETL 脚本使用的同步数据库 URL（psycopg2）"""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


try:
    settings = Settings()
except Exception as e:
    print(f"[CONFIG][FATAL] Settings 加载失败: {type(e).__name__}: {e}", flush=True)
    sys.exit(1)
