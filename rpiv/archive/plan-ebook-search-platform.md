---
description: "功能实施计划: 电子书聚合搜索平台 MVP"
status: archived
created_at: 2026-02-06T16:10:00
updated_at: 2026-02-06T21:50:00
archived_at: 2026-02-06T21:50:00
related_files:
  - rpiv/requirements/prd-ebook-search-platform.md
  - ebook_system_design.md
  - meilisearch_technical_notes.md
  - vue3_vite_search_best_practices.md
  - fastapi_best_practices.md
  - anna_archive_datasets_research.md
  - rpiv/ipfs_gateway_research.md
---

# 功能：电子书聚合搜索平台 MVP

以下计划应该是完整的，但在开始实施之前，验证文档和代码库模式以及任务合理性非常重要。

特别注意现有工具、类型和模型的命名。从正确的文件导入等。

## 功能描述

EasyBook 是一个电子书聚合搜索平台，为用户提供统一的电子书检索入口。平台汇聚 Anna's Archive、Z-Library 等开源元数据库的书籍信息，用户通过关键词搜索即可找到所需电子书，并通过 IPFS 去中心化网络获取可靠的下载链接。

核心价值：通过"静态索引入库 + IPFS 内容寻址交付"的策略，从根本上解决资源分散和死链两大痛点。

## 用户故事

作为一个中文电子书读者
我想要在一个平台上通过关键词搜索所有来源的电子书
以便快速找到并下载我需要的书籍，无需辗转多个网站

## 问题陈述

当前电子书资源分散在众多网站，用户查找一本书往往需要辗转多个站点，且经常遇到下载链接失效的问题。没有一个统一的聚合入口提供可靠的搜索和下载体验。

## 解决方案陈述

构建一个 Web 搜索平台：
1. 离线批量导入 Anna's Archive/Z-Library 元数据到 PostgreSQL + Meilisearch
2. 提供 FastAPI 搜索 API 对接 Meilisearch 全文检索
3. 基于 IPFS CID 动态拼接最优网关下载链接
4. Vue3 前端提供简洁的搜索和下载界面
5. 后台定时检查 IPFS 网关健康状态

## 功能元数据

**功能类型**：新功能
**估计复杂度**：高
**主要受影响的系统**：全新项目（后端 + 前端 + 数据管道 + 定时任务）
**依赖项**：Docker（PostgreSQL + Meilisearch）、uv（Python）、pnpm（Node.js）

---

## 上下文参考

### 相关代码库文件 重要：在实施之前必须阅读这些文件！

- `rpiv/requirements/prd-ebook-search-platform.md` - 完整的产品需求文档（API 规范、数据模型、验收标准）
- `ebook_system_design.md` - 系统架构设计参考（数据库表结构、BFF 架构图）
- `meilisearch_technical_notes.md` - Meilisearch 配置指南（中文分词、索引配置、分页、Docker Compose）
- `fastapi_best_practices.md` - FastAPI 项目结构和最佳实践（异步数据库、Pydantic v2、CORS、限流、日志）
- `vue3_vite_search_best_practices.md` - Vue3 前端搜索界面模板（组件设计、路由、状态管理、Axios 封装）
- `anna_archive_datasets_research.md` - Anna's Archive 数据格式详解（JSONL 字段、编码处理、ETL 注意事项）
- `rpiv/ipfs_gateway_research.md` - IPFS 网关健康检查实现（HEAD 请求、限流、熔断、故障转移）

### 要创建的新文件

**后端：**
```
backend/
├── pyproject.toml                    # uv 项目配置
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI 应用入口 + lifespan
│   ├── config.py                     # pydantic-settings 配置
│   ├── database.py                   # SQLAlchemy 异步引擎 + 会话
│   ├── models/
│   │   ├── __init__.py
│   │   └── book.py                   # Book ORM 模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── search.py                 # 搜索请求/响应 Pydantic 模型
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py             # 路由汇总
│   │       ├── search.py             # /api/search 搜索路由
│   │       ├── download.py           # /api/download/{id} 下载路由
│   │       └── health.py             # /api/health 健康检查路由
│   ├── services/
│   │   ├── __init__.py
│   │   ├── search_service.py         # Meilisearch 搜索业务逻辑
│   │   ├── gateway_service.py        # IPFS 网关管理和健康检查
│   │   └── scheduler_service.py      # APScheduler 定时任务
│   └── core/
│       ├── __init__.py
│       └── logging_config.py         # 日志配置
├── etl/
│   ├── __init__.py
│   ├── import_annas.py               # Anna's Archive JSONL 导入脚本
│   └── sync_meilisearch.py           # PostgreSQL → Meilisearch 同步脚本
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_search.py
    └── test_gateway.py
```

**前端：**
```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── .env
├── .env.production
└── src/
    ├── main.ts
    ├── App.vue
    ├── AppContent.vue
    ├── env.d.ts
    ├── api/
    │   ├── request.ts                # Axios 封装
    │   └── modules/
    │       └── search.ts             # 搜索 API
    ├── types/
    │   └── search.ts                 # 搜索类型定义
    ├── components/
    │   ├── SearchBox.vue             # 搜索框
    │   ├── BookList.vue              # 搜索结果列表
    │   ├── BookItem.vue              # 书籍结果项（含格式下载按钮）
    │   └── SearchPagination.vue      # 分页组件
    ├── views/
    │   ├── Home.vue                  # 首页（搜索入口）
    │   └── SearchPage.vue            # 搜索结果页
    ├── composables/
    │   └── useSearch.ts              # 搜索组合式函数
    ├── router/
    │   └── index.ts                  # 路由配置
    └── assets/
        └── styles/
            └── global.scss           # 全局样式
```

**根目录：**
```
EasyBook/
├── docker-compose.yml                # PostgreSQL + Meilisearch
├── .env.example                      # 环境变量模板
└── .gitignore
```

### 相关文档 在实施之前应该阅读这些！

