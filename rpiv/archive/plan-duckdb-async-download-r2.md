---
description: "功能实施计划: DuckDB 轻量搜索 + 异步代理下载 + R2 中转"
status: archived
created_at: 2026-02-08T23:30:00
updated_at: 2026-02-09T17:00:00
archived_at: 2026-02-09T17:00:00
superseded_by: rpiv/plans/plan-duckdb-search-migration.md
related_files:
  - rpiv/requirements/prd-download-source-optimization.md
supersede_reason: "下载链路验证结论：服务端代理下载不可行。范围缩减为仅 DuckDB 搜索迁移，新计划见 superseded_by。"
---

# 功能：DuckDB 轻量搜索 + 异步代理下载 + R2 中转

以下计划应该是完整的，但在开始实施之前，验证文档和代码库模式以及任务合理性非常重要。

特别注意现有工具、类型和模型的命名。从正确的文件导入等。

## 功能描述

EasyBook 架构迁移：用 DuckDB + Parquet 替代 Meilisearch 做搜索引擎，用后端代理下载 + Cloudflare R2 中转替代前端跳转外站方案，让中国大陆用户在 EasyBook 内完成搜索和下载的完整闭环。

## 用户故事

作为中国大陆的电子书读者，
我想要在 EasyBook 内搜索电子书后直接点击下载，
以便无需翻墙即可获取电子书文件。

## 问题陈述

当前架构存在两个根本性问题：
1. 下载方案无效 — 前端跳转外站（LibGen/Anna's Archive）对中国大陆用户完全无效，站点被墙
2. 搜索引擎过重 — Meilisearch 在 Railway Hobby Plan 上内存和存储需求过高

## 解决方案陈述

- **DuckDB + Parquet** 替代 Meilisearch（零常驻进程，Parquet 文件查询）
- **后端代理下载** 替代前端跳转（服务器代用户从 LibGen 下载）
- **Cloudflare R2** 作为中转存储（出口流量免费，预签名链接交付，7 天自动清理）
- **SQLite** 作为轻量任务队列（并发极低，无需 Redis）
- 移除 PostgreSQL 和 Meilisearch 生产依赖

## 功能元数据

**功能类型**：重构 + 新功能
**估计复杂度**：高
**主要受影响的系统**：后端搜索服务、后端 API、前端下载交互、部署架构、ETL 管线
**依赖项**：duckdb, beautifulsoup4, boto3, aiosqlite

---

## 上下文参考

### 相关代码库文件（实施前必读）

**后端核心（需重构）**

- `backend/app/main.py`（全部 122 行）— lifespan 初始化顺序：日志 → 数据库 → Meilisearch → 索引配置；需改为：日志 → DuckDB → SQLite → Worker 启动
- `backend/app/config.py`（全部 57 行）— Pydantic Settings；需新增 R2/LibGen/DuckDB/SQLite 配置项
- `backend/app/services/search_service.py`（全部 67 行）— 当前 Meilisearch 搜索服务，全局单例模式 `search_service = SearchService()`；需完全重写为 DuckDB
- `backend/app/api/v1/search.py`（全部 75 行）— 搜索 API 端点 + 结果合并逻辑（第 34-60 行核心合并算法按 `(title.lower(), author.lower())` 分组）；需调整异常处理和数据映射
- `backend/app/api/v1/router.py`（全部 8 行）— 路由注册，需新增 download_tasks 路由
- `backend/app/api/v1/health.py`（全部 49 行）— 健康检查，需从 PG+Meili 改为 DuckDB+SQLite
- `backend/app/schemas/search.py`（全部 32 行）— BookFormat/BookResult/SearchResponse 模式定义；`download_url` 字段当前始终为空字符串
- `backend/app/models/book.py`（全部 30 行）— SQLAlchemy Book 模型；迁移后生产环境不再需要但 ETL 本地导入仍用
- `backend/app/database.py`（全部 77 行）— SQLAlchemy async engine 管理；生产环境移除，但本地 ETL 仍需
- `backend/app/core/logging_config.py`（全部 41 行）— 日志配置，降低第三方库级别；保留

**后端 ETL（需新增导出脚本）**

- `backend/etl/import_annas.py`（全部 301 行）— 数据导入脚本，`parse_record()` 函数（第 74-121 行）包含完整的数据清洗逻辑（格式过滤、语言过滤、MD5 提取、OpenCC 简繁转换）；**保留不变**（本地 ETL 仍用 PG）
- `backend/etl/sync_meilisearch.py`（全部 267 行）— Meilisearch 同步脚本；生产环境不再需要但本地开发保留

**前端核心（需重构）**

- `frontend/src/components/BookItem.vue`（全部 160 行）— 下载按钮交互，当前用 `n-popover` + 外站跳转链接（第 8-46 行）；`getDownloadSources()` 函数（第 65-84 行）返回 Anna's Archive / 鸠摩搜索 / 24h搜书 链接；需完全重写为异步下载按钮
- `frontend/src/composables/useSearch.ts`（全部 66 行）— 搜索状态管理；**保持不变**（搜索 API 接口契约不变）
- `frontend/src/api/request.ts`（全部 42 行）— Axios 实例，baseURL 从环境变量读取，响应拦截器自动解包 `response.data`
- `frontend/src/api/modules/search.ts`（全部 7 行）— 搜索 API 调用函数
- `frontend/src/types/search.ts`（全部 22 行）— BookFormat/BookResult/SearchResponse 类型定义
- `frontend/src/views/SearchPage.vue`（全部 105 行）— 搜索结果页
- `frontend/src/components/BookList.vue`（全部 32 行）— 书籍列表组件

**配置和部署**

- `backend/pyproject.toml`（全部 44 行）— 依赖声明；需增删包
- `backend/Dockerfile`（全部 25 行）— 后端容器镜像；需确保 /app/data 目录可写
- `frontend/Dockerfile`（全部 17 行）— 前端容器镜像；`VITE_ANNAS_ARCHIVE_URL` ARG 不再需要
- `docker-compose.yml`（全部 67 行）— 本地开发环境；需调整（PG/Meili 保留给本地 ETL，新增 Volume 映射）

**测试**

- `backend/tests/conftest.py`（全部 39 行）— 测试 fixtures，`sample_meilisearch_hits` 模拟数据
- `backend/tests/test_search.py`（全部 115 行）— 搜索合并逻辑 + SearchService mock 测试；需重写适配 DuckDB
- `backend/tests/test_gateway.py`（全部 120 行）— ETL 清洗逻辑测试；**保留不变**

### 要创建的新文件

**后端新增**

