import json
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://easybook:easybook@localhost:5432/easybook"
    # Meilisearch
    MEILI_URL: str = "http://localhost:7700"
    MEILI_MASTER_KEY: str = ""
    # IPFS 网关（逗号分隔字符串）
    IPFS_GATEWAYS: str = (
        "ipfs.io,dweb.link,gateway.pinata.cloud,ipfs.filebase.io,w3s.link,4everland.io"
    )
    # 健康检查配置
    HEALTH_CHECK_INTERVAL_HOURS: int = 24
    HEALTH_CHECK_FAIL_THRESHOLD: int = 3
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    # 应用配置
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    @property
    def ipfs_gateway_list(self) -> List[str]:
        return [g.strip() for g in self.IPFS_GATEWAYS.split(",") if g.strip()]

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


settings = Settings()