- [meilisearch-python-sdk 文档](https://meilisearch-python-sdk.paulsanders.dev/) — 第三方异步/同步 SDK（本项目统一使用此包，AsyncClient 用于 API，Client 用于 ETL）
- [Meilisearch 搜索 API](https://www.meilisearch.com/docs/reference/api/search) — 分页参数 page/hitsPerPage
- [FastAPI Lifespan 文档](https://fastapi.tiangolo.com/advanced/events/) — 应用生命周期管理
- [APScheduler AsyncIOScheduler](https://apscheduler.readthedocs.io/) — 异步定时任务
- [IPFS Gateway Best Practices](https://docs.ipfs.tech/how-to/gateway-best-practices/) — 网关使用规范
- [IPFS Public Gateway Checker](https://ipfs.github.io/public-gateway-checker/) — 实时网关状态

### 要遵循的模式

**命名约定：**
- Python：snake_case（变量、函数、文件名）
- TypeScript/Vue：camelCase（变量、函数）、PascalCase（组件）
- API 路径：kebab-case（`/api/search`、`/api/download/{id}`）
- 数据库表名：复数 snake_case（`books`、`gateway_health`）

**后端分层架构：**
```
API Route (app/api/v1/*.py) → Service (app/services/*.py) → Database/External (app/database.py, Meilisearch)
```
- 路由层只做参数验证和响应格式化
- 业务逻辑在 Service 层
- 数据库操作通过 SQLAlchemy 异步 Session

**错误处理模式：**
```python
# 使用 FastAPI HTTPException，service 层抛异常，route 层捕获
from fastapi import HTTPException
raise HTTPException(status_code=404, detail="Book not found")
```

**日志模式：**
```python
import logging
logger = logging.getLogger(__name__)
# 外部 API 调用、异常处理、关键业务流程必须有日志
```

**前端 API 调用模式：**
- Axios 实例封装在 `api/request.ts`
- 搜索直接用 composable（`useSearch.ts`），不用 Pinia Store（MVP 单页面搜索，无需跨页面共享状态）
- URL 参数同步搜索状态（`/search?q=三体&page=1`）

**Meilisearch 索引配置：**
```python
# 使用 page + hitsPerPage 分页方式（需要 totalHits 和 totalPages）
# searchableAttributes 优先级：title > author
# filterable: extension, language
```

---

## 实施计划

### Phase 1：基础设施与项目骨架

**目标**：搭建开发环境，创建前后端项目框架，启动 Docker 服务

**任务：**
- Docker Compose 配置（PostgreSQL 16 + Meilisearch v1.35.0）
- 后端 FastAPI 项目初始化（uv + pyproject.toml）
- 前端 Vue3 项目初始化（pnpm + Vite + TypeScript + Naive UI）
- 基础配置管理（pydantic-settings + .env）
- 数据库连接配置（SQLAlchemy 异步 + asyncpg）
- 日志系统配置

### Phase 2：数据模型与 ETL

**目标**：定义数据模型，实现 Anna's Archive 数据导入脚本

**任务：**
- Book ORM 模型和数据库表
- ETL 导入脚本（解析 zstd 压缩的 JSONL）
- 数据清洗（格式过滤、MD5 去重、简繁体统一）
- PostgreSQL → Meilisearch 索引同步
- Meilisearch 索引配置（searchable/filterable/sortable）

### Phase 3：后端核心 API

**目标**：实现搜索、下载链接生成、健康检查 API

**任务：**
- 搜索 Service（对接 Meilisearch 异步 SDK）
- `/api/search` 搜索路由（分页 + 多格式合并）
- IPFS 网关管理 Service（健康检查 + 智能选优）
- `/api/download/{book_format_id}` 下载链接路由
- `/api/health` 健康检查路由
- APScheduler 定时任务（网关健康检查）
- CORS 配置和 API 限流（SlowAPI）

### Phase 4：前端搜索界面

**目标**：实现用户可交互的搜索和下载界面

**任务：**
- Axios 封装和 API 类型定义
- 搜索组合式函数（useSearch.ts）
- 搜索框组件（SearchBox.vue）
- 搜索结果列表和书籍项组件（BookList.vue + BookItem.vue）
- 分页组件（SearchPagination.vue）
- 首页和搜索结果页（Home.vue + SearchPage.vue）
- 路由配置（URL 参数 ↔ 搜索状态同步）
- Vite 开发代理配置（前后端联调）

---

## 逐步任务

重要：按顺序从上到下执行每个任务。每个任务都是原子的且可独立测试。

---

### 任务 1: CREATE docker-compose.yml

- **IMPLEMENT**: 在项目根目录创建 `docker-compose.yml`，包含：
  - PostgreSQL 16-alpine：端口 5432，用户 `easybook`，数据库 `easybook`，数据卷持久化，健康检查
  - Meilisearch v1.35.0：端口 7700，master key 从 .env 读取，数据卷持久化，健康检查，禁用 analytics
  - 网络 `easybook-network`
- **PATTERN**: 参考 `meilisearch_technical_notes.md` 第 380-460 行（Docker Compose 配置）和 `fastapi_best_practices.md` 第 1080-1195 行
- **GOTCHA**: Meilisearch 健康检查用 `wget` 而非 `curl`（alpine 镜像无 curl）；PostgreSQL 健康检查用 `pg_isready`
- **VALIDATE**: `docker compose up -d && docker compose ps` 确认两个容器都是 healthy 状态

### 任务 2: CREATE .env.example 和 .gitignore

- **IMPLEMENT**: 创建 `.env.example` 包含所有环境变量模板：
  ```
  # PostgreSQL
  DATABASE_URL=postgresql+asyncpg://easybook:easybook@localhost:5432/easybook
  # Meilisearch
  MEILI_URL=http://localhost:7700
  MEILI_MASTER_KEY=your-master-key-at-least-16-chars
  # IPFS
  IPFS_GATEWAYS=ipfs.io,dweb.link,gateway.pinata.cloud,ipfs.filebase.io,w3s.link,4everland.io
  # 健康检查
  HEALTH_CHECK_INTERVAL_HOURS=24
  HEALTH_CHECK_FAIL_THRESHOLD=3
  # 应用
  CORS_ORIGINS=["http://localhost:3000"]
  DEBUG=true
  LOG_LEVEL=DEBUG
  ```
  创建 `.gitignore`：忽略 `.env`、`__pycache__`、`node_modules`、`dist`、`*.pyc`、`.venv`、`meili_data`、`postgres_data`、`logs/`
- **VALIDATE**: 确认 `.env.example` 内容完整，`.gitignore` 覆盖关键文件

### 任务 3: CREATE 后端项目骨架 backend/pyproject.toml

- **IMPLEMENT**: 在 `backend/` 目录下初始化 uv 项目：
  ```toml
  [project]
  name = "easybook-backend"
  version = "0.1.0"
  description = "EasyBook 电子书聚合搜索平台后端"
  requires-python = ">=3.12"
  dependencies = [
      "fastapi[standard]>=0.115.0",
      "uvicorn[standard]>=0.30.0",
      "sqlalchemy[asyncio]>=2.0.0",
      "asyncpg>=0.29.0",
      "pydantic>=2.9.0",
      "pydantic-settings>=2.5.0",
      "alembic>=1.13.0",
      "meilisearch-python-sdk>=7.0.0",
      "psycopg2-binary>=2.9.9",
      "httpx>=0.27.0",
      "opencc-python-reimplemented>=0.1.7",
      "zstandard>=0.23.0",
      "apscheduler>=3.10.0,<4.0.0",
      "slowapi>=0.1.9",
  ]

  [project.optional-dependencies]
  dev = [
      "pytest>=8.0.0",
      "pytest-asyncio>=0.24.0",
      "ruff>=0.7.0",
  ]

  [build-system]
  requires = ["hatchling"]
  build-backend = "hatchling.build"

  [tool.hatch.build.targets.wheel]
  packages = ["app", "etl"]

  [tool.ruff]
  line-length = 100
  target-version = "py312"

  [tool.pytest.ini_options]
  asyncio_mode = "auto"
  testpaths = ["tests"]
  ```
- **IMPORTS**: 注意 `meilisearch-python-sdk`（异步 SDK）而非 `meilisearch`（官方同步 SDK）
- **GOTCHA**: `apscheduler` 锁定 3.x 版本（4.x 仍为 alpha）；`hatch.build.targets.wheel.packages` 必须包含 `app` 和 `etl` 两个包
- **VALIDATE**: `cd backend && uv sync` 成功安装所有依赖

### 任务 4: CREATE backend/app/config.py

- **IMPLEMENT**: 使用 pydantic-settings 管理配置：
  ```python
  from typing import List
  from pydantic import Field, field_validator
  from pydantic_settings import BaseSettings, SettingsConfigDict

  class Settings(BaseSettings):
      # 数据库
      DATABASE_URL: str = "postgresql+asyncpg://easybook:easybook@localhost:5432/easybook"
      # Meilisearch
      MEILI_URL: str = "http://localhost:7700"
      MEILI_MASTER_KEY: str = ""
      # IPFS 网关（逗号分隔字符串）
      IPFS_GATEWAYS: str = "ipfs.io,dweb.link,gateway.pinata.cloud,ipfs.filebase.io,w3s.link,4everland.io"
      # 健康检查配置
      HEALTH_CHECK_INTERVAL_HOURS: int = 24
      HEALTH_CHECK_FAIL_THRESHOLD: int = 3
      # CORS
      CORS_ORIGINS: List[str] = ["http://localhost:3000"]
      # 应用配置
      DEBUG: bool = False
      LOG_LEVEL: str = "INFO"
      LOG_FILE: str = "logs/app.log"

      @field_validator("CORS_ORIGINS", mode="before")
      @classmethod
      def parse_cors(cls, v):
          if isinstance(v, str):
              import json
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
          env_file="../.env",
          env_file_encoding="utf-8",
          case_sensitive=True,
          extra="ignore",
      )

  settings = Settings()
  ```
- **PATTERN**: 参考 `fastapi_best_practices.md` 第 480-562 行
- **GOTCHA**: `env_file` 路径是相对于运行目录的，如果从 `backend/` 运行则 `.env` 在上一级；IPFS_GATEWAYS 存为逗号分隔字符串比 JSON 数组更方便命令行设置
- **VALIDATE**: `uv run python -c "from app.config import settings; print(settings.MEILI_URL)"`

### 任务 5: CREATE backend/app/core/logging_config.py

- **IMPLEMENT**: 日志配置模块，在 lifespan 中调用一次：
  ```python
  import logging
  import sys
  from pathlib import Path
  from app.config import settings

  def setup_logging() -> None:
      log_file = Path(settings.LOG_FILE)
      log_file.parent.mkdir(parents=True, exist_ok=True)

      log_format = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"

      logging.basicConfig(
          level=getattr(logging, settings.LOG_LEVEL.upper()),
          format=log_format,
          datefmt="%Y-%m-%d %H:%M:%S",
          handlers=[
              logging.StreamHandler(sys.stdout),
              logging.FileHandler(log_file, encoding="utf-8"),
          ],
      )

      # 降低第三方库日志级别
      logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
      logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
      logging.getLogger("httpx").setLevel(logging.WARNING)
      logging.getLogger("apscheduler").setLevel(logging.INFO)
  ```
- **PATTERN**: 参考 `fastapi_best_practices.md` 第 644-698 行
- **VALIDATE**: 导入模块无报错

### 任务 6: CREATE backend/app/database.py

- **IMPLEMENT**: SQLAlchemy 2.0 异步引擎和会话管理：
  ```python
  import logging
  from typing import AsyncGenerator
  from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
  from sqlalchemy.orm import DeclarativeBase
  from app.config import settings

  logger = logging.getLogger(__name__)

  class Base(DeclarativeBase):
      pass

  engine: AsyncEngine | None = None
  async_session_maker: async_sessionmaker[AsyncSession] | None = None

  async def get_db() -> AsyncGenerator[AsyncSession, None]:
      if async_session_maker is None:
          raise RuntimeError("Database not initialized")
      async with async_session_maker() as session:
          try:
              yield session
              await session.commit()
          except Exception:
              await session.rollback()
              raise

  async def init_db() -> None:
      global engine, async_session_maker
      engine = create_async_engine(
          settings.DATABASE_URL,
          echo=settings.DEBUG,
          pool_size=10,
          max_overflow=20,
          pool_recycle=3600,
          pool_pre_ping=True,
      )
      async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
      logger.info("Database connection pool initialized")

  async def close_db() -> None:
      if engine:
          await engine.dispose()
          logger.info("Database connection pool disposed")
  ```
- **PATTERN**: 参考 `fastapi_best_practices.md` 第 166-263 行
- **VALIDATE**: 导入模块无报错

### 任务 7: CREATE backend/app/models/book.py

- **IMPLEMENT**: Book ORM 模型（对应 `books` 表）：
  ```python
  from datetime import datetime
  from typing import Optional
  from sqlalchemy import String, BigInteger, DateTime, Boolean, Index, func, text
  from sqlalchemy.orm import Mapped, mapped_column
  from app.database import Base

  class Book(Base):
      __tablename__ = "books"

      id: Mapped[int] = mapped_column(primary_key=True, index=True)
      title: Mapped[str] = mapped_column(String(512), nullable=False)
      author: Mapped[Optional[str]] = mapped_column(String(512))
      extension: Mapped[str] = mapped_column(String(10), nullable=False)  # epub/pdf/mobi/azw3
      filesize: Mapped[Optional[int]] = mapped_column(BigInteger)
      language: Mapped[Optional[str]] = mapped_column(String(20))
      md5: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
      ipfs_cid: Mapped[Optional[str]] = mapped_column(String(255))
      year: Mapped[Optional[str]] = mapped_column(String(10))
      publisher: Mapped[Optional[str]] = mapped_column(String(255))
      created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

      __table_args__ = (
          Index("idx_books_extension", "extension"),
          Index("idx_books_language", "language"),
      )
  ```
- **PATTERN**: 参考 `ebook_system_design.md` 第 138-154 行（表结构）和 `fastapi_best_practices.md` 第 266-296 行（ORM 模型）
- **GOTCHA**: `md5` 字段 unique 约束用于去重；`extension` 和 `language` 建索引用于过滤查询；`filesize` 用 BigInteger（部分大文件超过 2GB）

### 任务 8: CREATE backend/app/models/gateway_health.py

- **IMPLEMENT**: IPFS 网关健康状态模型：
  ```python
  from datetime import datetime
  from typing import Optional
  from sqlalchemy import String, Float, Integer, DateTime, Boolean, func
  from sqlalchemy.orm import Mapped, mapped_column
  from app.database import Base

  class GatewayHealth(Base):
      __tablename__ = "gateway_health"

      id: Mapped[int] = mapped_column(primary_key=True, index=True)
      gateway_url: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
      available: Mapped[bool] = mapped_column(Boolean, default=False)
      response_time_ms: Mapped[Optional[float]] = mapped_column(Float)
      consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
      last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
      updated_at: Mapped[datetime] = mapped_column(
          DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
      )
  ```
- **PATTERN**: 参考 PRD 第 219-221 行（连续失败阈值机制）和 `rpiv/ipfs_gateway_research.md` 第 460-517 行（熔断器模式）

### 任务 9: CREATE backend/app/schemas/search.py

- **IMPLEMENT**: Pydantic v2 请求/响应模型：
  ```python
  from pydantic import BaseModel, Field, ConfigDict

  class SearchRequest(BaseModel):
      q: str = Field(..., min_length=1, max_length=200, description="搜索关键词")
      page: int = Field(1, ge=1, description="页码")
      page_size: int = Field(20, ge=1, le=100, description="每页条数")

  class BookFormat(BaseModel):
      extension: str
      filesize: int | None = None
      download_url: str
      model_config = ConfigDict(from_attributes=True)

  class BookResult(BaseModel):
      id: str  # 使用 MD5 作为唯一标识
      title: str
      author: str | None = None
      formats: list[BookFormat]
      model_config = ConfigDict(from_attributes=True)

  class SearchResponse(BaseModel):
      total: int
      page: int
      page_size: int
      results: list[BookResult]

  class DownloadResponse(BaseModel):
      download_url: str
      gateway: str
      alternatives: list[str]

  class HealthResponse(BaseModel):
      status: str
      database: str
      meilisearch: str
      last_health_check: str | None = None
  ```
- **PATTERN**: 参考 PRD 第 292-336 行（API 响应格式）和 `fastapi_best_practices.md` 第 330-409 行（Pydantic v2 模型分离）
- **GOTCHA**: `BookResult.id` 用 MD5 哈希作为公开 ID（不暴露数据库自增 ID）；`formats` 是同一本书的多个格式列表（同书名+作者合并）

### 任务 10: CREATE backend/app/services/search_service.py

- **IMPLEMENT**: Meilisearch 搜索业务逻辑：
  ```python
  import logging
  from meilisearch_python_sdk import AsyncClient
  from app.config import settings

  logger = logging.getLogger(__name__)

  class SearchService:
      def __init__(self):
          self.client: AsyncClient | None = None
          self.index_name = "books"

      async def init(self):
          self.client = AsyncClient(settings.MEILI_URL, settings.MEILI_MASTER_KEY)
          logger.info("Meilisearch client initialized")

      async def close(self):
          if self.client:
              await self.client.aclose()

      async def search(self, query: str, page: int = 1, page_size: int = 20) -> dict:
          """搜索书籍，返回 Meilisearch 原始结果"""
          index = self.client.index(self.index_name)
          result = await index.search(
              query,
              page=page,
              hits_per_page=page_size,
          )
          return {
              "hits": result.hits,
              "total_hits": result.total_hits,
              "page": page,
              "page_size": page_size,
          }

      async def configure_index(self):
          """配置 Meilisearch 索引属性（初始化时调用一次）"""
          index = self.client.index(self.index_name)
          await index.update_searchable_attributes(["title", "author"])
          await index.update_filterable_attributes(["extension", "language"])
          await index.update_sortable_attributes(["filesize"])
          logger.info("Meilisearch index configured")

  search_service = SearchService()
  ```
- **PATTERN**: 参考 `meilisearch_technical_notes.md` 第 56-110 行（SDK 用法）和第 127-190 行（索引配置）
- **IMPORTS**: 使用 `meilisearch_python_sdk.AsyncClient`（第三方异步 SDK），不是 `meilisearch.Client`（官方同步 SDK）
- **GOTCHA**: 使用 `page` + `hits_per_page` 分页方式时，Meilisearch 返回 `totalHits`（SDK 中映射为 `total_hits`），不是 `estimatedTotalHits`（`estimated_total_hits`）。后者仅在 `offset` + `limit` 分页时出现

### 任务 11: CREATE backend/app/services/gateway_service.py

- **IMPLEMENT**: IPFS 网关管理和健康检查 Service：
  - 使用 httpx AsyncClient 发送 HEAD 请求检测网关可用性
  - 测试 CID 使用 IPFS 白皮书：`QmR7GSQM93Cx5eAg6a6yRzNde1FQv7uL6X1o4k7zrJa3LX`
  - `check_all_gateways()`: 并发检测所有网关，更新数据库 `gateway_health` 表
  - `get_best_gateway()`: 返回响应时间最快的可用网关
  - `build_download_url(cid, filename)`: 拼接完整下载 URL
  - `get_alternatives(cid, filename, exclude_gateway)`: 返回备用网关 URL 列表
  - 连续失败达到 `HEALTH_CHECK_FAIL_THRESHOLD` 次后标记为不可用
- **PATTERN**: 参考 `rpiv/ipfs_gateway_research.md` 第 250-398 行（完整的 IPFSGatewayHealthChecker 类）
- **IMPORTS**: `httpx`, `asyncio`, `sqlalchemy.ext.asyncio.AsyncSession`
- **GOTCHA**:
  - HEAD 请求超时设置：connect=5s, read=10s
  - 状态码 200/301/302/307/308 视为可用
  - cloudflare-ipfs.com 已退役，不要加入网关列表
  - 需要处理 429 限流响应
  - **DB session 自管理**：`check_all_gateways()` 会在 APScheduler 调度中运行，此时没有 FastAPI 的依赖注入上下文。Service 必须自行创建 SQLAlchemy AsyncSession（从 `database.async_session_maker` 获取），不能依赖 `Depends(get_db)`

### 任务 12: CREATE backend/app/services/scheduler_service.py

- **IMPLEMENT**: APScheduler 定时任务管理：
  ```python
  import logging
  from apscheduler.schedulers.asyncio import AsyncIOScheduler
  from app.config import settings

  logger = logging.getLogger(__name__)

  scheduler = AsyncIOScheduler(timezone="UTC")

  def setup_scheduler():
      from app.services.gateway_service import gateway_service
      scheduler.add_job(
          gateway_service.check_all_gateways,
          "interval",
          hours=settings.HEALTH_CHECK_INTERVAL_HOURS,
          id="ipfs_health_check",
          replace_existing=True,
      )
      logger.info(f"Scheduler configured: health check every {settings.HEALTH_CHECK_INTERVAL_HOURS}h")
  ```
- **PATTERN**: 参考 APScheduler 3.x AsyncIOScheduler 文档
- **GOTCHA**: `setup_scheduler()` 在 lifespan 中调用，不在模块顶层导入 gateway_service（避免循环导入）；使用 `replace_existing=True` 防止重复添加 job

### 任务 13: CREATE backend/app/api/v1/search.py

- **IMPLEMENT**: 搜索路由：
  ```python
  @router.get("/search", response_model=SearchResponse)
  async def search_books(
      q: str = Query(..., min_length=1, max_length=200),
      page: int = Query(1, ge=1),
      page_size: int = Query(20, ge=1, le=100),
  ):
  ```
  - 调用 `search_service.search(q, page, page_size)`
  - 将 Meilisearch 返回的 hits 按 title+author 分组合并格式
  - 为每个格式调用 `gateway_service.build_download_url()` 生成下载链接
  - 返回 `SearchResponse` 格式
- **PATTERN**: 参考 PRD 第 280-317 行（API 规范）
- **GOTCHA**: 多格式合并逻辑——Meilisearch 中每条记录是一个 format（一个 MD5），同一本书可能有多条记录。合并键为 `(title.lower().strip(), author.lower().strip())`；如果 `ipfs_cid` 为空，该格式的 `download_url` 设为空字符串 `""`（前端根据此字段决定是否展示下载按钮）

### 任务 14: CREATE backend/app/api/v1/download.py

- **IMPLEMENT**: 下载链接路由：
  ```python
  @router.get("/download/{md5}")
  async def get_download_url(md5: str, db: AsyncSession = Depends(get_db)):
  ```
  - 从数据库查询 `md5` 对应的 Book 记录
  - 获取 `ipfs_cid`，如果为空返回 404
  - 调用 `gateway_service.get_best_gateway()` 获取最优网关
  - 调用 `gateway_service.get_alternatives()` 获取备用链接
  - 返回 `DownloadResponse`
- **PATTERN**: 参考 PRD 第 319-336 行

### 任务 15: CREATE backend/app/api/v1/health.py

- **IMPLEMENT**: 健康检查路由：
  - `GET /api/health` 返回 `HealthResponse`
  - 检查 PostgreSQL 连接（`SELECT 1`）
  - 检查 Meilisearch 连接（`client.health()`）
  - 返回最近一次网关健康检查时间
- **PATTERN**: 参考 `fastapi_best_practices.md` 第 914-1014 行

### 任务 16: CREATE backend/app/api/v1/router.py

- **IMPLEMENT**: 汇总所有 v1 路由：
  ```python
  from fastapi import APIRouter
  from app.api.v1 import search, download, health

  api_router = APIRouter()
  api_router.include_router(search.router, tags=["Search"])
  api_router.include_router(download.router, tags=["Download"])
  api_router.include_router(health.router, tags=["Health"])
  ```

### 任务 17: CREATE backend/app/main.py

- **IMPLEMENT**: FastAPI 应用入口，完整的 lifespan 管理：
  ```python
  from contextlib import asynccontextmanager
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # 启动
      setup_logging()
      await init_db()
      await search_service.init()
      await search_service.configure_index()
      setup_scheduler()
      scheduler.start()
      # 首次启动时执行一次网关健康检查
      asyncio.create_task(gateway_service.check_all_gateways())
      yield
      # 关闭
      scheduler.shutdown(wait=True)
      await search_service.close()
      await close_db()

  app = FastAPI(title="EasyBook API", lifespan=lifespan)
  # CORS
  app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, ...)
  # API 限流（使用内存存储，不依赖 Redis）
  from slowapi import Limiter
  from slowapi.util import get_remote_address
  limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
  app.state.limiter = limiter
  # 路由
  app.include_router(api_router, prefix="/api")
  ```
- **PATTERN**: 参考 `fastapi_best_practices.md` 第 1290-1371 行
- **GOTCHA**: `api_router` 挂载在 `/api` 前缀下（不是 `/api/v1`，因为 MVP 阶段不需要版本管理）；首次启动异步执行一次网关检查（`create_task` 不阻塞启动）；SlowAPI 使用 `memory://` 存储（MVP 不依赖 Redis），后续分布式部署再切换 Redis

### 任务 18: CREATE backend/etl/import_annas.py

- **IMPLEMENT**: Anna's Archive JSONL 数据导入脚本：
  - 命令行入口：`uv run python -m etl.import_annas <path_to_jsonl_zst>`
  - 使用 `zstandard` 流式解压 `.jsonl.zst` 文件（`max_window_size=2**31`）
  - **自适应 JSONL 解析**：Anna's Archive JSONL 有两种结构，脚本需自动识别：
    - **嵌套结构**：`{"aacid": "...", "metadata": {"title": "...", "author": "...", ...}}`（字段在 `metadata` 键下）
    - **扁平结构**：`{"title": "...", "author": "...", ...}`（字段直接在顶层）
    - 检测逻辑：`record.get("metadata", record)` — 如有 `metadata` 键则从中取字段，否则直接从 record 取
  - 逐行解析 JSON，提取字段：
    - `title` → `book.title`
    - `author` → `book.author`
    - `extension` → `book.extension`（仅保留 epub/pdf/mobi/azw3）
    - `filesize_reported` → `book.filesize`
    - `md5_reported` 或 `md5` → `book.md5`（强制小写，两个字段名都需兼容）
    - `ipfs_cid` → `book.ipfs_cid`（可能为空，无 CID 的记录仍然导入）
    - `language` → `book.language`
    - `year` → `book.year`（正则提取四位数字）
    - `publisher` → `book.publisher`
  - 数据清洗：
    - 过滤 `extension` 不在 `{epub, pdf, mobi, azw3}` 的记录
    - **仅导入中文和英文记录**：`language` 字段包含 `zh`/`chi`/`Chinese` 或 `en`/`eng`/`English`（大小写不敏感），空值也保留（可能是未标注语言的中文书）
    - 过滤 `md5` 为空的记录
    - 过滤 `title` 为空的记录
    - `md5` 强制小写
    - 使用 OpenCC 将繁体中文 title/author 转为简体（`t2s.json` 配置）
  - **使用同步 SQLAlchemy engine**（`settings.sync_database_url`，psycopg2 驱动）：
    ```python
    from sqlalchemy import create_engine
    from app.config import settings
    sync_engine = create_engine(settings.sync_database_url)
    ```
  - 批量写入 PostgreSQL（每批 1000 条，使用 `ON CONFLICT (md5) DO NOTHING` 去重）
  - 进度日志（每 10000 条输出一次）
  - 支持 `--dry-run` 参数（只解析不写入，用于验证数据格式）
- **PATTERN**: 参考 `anna_archive_datasets_research.md` 第 254-292 行（流式解压）和第 296-332 行（字段处理）
- **IMPORTS**: `zstandard`, `json`, `sqlalchemy`（同步）, `opencc`, `argparse`, `re`
- **GOTCHA**:
  - zstd 解压需要 `max_window_size=2**31`（某些文件使用超大窗口）
  - 流式按行读取，不要一次性加载到内存（文件可能数十 GB）
  - `md5` 字段在不同数据源中可能叫 `md5_reported` 或 `md5`，提取逻辑：`data.get("md5_reported") or data.get("md5", "")`
  - OpenCC 转换：`import opencc; converter = opencc.OpenCC('t2s.json')`
  - 使用同步 SQLAlchemy engine + psycopg2 驱动（`settings.sync_database_url`），ETL 脚本不需要异步
  - 语言判断逻辑：`lang_lower = (language or "").lower(); is_zh_en = any(k in lang_lower for k in ["zh", "chi", "chinese", "en", "eng", "english"]) or not language`
- **VALIDATE**: `uv run python -m etl.import_annas sample.jsonl.zst --dry-run` 输出解析统计

### 任务 19: CREATE backend/etl/sync_meilisearch.py

- **IMPLEMENT**: PostgreSQL → Meilisearch 索引同步脚本：
  - 命令行入口：`uv run python -m etl.sync_meilisearch`
  - 从 PostgreSQL 分批读取 books 数据（每批 5000 条）
  - 转换为 Meilisearch 文档格式：
    ```python
    {
        "id": book.md5,  # 使用 MD5 作为文档 ID
        "title": book.title,
        "author": book.author or "",
        "extension": book.extension,
        "filesize": book.filesize or 0,
        "language": book.language or "",
        "ipfs_cid": book.ipfs_cid or "",
        "year": book.year or "",
        "publisher": book.publisher or "",
    }
    ```
  - 使用 `meilisearch_python_sdk.Client`（同步客户端）的 `index.add_documents()` 批量上传：
    ```python
    from meilisearch_python_sdk import Client
    client = Client(settings.MEILI_URL, settings.MEILI_MASTER_KEY)
    ```
  - 上传前先配置索引属性（searchableAttributes、filterableAttributes、sortableAttributes）
  - 进度日志
- **PATTERN**: 参考 `meilisearch_technical_notes.md` 第 127-190 行（索引配置）和第 367-374 行（分批上传）
- **IMPORTS**: `meilisearch_python_sdk.Client`（同一个第三方包的同步客户端），不是 `meilisearch.Client`（官方同步 SDK，本项目未安装）
- **GOTCHA**: `meilisearch-python-sdk` 同时提供 `AsyncClient` 和 `Client`，后端 API 用前者，ETL 用后者，无需安装额外包；批量上传每批 5000 条（保持在 100MB payload 限制内）；Meilisearch 的 `add_documents` 是幂等的（同 id 覆盖）；ETL 也使用同步 SQLAlchemy engine（`settings.sync_database_url`）读取数据
- **VALIDATE**: `uv run python -m etl.sync_meilisearch` 后通过 Meilisearch Dashboard（`http://localhost:7700`）搜索验证

### 任务 20: CREATE 数据库建表脚本

- **IMPLEMENT**: 创建 `backend/etl/create_tables.py`：
  ```python
  """创建数据库表（开发环境快速建表，不使用 Alembic 迁移）"""
  import asyncio
  from sqlalchemy.ext.asyncio import create_async_engine
  from app.database import Base
  from app.config import settings
  from app.models.book import Book  # noqa: F401 - 确保模型注册到 Base.metadata
  from app.models.gateway_health import GatewayHealth  # noqa: F401

  async def create_tables():
      engine = create_async_engine(settings.DATABASE_URL)
      async with engine.begin() as conn:
          await conn.run_sync(Base.metadata.create_all)
      await engine.dispose()
      print("Tables created successfully")

  if __name__ == "__main__":
      asyncio.run(create_tables())
  ```
- **GOTCHA**: MVP 阶段用 `create_all` 快速建表，不引入 Alembic 迁移（后续迭代再加）
- **VALIDATE**: `uv run python -m etl.create_tables` 后用 `psql` 确认 `books` 和 `gateway_health` 表存在

### 任务 21: CREATE 前端项目 frontend/

- **IMPLEMENT**: 使用 pnpm + Vite + Vue3 + TypeScript 初始化项目：
  ```bash
  cd frontend
  pnpm create vite . --template vue-ts
  pnpm install
  pnpm add naive-ui axios vue-router@4 @vicons/ionicons5
  pnpm add -D sass unplugin-auto-import unplugin-vue-components
  ```
  配置 `vite.config.ts`：
  - 自动导入 Vue Composition API 和 Naive UI 组件（AutoImport imports 只含 `'vue'` 和 `'vue-router'`，不含 `'pinia'`）
  - 路径别名 `@` → `src/`
  - 开发代理 `/api` → `http://localhost:8000`
  - 构建优化：手动分块 naive-ui 和 vue-vendor（`'vue-vendor': ['vue', 'vue-router']`，不含 pinia）
- **PATTERN**: 参考 `vue3_vite_search_best_practices.md` 第 1-120 行（完整配置）
- **GOTCHA**: Vite proxy rewrite 需要把 `/api` 前缀保留（后端路由也是 `/api` 前缀），所以 rewrite 规则不要去掉 `/api`：
  ```typescript
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      // 不需要 rewrite，直接透传 /api 路径
    }
  }
  ```
- **VALIDATE**: `pnpm dev` 能正常启动开发服务器

### 任务 22: CREATE 前端类型定义和 API 封装

- **IMPLEMENT**:
  - `src/types/search.ts`: 与后端 `SearchResponse` 对应的 TypeScript 类型
    ```typescript
    export interface BookFormat {
      extension: string
      filesize: number | null
      download_url: string
    }

    export interface BookResult {
      id: string
      title: string
      author: string | null
      formats: BookFormat[]
    }

    export interface SearchResponse {
      total: number
      page: number
      page_size: number
      results: BookResult[]
    }
    ```
  - `src/api/request.ts`: 轻量 Axios 封装：
    ```typescript
    import axios from 'axios'

    const http = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
      timeout: 10000,
    })

    // 响应拦截器：直接返回 response.data（FastAPI 直接返回 Pydantic 模型，无需解包）
    http.interceptors.response.use(
      (response) => response.data,
      (error) => Promise.reject(error),
    )

    export default http
    ```
  - `src/api/modules/search.ts`: 搜索 API 调用
    ```typescript
    import http from '../request'
    import type { SearchResponse } from '@/types/search'

    export function searchBooks(params: { q: string; page?: number; page_size?: number }) {
      return http.get<any, SearchResponse>('/search', { params })
    }
    ```
- **PATTERN**: 参考 `vue3_vite_search_best_practices.md` 第 236-502 行，但需简化
- **GOTCHA**:
  - MVP 阶段不需要 token/认证相关的拦截器逻辑
  - **不要使用 `{ code, data, message, success }` 响应包装模式**——FastAPI 直接返回 Pydantic 模型 JSON，Axios 拦截器直接返回 `response.data`
  - `http.get<any, SearchResponse>` 中第二个泛型参数是拦截器处理后的返回类型
  - `baseURL` 已含 `/api` 前缀，API 调用路径无需重复（用 `/search` 不是 `/api/search`）

### 任务 23: CREATE 前端搜索组合式函数 src/composables/useSearch.ts

- **IMPLEMENT**: 搜索状态管理（不用 Pinia，用 composable 即可）：
  ```typescript
  export function useSearch() {
    const query = ref('')
    const results = ref<BookResult[]>([])
    const total = ref(0)
    const page = ref(1)
    const pageSize = ref(20)
    const loading = ref(false)
    const error = ref<string | null>(null)
    const hasSearched = ref(false)

    const search = async () => { /* 调用 searchBooks API */ }
    const changePage = (newPage: number) => { /* 更新 page 并搜索 */ }

    return { query, results, total, page, pageSize, loading, error, hasSearched, search, changePage }
  }
  ```
- **PATTERN**: 参考 `vue3_vite_search_best_practices.md` 第 1182-1248 行

### 任务 24: CREATE 前端组件

- **IMPLEMENT**: 创建以下组件：
  1. `SearchBox.vue` — 搜索框（n-input + 搜索按钮，回车触发搜索）
  2. `BookItem.vue` — 书籍结果项：
     - 显示书名、作者
     - 格式标签（EPUB/PDF/MOBI/AZW3），每个格式是可点击的下载按钮
     - 文件大小显示（自动转换 KB/MB/GB）
     - 点击格式按钮在新窗口打开 download_url
  3. `BookList.vue` — 搜索结果列表（v-for BookItem，含 loading/empty 状态）
  4. `SearchPagination.vue` — 分页（使用 Naive UI n-pagination）
- **CID 缺失处理**：`BookItem.vue` 中，如果某个格式的 `download_url` 为空字符串，则该格式按钮显示为灰色禁用状态（tooltip 提示"暂无下载链接"），而非隐藏。这样用户知道该格式存在但暂不可下载
- **PATTERN**: 参考 `vue3_vite_search_best_practices.md` 第 534-938 行（组件模板），但需要适配电子书场景：
  - `BookItem` 不同于通用 `SearchItem`：没有 content/url/timestamp 字段，增加 formats 下载按钮
  - 格式标签使用不同颜色区分（epub=绿色, pdf=红色, mobi=蓝色, azw3=橙色）
- **GOTCHA**: 文件大小格式化工具函数 `formatFileSize(bytes)`：`< 1024 → B`，`< 1MB → KB`，`< 1GB → MB`，否则 `GB`

### 任务 25: CREATE 前端页面和路由

- **IMPLEMENT**:
  1. `Home.vue` — 首页：居中大搜索框，简洁品牌标识 "EasyBook"，无搜索历史（MVP 不做）
  2. `SearchPage.vue` — 搜索结果页：顶部搜索框 + 结果列表 + 分页，URL 参数同步
  3. `router/index.ts` — 路由配置：`/` → Home，`/search?q=xxx&page=1` → SearchPage
  4. `App.vue` + `AppContent.vue` — Naive UI ConfigProvider 包装
  5. `main.ts` — 入口文件
- **PATTERN**: 参考 `vue3_vite_search_best_practices.md` 第 1254-1591 行
- **GOTCHA**: SearchPage 从 URL query 恢复搜索状态（`route.query.q`），确保刷新页面能保持搜索结果；首页搜索后 `router.push({ path: '/search', query: { q } })`
- **VALIDATE**: `pnpm dev` 启动后，首页可见搜索框，输入关键词跳转到搜索页

### 任务 26: CREATE 前端全局样式和 env 配置

- **IMPLEMENT**:
  - `src/assets/styles/global.scss` — 重置样式 + CSS 变量 + 滚动条样式
  - `src/env.d.ts` — TypeScript 环境类型声明（ImportMetaEnv + Naive UI window 类型）
  - `.env` — `VITE_API_BASE_URL=/api`
  - `.env.production` — `VITE_API_BASE_URL=https://api.example.com`（占位）
- **PATTERN**: 参考 `vue3_vite_search_best_practices.md` 第 1596-1857 行

### 任务 27: 前后端联调测试

- **IMPLEMENT**: 确保完整的搜索 → 下载流程：
  1. 启动 Docker 服务（PostgreSQL + Meilisearch）
  2. 运行建表脚本
  3. 准备测试数据（手动插入几条 books 记录或使用小样本 JSONL）
  4. 运行 Meilisearch 同步脚本
  5. 启动后端：`cd backend && uv run uvicorn app.main:app --reload --port 8000`
  6. 启动前端：`cd frontend && pnpm dev`
  7. 在浏览器中测试搜索和下载
- **VALIDATE**:
  - `curl "http://localhost:8000/api/search?q=python"` 返回搜索结果
  - `curl "http://localhost:8000/api/health"` 返回健康状态
  - 浏览器中搜索关键词能看到结果，点击格式按钮能打开 IPFS 下载链接
  - 翻页正常工作

---

## 测试策略

### 单元测试

使用 pytest + pytest-asyncio：

1. **search_service 测试** — mock Meilisearch client，验证搜索参数传递和结果格式化
2. **gateway_service 测试** — mock httpx，验证 HEAD 请求逻辑、状态判断、连续失败计数
3. **多格式合并测试** — 验证同 title+author 的多条记录正确合并为 formats 列表
4. **数据清洗测试** — 验证 ETL 清洗规则（格式过滤、MD5 去重、简繁体转换）

### 集成测试

1. **搜索 API 端到端** — 启动 FastAPI TestClient + 真实 Meilisearch 实例，测试搜索流程
2. **健康检查** — 验证 `/api/health` 在所有服务正常/异常时的响应

### 边缘情况

- 搜索空关键词 → 400 错误
- 搜索无结果 → 返回 `total: 0, results: []`
- 下载不存在的 MD5 → 404
- 下载无 IPFS CID 的书籍 → 返回适当错误
- 所有 IPFS 网关不可用 → 下载接口返回 503
- Meilisearch 不可用 → 搜索返回 503
- 极长关键词（200 字符）→ 正常处理
- page_size 超过 100 → 参数验证拒绝

---

## 验证命令

执行每个命令以确保零回归和 100% 功能正确性。

### 级别 1：语法和样式

```bash
# 后端代码检查
cd backend && uv run ruff check app/ etl/

# 前端类型检查
cd frontend && pnpm run type-check
```

### 级别 2：单元测试

```bash
cd backend && uv run pytest tests/ -v
```

### 级别 3：服务启动验证

```bash
# Docker 服务
docker compose up -d && docker compose ps

# 后端启动
cd backend && uv run uvicorn app.main:app --port 8000 &

# 前端构建
cd frontend && pnpm build
```

### 级别 4：手动验证

```bash
# 搜索 API
curl "http://localhost:8000/api/search?q=python&page=1&page_size=5"

# 健康检查
curl "http://localhost:8000/api/health"

# 下载链接（替换实际 MD5）
curl "http://localhost:8000/api/download/<actual_md5>"

# 前端浏览器测试
# 打开 http://localhost:3000，执行搜索 → 查看结果 → 点击下载
```

---

## 验收标准

- [ ] Docker Compose 一键启动 PostgreSQL + Meilisearch
- [ ] ETL 脚本能解析 Anna's Archive JSONL.zst 文件并导入数据库
- [ ] ETL 正确过滤非电子书格式，基于 MD5 去重，简繁体统一
- [ ] PostgreSQL → Meilisearch 索引同步成功
- [ ] `/api/search?q=xxx` 返回正确的分页搜索结果（< 500ms）
- [ ] 搜索支持中文分词和模糊匹配
- [ ] 同一本书多格式正确合并展示
- [ ] `/api/download/{md5}` 返回可用的 IPFS 下载链接
- [ ] 下载链接使用最优可用网关
- [ ] IPFS 网关健康检查定时执行（可配置间隔）
- [ ] 连续失败阈值机制正确标记不可用网关
- [ ] `/api/health` 返回系统健康状态
- [ ] Vue3 前端搜索界面可正常使用
- [ ] 首页输入关键词 → 搜索结果页 → 点击下载 完整流程畅通
- [ ] URL 参数与搜索状态同步（刷新不丢失搜索结果）
- [ ] 搜索无结果时展示友好提示
- [ ] 后端有基本的错误处理和日志记录
- [ ] 代码通过 ruff 检查，无 lint 错误
- [ ] 无用户注册/登录功能（MVP 范围外）

---

## 完成检查清单

- [ ] 所有 27 个任务按顺序完成
- [ ] 每个任务验证立即通过
- [ ] 所有验证命令成功执行
- [ ] 完整测试套件通过（单元 + 集成）
- [ ] 无代码检查或类型检查错误
- [ ] 手动测试确认功能有效
- [ ] 所有验收标准均满足
- [ ] 代码已审查质量和可维护性

---

## 备注

### 设计决策

1. **异步 vs 同步 Meilisearch SDK**：统一使用 `meilisearch-python-sdk` 一个包。后端 API 用 `AsyncClient`（异步），ETL 脚本用 `Client`（同步）。不安装官方 `meilisearch` 包，避免依赖混乱。

2. **APScheduler 3.x vs 4.x**：选择 3.x 稳定版。4.x 仍为 alpha（v4.0.0a6），不适合生产使用。

3. **Pinia vs Composable**：前端用 composable（`useSearch.ts`）而非 Pinia Store。原因：MVP 只有搜索一个核心功能，搜索状态无需跨页面共享，composable 更轻量。

4. **不使用 Alembic 迁移**：MVP 阶段用 `create_all` 快速建表。后续迭代再引入 Alembic。

5. **不使用 Redis**：MVP 阶段不配置 SlowAPI 的 Redis 后端，使用内存存储即可。后续需要分布式部署时再引入。

6. **IPFS CID 可能为空**：Anna's Archive 团队已放弃 IPFS 主推 Torrent，大量记录可能无 CID。ETL 仍导入所有有 MD5 的记录（含无 CID 的），搜索结果中无 CID 的格式展示灰色禁用下载按钮（tooltip 提示"暂无下载链接"）。

7. **cloudflare-ipfs.com 已退役**：2024年8月14日后停止服务，网关列表中不包含此网关。

### 技术风险

1. **Anna's Archive 数据文件获取**：Dumps 文件通过 BitTorrent 下载，可能需要较长时间。建议先用小样本开发，大文件异步下载。

2. **IPFS CID 覆盖率**：如果大部分记录无 CID，下载功能的可用性会受限。可在后续迭代中增加 LibGen 直连作为备用下载源。

3. **Meilisearch 中文搜索效果**：Jieba 分词可能对书名分词不够精确。可在后续通过自定义字典优化。

### 信心分数：9/10

**理由**：
- 所有技术选型已通过研究验证，无重大不确定性
- 研究文档极为详尽，包含完整的代码示例和配置模板
- 12 处技术问题已在审查中发现并修正（SDK 导入、分页字段、DB session 管理、Vite 代理、Axios 封装等）
- 4 项产品决策已确认（CID 策略：全部导入；语言过滤：仅中英文；JSONL 格式：自适应解析；PRD 更新：移除退役网关）
- 前后端模式清晰，有完整的参考代码
- 剩余风险：实际 Dumps 数据可能有未预见的边界情况，ETL 需在实际数据上验证