- `backend/app/services/search_service.py` — 重写：DuckDB + Parquet 查询服务
- `backend/app/services/download_task_service.py` — 新增：下载任务 CRUD（SQLite）
- `backend/app/services/libgen_resolver.py` — 新增：MD5 → 真实下载链接解析（library.lol HTML 两步跳转）
- `backend/app/services/r2_service.py` — 新增：Cloudflare R2 上传 + 预签名链接生成
- `backend/app/services/worker_service.py` — 新增：后台 Worker（任务消费循环）
- `backend/app/db/sqlite.py` — 新增：SQLite 连接管理 + 表定义
- `backend/app/api/v1/download_tasks.py` — 新增：下载任务 API 端点
- `backend/app/schemas/download.py` — 新增：下载任务请求/响应模型
- `backend/etl/export_parquet.py` — 新增：PostgreSQL → Parquet 导出脚本

**前端新增**

- `frontend/src/composables/useDownloadTask.ts` — 新增：下载任务创建 + 状态轮询
- `frontend/src/types/download.ts` — 新增：下载任务类型定义
- `frontend/src/api/modules/download.ts` — 新增：下载任务 API 调用函数

### 相关文档（实施前阅读）

- [DuckDB Python API](https://duckdb.org/docs/stable/clients/python/overview)
  - 连接管理、Parquet 查询、参数绑定
  - 原因：搜索服务核心实现
- [DuckDB Parquet Tips](https://duckdb.org/docs/stable/data/parquet/tips)
  - Row group 大小优化、压缩选择
  - 原因：导出 Parquet 时的配置
- [Cloudflare R2 boto3 示例](https://developers.cloudflare.com/r2/examples/aws/boto3/)
  - R2 S3 兼容 API 的 Python 配置
  - 原因：R2 服务实现
- [Cloudflare R2 对象生命周期](https://developers.cloudflare.com/r2/buckets/object-lifecycles/)
  - 自动删除规则配置
  - 原因：7 天清理策略
- [boto3 generate_presigned_url](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/generate_presigned_url.html)
  - 预签名 URL 生成，ResponseContentDisposition 参数
  - 原因：下载链接生成
- [aiosqlite GitHub](https://github.com/omnilib/aiosqlite)
  - async SQLite 接口
  - 原因：任务队列在 async FastAPI 中的使用
- [Railway Volumes](https://docs.railway.com/volumes)
  - Volume 挂载到 /app/data、构建时不可用、权限配置
  - 原因：Parquet + SQLite 持久化存储
- [BeautifulSoup4 文档](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
  - HTML 解析提取链接
  - 原因：LibGen 页面解析

### 要遵循的模式

**服务初始化（全局单例 + lifespan）**

从 `backend/app/services/search_service.py` 提取的模式：
```python
# 服务类定义
class SearchService:
    def __init__(self):
        self.client = None

    async def init(self):
        # 初始化资源
        ...

    async def close(self):
        # 清理资源
        ...

# 全局单例
search_service = SearchService()

# 在 main.py lifespan 中初始化/清理
```

**API 路由注册**

从 `backend/app/api/v1/router.py`：
```python
api_router = APIRouter()
api_router.include_router(search.router, tags=["Search"])
api_router.include_router(health.router, tags=["Health"])
# 新增：
api_router.include_router(download_tasks.router, tags=["Download"])
```

**错误处理**

从 `backend/app/api/v1/search.py` 第 23-30 行：
```python
try:
    result = await service_call()
except (SpecificError1, SpecificError2) as e:
    logger.error("描述: param=%s, error=%s: %s", param, type(e).__name__, e)
    raise HTTPException(status_code=503, detail="用户友好消息")
except Exception:
    logger.exception("未预期错误: param=%s", param)
    raise HTTPException(status_code=500, detail="内部错误")
```

**日志模式**

```python
import logging
logger = logging.getLogger(__name__)

# INFO: 关键事件
logger.info("操作完成: param=%s, result=%s", param, result)
# ERROR: 操作失败
logger.error("操作失败: param=%s, error=%s", param, error)
# EXCEPTION: 未预期异常（自动包含堆栈）
logger.exception("未预期错误: param=%s", param)
```

**Pydantic Schema 模式**

```python
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    field: str
    optional_field: int | None = None
    model_config = ConfigDict(from_attributes=True)
```

**前端 API 调用模式**

```typescript
// api/modules/xxx.ts
import http from '../request'
import type { ResponseType } from '@/types/xxx'

export function apiCall(params: ParamsType) {
  return http.get<unknown, ResponseType>('/endpoint', { params })
}

export function apiPost(data: DataType) {
  return http.post<unknown, ResponseType>('/endpoint', data)
}
```

**前端 Composable 模式**

从 `frontend/src/composables/useSearch.ts`：
```typescript
import { ref } from 'vue'

export function useXxx() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const data = ref<DataType | null>(null)

  const doAction = async () => {
    loading.value = true
    error.value = null
    try {
      data.value = await apiCall()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed'
    } finally {
      loading.value = false
    }
  }

  return { loading, error, data, doAction }
}
```

---

## 实施计划

### 阶段 1：数据管线（本地）

验证 DuckDB + Parquet 方案可行性。创建导出脚本，生成 Parquet 文件。

**任务：**
- 新增 `export_parquet.py` 导出脚本
- 验证 DuckDB 查询中文 ILIKE 性能
- 确认 Parquet 文件大小和格式正确

### 阶段 2：后端基础设施

搭建新的底层服务：DuckDB 搜索、SQLite 任务队列、R2 存储。

**任务：**
- 更新 `config.py` 新增配置项
- 创建 `db/sqlite.py` SQLite 管理
- 重写 `services/search_service.py` 为 DuckDB
- 创建 `services/r2_service.py`
- 创建 `services/libgen_resolver.py`
- 创建 `services/download_task_service.py`
- 创建 `services/worker_service.py`

### 阶段 3：后端 API 层

对接新服务，创建下载任务 API，更新搜索 API 异常处理。

**任务：**
- 创建 `schemas/download.py`
- 创建 `api/v1/download_tasks.py`
- 更新 `api/v1/search.py` 异常处理
- 更新 `api/v1/router.py` 路由注册
- 更新 `api/v1/health.py` 健康检查
- 重构 `main.py` lifespan

### 阶段 4：前端重构

前端对接新的下载 API，替换外站跳转。

**任务：**
- 创建 `types/download.ts`
- 创建 `api/modules/download.ts`
- 创建 `composables/useDownloadTask.ts`
- 重构 `components/BookItem.vue`

### 阶段 5：依赖和部署配置

更新依赖、Dockerfile、docker-compose。

**任务：**
- 更新 `pyproject.toml` 依赖
- 更新后端 `Dockerfile`
- 更新 `docker-compose.yml`
- 更新前端 `Dockerfile`（移除 VITE_ANNAS_ARCHIVE_URL）

### 阶段 6：测试与验证

更新测试套件，验证全流程。

**任务：**
- 重写 `tests/test_search.py`
- 新增下载任务 API 测试
- 新增 LibGen 解析器测试
- 验证全流程

---

## 逐步任务

### 任务 1：CREATE `backend/etl/export_parquet.py`

- **IMPLEMENT**：从本地 PostgreSQL 读取 books 表，选取字段（md5, title, author, year, extension, filesize, language），导出为 Parquet 文件（snappy 压缩）
- **PATTERN**：参考 `etl/import_annas.py` 的 `settings.sync_database_url` 获取同步数据库 URL；使用 `create_engine(settings.sync_database_url)` 连接
- **IMPORTS**：`pandas`, `pyarrow`, `sqlalchemy`（已有），新增 `pandas` 和 `pyarrow` 到 dev 依赖（仅本地运行）
- **GOTCHA**：
  - Parquet 导出脚本只在本地执行，不需要加入生产依赖
  - 使用 snappy 压缩（DuckDB 解压快，性能最优）
  - Row group 大小建议 100,000-1,000,000 行（DuckDB 跨 row group 并行化）
  - 输出路径默认 `data/books.parquet`
- **VALIDATE**：`cd backend && uv run python -m etl.export_parquet --output data/books.parquet && uv run python -c "import duckdb; r = duckdb.sql(\"SELECT count(*) FROM 'data/books.parquet'\"); print(r)"`

### 任务 2：UPDATE `backend/app/config.py`

- **IMPLEMENT**：在 Settings 类中新增以下配置项：
  ```python
  # DuckDB / Parquet
  PARQUET_PATH: str = "data/books.parquet"
  # SQLite 任务队列
  SQLITE_PATH: str = "data/jobs.db"
  # LibGen 镜像
  LIBGEN_MIRROR_URL: str = "https://library.lol"
  LIBGEN_FALLBACK_URL: str = "https://libgen.li"
  # Cloudflare R2
  R2_ENDPOINT_URL: str = ""
  R2_ACCESS_KEY_ID: str = ""
  R2_SECRET_ACCESS_KEY: str = ""
  R2_BUCKET_NAME: str = "easybook-downloads"
  R2_PUBLIC_URL: str = ""  # 用于预签名链接的公开 URL
  # 下载配置
  DOWNLOAD_TIMEOUT: int = 300
  PRESIGNED_URL_EXPIRY: int = 86400  # 24 小时
  WORKER_POLL_INTERVAL: int = 10
  ```
- **PATTERN**：参考现有 `DATABASE_URL`、`MEILI_URL` 等字段的定义模式（`backend/app/config.py` 第 13-23 行）
- **IMPORTS**：无新增
- **GOTCHA**：
  - 保留 `DATABASE_URL`、`MEILI_URL`、`MEILI_MASTER_KEY`（本地开发 ETL 仍需要）
  - 不要删除 `ensure_asyncpg_driver` 和 `sync_database_url`（ETL 仍用）
  - R2 配置项在生产环境通过 Railway 环境变量设置
- **VALIDATE**：`cd backend && uv run python -c "from app.config import settings; print(settings.PARQUET_PATH, settings.SQLITE_PATH, settings.LIBGEN_MIRROR_URL)"`

### 任务 3：CREATE `backend/app/db/__init__.py` 和 `backend/app/db/sqlite.py`

- **IMPLEMENT**：
  - `__init__.py`：空文件
  - `sqlite.py`：使用 `aiosqlite` 管理 SQLite 连接和表定义
    - `init_sqlite()` — 创建/打开数据库，开启 WAL 模式，创建 `download_tasks` 表
    - `get_sqlite()` — 返回 aiosqlite 连接
    - `close_sqlite()` — 关闭连接
    - 表定义：
      ```sql
      CREATE TABLE IF NOT EXISTS download_tasks (
          id TEXT PRIMARY KEY,
          md5 TEXT NOT NULL,
          extension TEXT NOT NULL,
          title TEXT,
          status TEXT NOT NULL DEFAULT 'pending',
          download_url TEXT,
          error_message TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          expires_at TEXT
      );
      CREATE INDEX IF NOT EXISTS idx_status ON download_tasks(status);
      CREATE INDEX IF NOT EXISTS idx_md5_ext ON download_tasks(md5, extension);
      ```
- **PATTERN**：参考 `database.py` 的全局变量 + init/close 模式
- **IMPORTS**：`aiosqlite`（新增依赖）
- **GOTCHA**：
  - WAL 模式：`PRAGMA journal_mode=WAL;`（允许并发读写）
  - aiosqlite 使用单线程执行 SQLite 操作，不会阻塞 asyncio 事件循环
  - SQLite 路径从 `settings.SQLITE_PATH` 读取
  - 确保目录存在：`Path(settings.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)`
- **VALIDATE**：`cd backend && uv run python -c "import asyncio; from app.db.sqlite import init_sqlite, close_sqlite; asyncio.run(init_sqlite()); print('SQLite OK'); asyncio.run(close_sqlite())"`

### 任务 4：REWRITE `backend/app/services/search_service.py`

- **IMPLEMENT**：用 DuckDB 替换 Meilisearch，保持相同的公共接口 `search(query, page, page_size) -> dict`
  ```python
  import logging
  import duckdb
  from app.config import settings

  logger = logging.getLogger(__name__)

  class SearchService:
      def __init__(self):
          self.parquet_path = settings.PARQUET_PATH
          self._con: duckdb.DuckDBPyConnection | None = None

      async def init(self):
          """初始化 DuckDB 持久连接（预热 Parquet 文件元数据）"""
          logger.info("正在初始化 DuckDB: parquet=%s", self.parquet_path)
          self._con = duckdb.connect()  # 内存模式，无持久数据库
          # 预热：加载 Parquet 元数据到内存
          count = self._con.execute(
              f"SELECT count(*) FROM '{self.parquet_path}'"
          ).fetchone()[0]
          logger.info("DuckDB 初始化完成，Parquet 记录数: %d", count)

      async def close(self):
          if self._con:
              self._con.close()
              self._con = None
              logger.info("DuckDB 连接已关闭")

      def _ensure_con(self) -> duckdb.DuckDBPyConnection:
          if self._con is None:
              raise RuntimeError("SearchService not initialized, call init() first")
          return self._con

      def search_sync(self, query: str, page: int = 1, page_size: int = 20) -> dict:
          """同步搜索方法（DuckDB 是同步 API）"""
          con = self._ensure_con()
          offset = (page - 1) * page_size
          pattern = f"%{query}%"

          # 搜索查询
          sql = f"""
              SELECT md5, title, author, year, extension, filesize, language
              FROM '{self.parquet_path}'
              WHERE title ILIKE $1 OR author ILIKE $1
              ORDER BY year DESC NULLS LAST
              LIMIT $2 OFFSET $3
          """
          results = con.execute(sql, [pattern, page_size, offset]).fetchall()

          # 总数查询
          count_sql = f"""
              SELECT COUNT(*)
              FROM '{self.parquet_path}'
              WHERE title ILIKE $1 OR author ILIKE $1
          """
          total = con.execute(count_sql, [pattern]).fetchone()[0]

          # 转换为 dict 列表（兼容现有合并逻辑）
          columns = ["md5", "title", "author", "year", "extension", "filesize", "language"]
          hits = [dict(zip(columns, row)) for row in results]
          # 将 md5 映射为 id（兼容现有 API 层合并逻辑中 hit.get("id", "")）
          for hit in hits:
              hit["id"] = hit["md5"]

          return {
              "hits": hits,
              "total_hits": total,
              "page": page,
              "page_size": page_size,
          }

  search_service = SearchService()
  ```
- **PATTERN**：保持 `search_service = SearchService()` 全局单例模式（`backend/app/services/search_service.py` 第 66 行）
- **IMPORTS**：`duckdb`（新增依赖），移除 `meilisearch_python_sdk`
- **GOTCHA**：
  - DuckDB 是同步 API，不能用 `await`。`init()` 和 `close()` 保持 `async` 签名以兼容 lifespan 调用，但内部执行同步操作
  - `search_sync()` 是同步方法，需要在 API 层用 `asyncio.to_thread()` 包装
  - 参数绑定使用 `$1`、`$2`、`$3` 语法（DuckDB prepared statements），**不用 Python f-string 拼接查询值**（防止 SQL 注入）
  - Parquet 文件路径通过 `settings.PARQUET_PATH` 配置（Railway Volume 挂载到 `/app/data`）
  - DuckDB `connect()` 无参数 = 内存模式，不创建持久数据库文件
  - DuckDB 线程安全：同一连接的查询是串行的，不同连接可以并行（此处用单连接足够）
  - DuckDB 内存默认使用系统 80% RAM，Railway Hobby Plan 内存有限，可能需要 `SET memory_limit = '512MB'`
- **VALIDATE**：`cd backend && uv run python -c "from app.services.search_service import search_service; import asyncio; asyncio.run(search_service.init()); r = search_service.search_sync('python', 1, 5); print(r); asyncio.run(search_service.close())"`

### 任务 5：CREATE `backend/app/services/r2_service.py`

- **IMPLEMENT**：Cloudflare R2 上传 + 预签名链接生成服务
  - `R2Service` 类，全局单例 `r2_service`
  - `init()` — 创建 boto3 S3 client（配置 R2 endpoint）
  - `close()` — 无特殊清理（boto3 client 无需显式关闭）
  - `upload_file(file_path, object_key, content_disposition)` — 上传本地文件到 R2
  - `generate_presigned_url(object_key, expiry)` — 生成 GET 预签名 URL
  - `object_exists(object_key)` — 检查 R2 中是否已存在对象（HEAD 请求）
  - 对象路径格式：`ebooks/{md5}.{ext}`
- **PATTERN**：参考 `search_service.py` 全局单例模式
- **IMPORTS**：`boto3`（新增依赖）
- **GOTCHA**：
  - R2 endpoint URL 格式：`https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
  - 预签名 URL 需要使用 `ResponseContentDisposition` 参数设置下载文件名
  - boto3 client 配置：`endpoint_url`, `aws_access_key_id`, `aws_secret_access_key`, `region_name='auto'`
  - `object_exists()` 用 `head_object()` + 捕获 `ClientError`（404 = 不存在）
  - `upload_file()` 设置 `ContentDisposition: attachment; filename="书名.ext"`，需处理文件名中的非 ASCII 字符（RFC 5987 编码）
  - boto3 是同步库，在 async FastAPI 中需要用 `asyncio.to_thread()` 包装
- **VALIDATE**：`cd backend && uv run python -c "from app.services.r2_service import r2_service; print('R2Service imported OK')"`

### 任务 6：CREATE `backend/app/services/libgen_resolver.py`

- **IMPLEMENT**：LibGen 资源解析器，通过 MD5 获取真实下载链接
  - `resolve_download_url(md5: str) -> str` — 两步跳转解析
    1. GET `{LIBGEN_MIRROR_URL}/main/{MD5}` — 获取中间页 HTML
    2. 用 BeautifulSoup 解析 HTML，提取 `<a>` 标签中包含 "GET" 或 "Cloudflare" 文本的链接
    3. 返回真实下载 URL
  - 支持主镜像失败后自动尝试备用镜像（`LIBGEN_FALLBACK_URL`）
  - 使用项目已有的 `httpx` 作为 HTTP 客户端
- **PATTERN**：函数级模块，不需要类和全局单例（无状态）
- **IMPORTS**：`httpx`（已有），`beautifulsoup4`（新增依赖）
- **GOTCHA**：
  - library.lol 中间页通常有 `<a href="https://download.library.lol/main/...">GET</a>` 这样的链接
  - 也可能有 Cloudflare 镜像链接
  - 需要设置 User-Agent 模拟浏览器（避免 403）
  - 下载超时使用 `settings.DOWNLOAD_TIMEOUT`
  - 错误时抛出自定义异常（如 `LibgenResolveError`），由 Worker 捕获并记录
  - httpx 在 async 环境中使用 `httpx.AsyncClient`
- **VALIDATE**：`cd backend && uv run python -c "from app.services.libgen_resolver import resolve_download_url; print('libgen_resolver imported OK')"`

### 任务 7：CREATE `backend/app/services/download_task_service.py`

- **IMPLEMENT**：下载任务 CRUD 服务
  - `create_task(md5, extension, title) -> dict` — 创建新任务（含去重逻辑）
  - `get_task(task_id) -> dict | None` — 查询单个任务
  - `get_pending_task() -> dict | None` — 获取最早的 pending 任务
  - `update_task_status(task_id, status, download_url=None, error_message=None, expires_at=None)` — 更新任务状态
  - `mark_expired_tasks()` — 将过期的 done 任务标记为 expired
  - 去重逻辑：同一 md5+extension 如果已有 done 且未过期的任务，直接返回已有结果
- **PATTERN**：使用 `aiosqlite` 直接操作（不用 ORM），参考 `db/sqlite.py` 的连接获取
- **IMPORTS**：`aiosqlite`, `uuid`, `datetime`
- **GOTCHA**：
  - task_id 使用 UUID4 字符串
  - 时间格式使用 ISO 8601（`datetime.utcnow().isoformat() + "Z"`）
  - 去重检查：`SELECT * FROM download_tasks WHERE md5=? AND extension=? AND status='done' AND expires_at > datetime('now')`
  - 所有操作都是 async（aiosqlite）
- **VALIDATE**：`cd backend && uv run python -c "from app.services.download_task_service import create_task; print('download_task_service imported OK')"`

### 任务 8：CREATE `backend/app/services/worker_service.py`

- **IMPLEMENT**：后台 Worker 服务
  - `start_worker()` — 启动后台 asyncio 任务（每 N 秒轮询一次）
  - `stop_worker()` — 停止后台任务
  - 处理流程：
    1. 查询 pending 任务
    2. 更新状态为 processing
    3. 检查 R2 缓存（`r2_service.object_exists()`）→ 命中则直接生成预签名 URL
    4. 调用 `libgen_resolver.resolve_download_url(md5)` 获取真实链接
    5. 用 httpx 流式下载到 `/tmp/{md5}.{ext}`
    6. 用 `r2_service.upload_file()` 上传到 R2
    7. 生成预签名 URL
    8. 更新任务状态为 done
    9. 异常时更新为 failed
    10. 清理 `/tmp` 临时文件
  - 过期清理：每小时调用 `mark_expired_tasks()`
- **PATTERN**：参考 lifespan 中启动 asyncio 后台任务的模式
- **IMPORTS**：`asyncio`, `httpx`, `tempfile`, `pathlib`
- **GOTCHA**：
  - 后台任务使用 `asyncio.create_task()` 启动
  - Worker 循环中必须捕获所有异常，避免循环因单个任务失败而终止
  - 文件下载使用 httpx 流式传输：`async with client.stream("GET", url) as response`
  - 下载完成后校验文件大小 > 1KB（过小视为无效）
  - 使用 `asyncio.to_thread()` 包装 boto3 同步调用
  - 取消支持：`stop_worker()` 设置取消标志，Worker 在每次轮询开始时检查
  - 清理 `/tmp` 文件用 `finally` 块确保执行
- **VALIDATE**：`cd backend && uv run python -c "from app.services.worker_service import start_worker, stop_worker; print('worker_service imported OK')"`

### 任务 9：CREATE `backend/app/schemas/download.py`

- **IMPLEMENT**：下载任务的 Pydantic 模型
  ```python
  class DownloadTaskCreate(BaseModel):
      md5: str
      extension: str
      title: str = ""

  class DownloadTaskResponse(BaseModel):
      task_id: str
      md5: str
      title: str
      status: str  # pending/processing/done/failed/expired
      download_url: str | None = None
      error_message: str | None = None
      expires_at: str | None = None
      created_at: str
      message: str = ""
  ```
- **PATTERN**：参考 `schemas/search.py` 的 Pydantic v2 模式
- **IMPORTS**：`pydantic`
- **GOTCHA**：
  - `DownloadTaskCreate` 用于 POST 请求体
  - `DownloadTaskResponse` 用于所有下载任务相关的响应
  - `message` 字段用于给前端显示友好提示
- **VALIDATE**：`cd backend && uv run python -c "from app.schemas.download import DownloadTaskCreate, DownloadTaskResponse; print('schemas OK')"`

### 任务 10：CREATE `backend/app/api/v1/download_tasks.py`

- **IMPLEMENT**：下载任务 API 端点
  - `POST /v1/download-tasks` — 创建下载任务（含去重返回已有结果）
  - `GET /v1/download-tasks/{task_id}` — 查询任务状态
- **PATTERN**：参考 `api/v1/search.py` 的路由定义、错误处理、日志模式
- **IMPORTS**：`fastapi`, `app.schemas.download`, `app.services.download_task_service`
- **GOTCHA**：
  - POST 端点返回 201 Created（新建任务）或 200 OK（返回已有结果）
  - GET 端点如果任务不存在返回 404
  - 路由前缀不要加 `/api`（在 `router.py` 中由 `api_router` 统一加前缀）
- **VALIDATE**：`cd backend && uv run python -c "from app.api.v1.download_tasks import router; print('download_tasks router OK')"`

### 任务 11：UPDATE `backend/app/api/v1/search.py`

- **IMPLEMENT**：
  1. 移除 `meilisearch_python_sdk.errors` 导入
  2. 将 `await search_service.search()` 改为 `await asyncio.to_thread(search_service.search_sync, q, page, page_size)`
  3. 更新异常处理：移除 `MeilisearchError`、`httpx.HTTPError`，改为捕获 `duckdb.Error`（或通用 `Exception`）
  4. 保持结果合并逻辑不变（第 34-60 行的 `merged` 字典合并）
- **PATTERN**：保持现有错误处理结构（`backend/app/api/v1/search.py` 第 23-30 行）
- **IMPORTS**：新增 `asyncio`，移除 `httpx`, `meilisearch_python_sdk`
- **GOTCHA**：
  - `asyncio.to_thread()` 将同步 DuckDB 调用放到线程池执行，不阻塞事件循环
  - 合并逻辑中 `hit.get("id", "")` 和 `hit.get("md5", "")` 在新的搜索结果中都有（任务 4 中设置了 `hit["id"] = hit["md5"]`）
  - `BookFormat` 的 `download_url` 字段保持为空字符串（前端不再使用此字段做跳转）
- **VALIDATE**：`cd backend && uv run ruff check app/api/v1/search.py`

### 任务 12：UPDATE `backend/app/api/v1/router.py`

- **IMPLEMENT**：新增 download_tasks 路由注册
  ```python
  from app.api.v1 import health, search, download_tasks

  api_router = APIRouter()
  api_router.include_router(search.router, tags=["Search"])
  api_router.include_router(health.router, tags=["Health"])
  api_router.include_router(download_tasks.router, tags=["Download"])
  ```
- **PATTERN**：参考现有路由注册模式（`router.py` 第 6-7 行）
- **VALIDATE**：`cd backend && uv run python -c "from app.api.v1.router import api_router; print('routes:', [r.path for r in api_router.routes])"`

### 任务 13：UPDATE `backend/app/api/v1/health.py`

- **IMPLEMENT**：
  1. 移除 PostgreSQL 健康检查（`async_session_maker` + `SELECT 1`）
  2. 移除 Meilisearch 健康检查（`search_service.client.health()`）
  3. 新增 DuckDB 健康检查（尝试简单查询）
  4. 新增 SQLite 健康检查（尝试连接）
  5. 更新 `HealthResponse` schema 字段名：`database` → `duckdb`, `meilisearch` → `sqlite`
- **PATTERN**：保持现有 try/except 模式
- **IMPORTS**：移除 `sqlalchemy`, `app.database`；新增 `app.services.search_service`, `app.db.sqlite`
- **GOTCHA**：更新 `schemas/search.py` 中的 `HealthResponse` 字段以匹配（或使用更通用的字段名）
- **VALIDATE**：`cd backend && uv run ruff check app/api/v1/health.py`

### 任务 14：REFACTOR `backend/app/main.py`

- **IMPLEMENT**：
  1. 移除导入：`app.database.close_db, init_db`
  2. 新增导入：`app.db.sqlite.init_sqlite, close_sqlite`, `app.services.worker_service.start_worker, stop_worker`
  3. 更新 lifespan：
     - 移除数据库初始化/关闭
     - 移除 Meilisearch 客户端初始化/关闭和索引配置
     - 新增 DuckDB 初始化（`search_service.init()`）
     - 新增 SQLite 初始化（`init_sqlite()`）
     - 新增 R2 服务初始化（`r2_service.init()`）— 仅当 R2 配置存在时
     - 新增 Worker 启动（`start_worker()`）
     - 关闭阶段：Worker → R2 → SQLite → DuckDB
  4. 保留：日志系统初始化、CORS、限流、路由
- **PATTERN**：保持现有 lifespan 的 try/except 和日志模式
- **IMPORTS**：按上述调整
- **GOTCHA**：
  - Worker 必须在 SQLite 和 R2 都初始化成功后才启动
  - R2 初始化应该是可选的（如果未配置 R2 环境变量则跳过，Worker 也不启动）
  - 保持 Boot 阶段的 `print()` 模式（logging 未初始化前使用）
  - 关闭顺序：先停 Worker → 再关其他服务
- **VALIDATE**：`cd backend && uv run ruff check app/main.py`

### 任务 15：CREATE `frontend/src/types/download.ts`

- **IMPLEMENT**：
  ```typescript
  export interface DownloadTaskCreate {
    md5: string
    extension: string
    title: string
  }

  export interface DownloadTaskResponse {
    task_id: string
    md5: string
    title: string
    status: 'pending' | 'processing' | 'done' | 'failed' | 'expired'
    download_url: string | null
    error_message: string | null
    expires_at: string | null
    created_at: string
    message: string
  }
  ```
- **VALIDATE**：`cd frontend && npx vue-tsc --noEmit 2>&1 | head -5`

### 任务 16：CREATE `frontend/src/api/modules/download.ts`

- **IMPLEMENT**：
  ```typescript
  import http from '../request'
  import type { DownloadTaskCreate, DownloadTaskResponse } from '@/types/download'

  export function createDownloadTask(data: DownloadTaskCreate) {
    return http.post<unknown, DownloadTaskResponse>('/v1/download-tasks', data)
  }

  export function getDownloadTaskStatus(taskId: string) {
    return http.get<unknown, DownloadTaskResponse>(`/v1/download-tasks/${taskId}`)
  }
  ```
- **PATTERN**：参考 `api/modules/search.ts` 的模式
- **GOTCHA**：axios 实例的响应拦截器已自动解包 `response.data`，所以返回类型直接是 `DownloadTaskResponse`
- **VALIDATE**：`cd frontend && npx vue-tsc --noEmit 2>&1 | head -5`

### 任务 17：CREATE `frontend/src/composables/useDownloadTask.ts`

- **IMPLEMENT**：下载任务管理组合函数
  - `useDownloadTask()` 返回：
    - `taskStates` — `ref<Map<string, DownloadTaskResponse>>`（key = `{md5}_{ext}`）
    - `startDownload(md5, ext, title)` — 创建任务并开始轮询
    - `getTaskState(md5, ext)` — 获取特定格式的任务状态
  - 轮询策略：
    - 前 30 秒：每 3 秒一次
    - 之后：每 10 秒一次
    - 最大轮询时间：5 分钟
    - 使用 `setTimeout` 递归实现（非 `setInterval`，避免积压）
  - 页面离开时自动清理所有轮询定时器（`onUnmounted`）
- **PATTERN**：参考 `composables/useSearch.ts` 的模式
- **IMPORTS**：`vue`（ref, onUnmounted），`@/api/modules/download`
- **GOTCHA**：
  - 轮询 key 使用 `{md5}_{ext}` 确保同一书的不同格式独立追踪
  - `done` 或 `failed` 状态时停止轮询
  - 需要处理网络错误时不终止轮询（继续重试）
  - `onUnmounted` 清理所有 timer ID
- **VALIDATE**：`cd frontend && npx vue-tsc --noEmit 2>&1 | head -5`

### 任务 18：REWRITE `frontend/src/components/BookItem.vue`

- **IMPLEMENT**：
  1. 移除 `n-popover` + 外站跳转链接（第 8-46 行）
  2. 移除 `getDownloadSources()` 函数（第 65-84 行）和 `ANNAS_ARCHIVE_URL` 常量（第 63 行）
  3. 新增：使用 `useDownloadTask` composable
  4. 每个格式按钮的行为改为：
     - 初始状态：显示格式名 + 文件大小，可点击
     - 点击后：调用 `startDownload(md5, ext, title)`
     - pending/processing：按钮显示"准备中..."，禁用，带 loading 状态
     - done：按钮显示"下载"，点击后 `window.open(download_url)`
     - failed：按钮显示"失败 ↻"，可点击重试
  5. 保留 `formatColor()` 和 `formatFileSize()` 函数
- **PATTERN**：使用 Naive UI 的 `n-button` 组件（已有），`:loading` prop 显示加载状态
- **IMPORTS**：新增 `useDownloadTask`
- **GOTCHA**：
  - 不要在 prop 上直接用 `v-model`（Naive UI 限制）
  - `useDownloadTask` 在 `<script setup>` 顶层调用（确保 `onUnmounted` 正确注册）
  - `window.open(url)` 用于打开 R2 预签名 URL（浏览器会自动下载带 Content-Disposition 的响应）
  - 每个 BookItem 实例需要自己的 download task 状态（通过 `{md5}_{ext}` key 隔离）
  - 由于 `useDownloadTask` 在每个 BookItem 中独立使用，需要确保不会创建过多轮询（考虑在 SearchPage 级别共享一个实例）
- **VALIDATE**：`cd frontend && npx vue-tsc --noEmit 2>&1 | head -5`

### 任务 19：UPDATE `backend/pyproject.toml`

- **IMPLEMENT**：
  1. 新增依赖：`duckdb>=1.0.0`, `beautifulsoup4>=4.12.0`, `boto3>=1.35.0`, `aiosqlite>=0.20.0`
  2. 移除依赖（从 dependencies 列表中删除）：`meilisearch-python-sdk>=7.0.0`, `asyncpg>=0.29.0`, `alembic>=1.13.0`
  3. 保留：`sqlalchemy[asyncio]`（本地 ETL 仍需）、`psycopg2-binary`（本地 ETL 仍需）、其他所有包
  4. 新增到 dev 依赖：`pandas>=2.0.0`, `pyarrow>=15.0.0`（导出 Parquet 脚本用）
- **PATTERN**：保持现有格式
- **GOTCHA**：
  - `sqlalchemy[asyncio]` 和 `psycopg2-binary` 保留是因为 `etl/import_annas.py` 和 `etl/sync_meilisearch.py` 仍需在本地执行
  - 移除后运行 `uv sync` 重新生成 lock 文件
  - `aiosqlite` 是 SQLite 的 async 包装，需要单独安装
- **VALIDATE**：`cd backend && uv sync && uv run python -c "import duckdb, bs4, boto3, aiosqlite; print('all deps OK')"`

### 任务 20：UPDATE `backend/Dockerfile`

- **IMPLEMENT**：
  1. 确保 `/app/data` 目录存在（`RUN mkdir -p /app/data`）
  2. 不需要 COPY Parquet 文件（Railway Volume 挂载到 `/app/data`）
  3. 保持其他配置不变
- **PATTERN**：参考现有 Dockerfile
- **GOTCHA**：
  - Railway Volume 在服务启动时挂载（不是构建时），构建期间 `/app/data` 是空的
  - `mkdir -p /app/data` 确保目录存在（Volume 挂载会覆盖此目录）
  - 不要在 Dockerfile 中 COPY `data/` 目录
- **VALIDATE**：`cd backend && docker build -t easybook-api-test . 2>&1 | tail -5`

### 任务 21：UPDATE `docker-compose.yml`

- **IMPLEMENT**：
  1. 保留 `postgres` 和 `meilisearch` 服务（本地 ETL 开发仍需）
  2. 修改 `backend` 服务：
     - 新增 volume 映射：`./backend/data:/app/data`（本地开发用）
     - 新增环境变量：`PARQUET_PATH`, `SQLITE_PATH`, `LIBGEN_MIRROR_URL`
     - 移除 `depends_on` 中的 `postgres` 和 `meilisearch`（API 不再依赖它们）
  3. 保留数据库和 Meilisearch 的健康检查和网络配置
- **PATTERN**：保持现有 YAML 格式
- **GOTCHA**：
  - 本地开发需要手动准备 `backend/data/books.parquet`（通过 export_parquet.py 生成）
  - R2 环境变量在本地 `.env` 中配置或留空（Worker 不启动）
- **VALIDATE**：`docker-compose config 2>&1 | head -20`

### 任务 22：UPDATE `frontend/Dockerfile`

- **IMPLEMENT**：移除 `VITE_ANNAS_ARCHIVE_URL` ARG 和 ENV（不再需要外站跳转 URL）
- **PATTERN**：保持其他配置不变
- **VALIDATE**：`cd frontend && docker build -t easybook-frontend-test . 2>&1 | tail -5`

### 任务 23：REWRITE `backend/tests/test_search.py`

- **IMPLEMENT**：
  1. 更新 `TestFormatMerge` — 保留合并逻辑测试（只需确保 hit 格式包含 `id` 和 `md5` 字段）
  2. 更新 `TestSearchService` — 将 Meilisearch mock 改为 DuckDB mock
     - 测试 `search_sync()` 方法而非 `search()`
     - Mock DuckDB 连接的 `execute().fetchall()` 和 `execute().fetchone()`
  3. 更新 `conftest.py` — `sample_meilisearch_hits` fixture 更名为 `sample_search_hits`，确保每个 hit 包含 `id` 和 `md5` 字段
- **PATTERN**：保持现有 pytest + unittest.mock 模式
- **GOTCHA**：
  - 合并逻辑在 `search.py` API 层，不在 `search_service.py`，所以合并测试不受影响
  - DuckDB 返回的是元组列表，`search_sync()` 内部已转换为 dict 列表
- **VALIDATE**：`cd backend && uv run pytest tests/test_search.py -v`

### 任务 24：CREATE `backend/tests/test_download.py`

- **IMPLEMENT**：
  1. `TestDownloadTaskService` — 测试任务创建、查询、去重逻辑
     - 使用临时 SQLite 文件（`tmp_path` fixture）
  2. `TestLibgenResolver` — 测试 HTML 解析逻辑
     - Mock httpx 响应，提供样例 HTML
  3. `TestDownloadTasksAPI` — 测试 API 端点
     - Mock download_task_service
- **PATTERN**：参考 `tests/test_search.py` 的 mock 模式
- **IMPORTS**：`pytest`, `unittest.mock`, `aiosqlite`
- **GOTCHA**：
  - SQLite 测试使用 `:memory:` 或 `tmp_path` 临时数据库
  - LibGen HTML 样例需要包含真实的页面结构（模拟 library.lol 返回）
- **VALIDATE**：`cd backend && uv run pytest tests/test_download.py -v`

### 任务 25：UPDATE `backend/app/schemas/search.py`

- **IMPLEMENT**：
  1. 更新 `HealthResponse` — 将 `database` 和 `meilisearch` 字段改为更通用的名称或保持不变但语义改变（`database` = DuckDB 状态, `meilisearch` → `task_queue` = SQLite 状态）
  2. 更新 `SearchResponse` 注释 — `total` 字段注释从 "Meilisearch 原始命中记录数" 改为 "DuckDB 查询匹配记录总数"
- **PATTERN**：保持 Pydantic v2 模式
- **GOTCHA**：前端不依赖 HealthResponse 的字段名，可以安全更改
- **VALIDATE**：`cd backend && uv run ruff check app/schemas/search.py`

---

## 测试策略

### 单元测试

- `test_search.py` — DuckDB 搜索服务 mock 测试 + 结果合并逻辑
- `test_download.py` — 下载任务 CRUD + LibGen HTML 解析 + API 端点
- `test_gateway.py` — ETL 清洗逻辑（保持不变）

### 集成测试

- 本地准备 `data/books.parquet`（小型测试集）
- 启动 API 服务，curl 测试搜索和下载全流程
- 验证 Worker 能正确处理任务（需要 R2 配置或 mock）

### 边缘情况

- 空搜索词 → 400 Bad Request（FastAPI Query 验证）
- 中文搜索 ILIKE → 验证子串匹配正确
- 同一 MD5 重复下载请求 → 去重返回已有结果
- Worker 下载失败 → 任务标记 failed，前端可重试
- R2 未配置 → Worker 不启动，API 正常（搜索可用，下载不可用）
- Parquet 文件不存在 → 搜索返回 503
- LibGen 镜像不可用 → 自动切换备用镜像
- 下载文件 < 1KB → 标记为 failed

---

## 验证命令

### 级别 1：语法和样式

```bash
cd backend && uv run ruff check app/ --fix
cd frontend && npx vue-tsc --noEmit
```

### 级别 2：单元测试

```bash
cd backend && uv run pytest tests/ -v
```

### 级别 3：集成测试（本地）

```bash
# 1. 准备数据（需要本地 PG 有数据）
cd backend && uv run python -m etl.export_parquet --output data/books.parquet

# 2. 启动 API
cd backend && uv run uvicorn app.main:app --reload --port 8000

# 3. 测试搜索
curl "http://localhost:8000/api/v1/search?q=python&page=1&page_size=5"

# 4. 测试下载任务创建
curl -X POST "http://localhost:8000/api/v1/download-tasks" \
  -H "Content-Type: application/json" \
  -d '{"md5": "test123", "extension": "epub", "title": "Test Book"}'

# 5. 测试任务状态查询
curl "http://localhost:8000/api/v1/download-tasks/{task_id}"

# 6. 健康检查
curl "http://localhost:8000/api/v1/health"
```

### 级别 4：前端验证

```bash
cd frontend && pnpm dev
# 浏览器访问 http://localhost:3000
# 1. 搜索 "python" → 看到结果
# 2. 点击格式按钮 → 按钮变为 "准备中..."
# 3. 查看网络请求确认 POST /api/v1/download-tasks 和 GET /api/v1/download-tasks/{id} 正常
```

---

## 验收标准

- [ ] DuckDB 搜索在 1 秒内返回结果（Parquet 查询）
- [ ] 搜索 API 接口契约保持不变（前端 useSearch 无需修改）
- [ ] 下载任务 API 端点正确创建、查询、去重
- [ ] Worker 能从 SQLite 取任务、解析 LibGen、下载文件、上传 R2、生成预签名 URL
- [ ] 前端下载按钮状态机正确：可点击 → 准备中 → 可下载/失败重试
- [ ] 前端轮询策略正确（3s/10s 递增，5 分钟超时，页面离开清理）
- [ ] R2 未配置时 API 正常启动（搜索可用，下载功能跳过）
- [ ] 所有单元测试通过
- [ ] ruff lint 零错误
- [ ] vue-tsc 类型检查通过
- [ ] 健康检查端点正确反映 DuckDB + SQLite 状态
- [ ] 环境变量切换 LibGen 镜像无需改代码

---

## 完成检查清单

- [ ] 所有 25 个任务按顺序完成
- [ ] 每个任务验证立即通过
- [ ] 所有验证命令成功执行
- [ ] 完整测试套件通过（单元 + 集成）
- [ ] 无代码检查或类型检查错误
- [ ] 手动测试确认搜索和下载流程正常
- [ ] 所有验收标准均满足
- [ ] 代码遵循项目约定和模式

---

## 备注

### 关键设计决策

1. **DuckDB 同步 API 在 async FastAPI 中的使用**：通过 `asyncio.to_thread()` 将 DuckDB 查询放到线程池执行，避免阻塞事件循环。这是 DuckDB 官方推荐的 async 集成方式。

2. **aiosqlite vs 同步 sqlite3**：选择 aiosqlite 是因为 Worker 和 API 都需要操作 SQLite，aiosqlite 的 async 接口与 FastAPI 的 async 模式更自然地协同。

3. **保留 PostgreSQL/Meilisearch 本地开发依赖**：ETL 管线（import_annas + sync_meilisearch）仍在本地用 PG，只是生产环境不再需要这两个服务。这避免了大规模重构 ETL 脚本。

4. **搜索 API 接口契约不变**：前端 `useSearch.ts` 和 `SearchResponse` 类型完全不需要修改，降低了前端的变更范围。

5. **R2 配置可选**：当 R2 环境变量为空时，Worker 不启动，但搜索功能仍然可用。这允许在没有 R2 账号的情况下进行本地开发和测试。

6. **useDownloadTask 共享问题**：由于 BookItem 是列表渲染的子组件，如果每个实例都创建自己的 composable 实例，可能导致大量独立的轮询。更好的方式是在 SearchPage 或 BookList 级别创建单个 `useDownloadTask` 实例，通过 provide/inject 传递给子组件。实施时需要注意这一点。

### 迁移后的 Railway 配置变更

- 新增 Volume 挂载到 `easybook-api` 的 `/app/data`
- 新增环境变量：`PARQUET_PATH`, `SQLITE_PATH`, `R2_*`, `LIBGEN_*`, `WORKER_*`
- 移除 `PostgreSQL` 服务
- 移除 `getmeili/meilisearch:v1.9.0` 服务
- 移除后端的 `DATABASE_URL`, `MEILI_URL`, `MEILI_MASTER_KEY` 环境变量

### Parquet 数据准备

生产部署前需要：
1. 本地执行 `export_parquet.py` 生成 `books.parquet`
2. 通过 Railway CLI 或 SSH 将文件上传到 Volume（`railway volume upload`）
3. 或在 Dockerfile 中添加下载步骤（如果 Parquet 存储在 R2 或其他 CDN）

### 风险

1. **DuckDB ILIKE 中文性能**：理论上子串匹配对中文有效（ILIKE 是 Unicode 感知的），但需要实际验证大数据集性能
2. **LibGen 反爬**：单 Worker 串行处理天然限流，但仍需注意不要频繁请求
3. **Railway Volume 大小**：Parquet 文件预计 1-3GB，Railway Volume 按 $0.25/GB/月 计费
4. **R2 中国大陆访问**：Cloudflare CDN 在中国有节点，但实际速度需验证

### 信心分数：8/10

主要风险点在于 LibGen HTML 解析的稳定性和 R2 中国大陆的实际下载速度。代码层面的实施路径非常清晰。
