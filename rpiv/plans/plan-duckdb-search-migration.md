---
description: "功能实施计划: DuckDB + Parquet 搜索迁移（替代 Meilisearch + PostgreSQL）"
status: completed
created_at: 2026-02-09T01:30:00
updated_at: 2026-02-09T20:00:00
archived_at: null
related_files:
  - rpiv/requirements/prd-duckdb-search-migration.md
---

# 功能：DuckDB + Parquet 搜索迁移

以下计划应该是完整的，但在开始实施之前，验证文档和代码库模式以及任务合理性非常重要。

特别注意现有工具、类型和模型的命名。从正确的文件导入等。

## 功能描述

用 DuckDB + Parquet 替代 Meilisearch 全文搜索引擎，移除生产环境对 Meilisearch 和 PostgreSQL 的依赖。搜索通过 DuckDB 直接查询 Parquet 文件实现。下载仍保持浏览器跳转 Anna's Archive 方案不变。

## 用户故事

作为 EasyBook 运维者，
我想要用 DuckDB + Parquet 替代 Meilisearch + PostgreSQL，
以便降低 Railway 上的资源占用（内存和存储），同时保持搜索功能正常。

## 问题陈述

当前 Meilisearch 索引 2000 万+ 元数据需要大量内存和存储，在 Railway Hobby Plan 上资源压力大。PostgreSQL 同样占用额外的服务资源。需要一个更轻量的搜索方案。

## 解决方案陈述

- **DuckDB + Parquet** 替代 Meilisearch（零常驻进程，直接查询 Parquet 文件）
- **移除 Meilisearch 和 PostgreSQL** 的生产运行依赖（保留 PostgreSQL 作为本地 ETL 数据源）
- **Railway Volume** 持久化存储 Parquet 文件
- 搜索 API 契约完全不变（前端零改动）
- 下载方案保持现状（浏览器跳转 Anna's Archive）

## 功能元数据

**功能类型**：重构
**估计复杂度**：中
**主要受影响的系统**：后端搜索服务、健康检查、配置、ETL 同步脚本、部署配置
**依赖项**：duckdb（新增）
**前端改动**：无

---

## 架构变更概要

```
迁移前:
Vue3 前端 → FastAPI → Meilisearch (全文检索) + PostgreSQL (元数据)

迁移后:
Vue3 前端 → FastAPI → DuckDB (查询 Parquet 文件)
                      PostgreSQL 仅保留本地 ETL 用途（不部署到生产）
```

## 关键技术决策

### DuckDB 连接策略
- **每次请求创建新连接**（`duckdb.connect()` → 查询 → 自动关闭）
- DuckDB 单连接非线程安全，每请求新连接是并发场景最安全的方式
- 使用 `asyncio.to_thread()` 将同步 DuckDB 查询桥接到 async FastAPI

### 搜索实现
- 使用 `ILIKE '%keyword%'` 子串匹配（等效 Meilisearch 的模糊搜索）
- 搜索字段：title, author（与 Meilisearch 配置一致）
- DuckDB 1.3+ 对 ILIKE 子串扫描做了 memchr 优化，性能可接受
- 千万级数据 ILIKE 全表扫描约 1-3 秒（可接受，用户量 <100）

### Parquet 文件规范
- 字段：md5, title, author, extension, filesize, language, year, publisher
- 使用 md5 作为文档 ID（映射到搜索结果的 `id` 字段）
- 压缩格式：Snappy（默认，解压快）
- Row Group 大小：100,000+ 行（DuckDB 最优扫描粒度）

### Railway Volume
- Mount Path: `/data`
- 存储：books.parquet 文件
- 容量需求：约 3-5GB（2000 万条元数据）

---

## 实施任务

### 阶段 1: 核心搜索服务替换

#### 任务 1: 新增 DuckDB 依赖
**文件**: `backend/pyproject.toml`
**操作**:
- 新增 `duckdb>=1.0.0` 到 dependencies
- 移除 `meilisearch-python-sdk>=7.0.0`
- 保留 `asyncpg`、`psycopg2-binary`、`sqlalchemy[asyncio]`（ETL 仍需要）
- 执行 `cd backend && uv sync`

#### 任务 2: 更新配置项
**文件**: `backend/app/config.py`
**操作**:
- 移除 `MEILI_URL` 和 `MEILI_MASTER_KEY`
- 新增 `DUCKDB_PARQUET_PATH: str = "./data/books.parquet"`（Parquet 文件完整路径）
- 新增 `DUCKDB_MEMORY_LIMIT: str = "256MB"`（DuckDB 内存上限）
- 新增 `DUCKDB_THREADS: int = 2`（查询线程数）
- 保留 `DATABASE_URL` 和相关 validator（ETL 本地使用）

```python
# 新增配置项
DUCKDB_PARQUET_PATH: str = "./data/books.parquet"
DUCKDB_MEMORY_LIMIT: str = "256MB"
DUCKDB_THREADS: int = 2
```

#### 任务 3: 重写 SearchService
**文件**: `backend/app/services/search_service.py`
**操作**: 完全重写，用 DuckDB 替代 Meilisearch

**关键接口保持不变**:
- `async def init()` — 验证 Parquet 文件存在
- `async def close()` — 空操作（DuckDB 每次请求新建连接）
- `async def search(query, page, page_size) -> dict` — 返回格式完全一致

```python
import asyncio
import logging
from pathlib import Path

import duckdb

from app.config import settings

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self):
        self.parquet_path: str = ""
        self._initialized: bool = False

    async def init(self):
        """验证 Parquet 文件存在"""
        self.parquet_path = settings.DUCKDB_PARQUET_PATH
        path = Path(self.parquet_path)
        if path.exists():
            # 验证文件可读，获取记录数
            count = await asyncio.to_thread(self._get_record_count)
            logger.info("DuckDB 搜索服务初始化成功: parquet=%s, records=%d",
                        self.parquet_path, count)
            self._initialized = True
        else:
            logger.warning("Parquet 文件不存在: %s，搜索功能不可用", self.parquet_path)

    async def close(self):
        """无需清理（每次查询用独立连接）"""
        logger.info("DuckDB 搜索服务已关闭")

    async def search(self, query: str, page: int = 1, page_size: int = 20) -> dict:
        """搜索书籍，返回与 Meilisearch 兼容的结果格式"""
        if not self._initialized:
            raise RuntimeError("SearchService not initialized, call init() first")

        logger.debug("搜索请求: query=%s, page=%d, page_size=%d", query, page, page_size)
        result = await asyncio.to_thread(
            self._sync_search, query, page, page_size
        )
        logger.info(
            "搜索完成: query=%s, total_hits=%d, page=%d",
            query, result["total_hits"], page,
        )
        return result

    def _sync_search(self, query: str, page: int, page_size: int) -> dict:
        """同步 DuckDB 查询（在线程中执行）"""
        offset = (page - 1) * page_size
        pattern = f"%{query}%"

        with duckdb.connect(config={
            "threads": settings.DUCKDB_THREADS,
            "memory_limit": settings.DUCKDB_MEMORY_LIMIT,
        }) as conn:
            # 获取总数
            count_sql = f"""
                SELECT COUNT(*) as cnt
                FROM read_parquet(?)
                WHERE title ILIKE ? OR author ILIKE ?
            """
            total_hits = conn.execute(count_sql, [self.parquet_path, pattern, pattern]).fetchone()[0]

            # 获取分页结果
            search_sql = f"""
                SELECT md5 as id, title, author, extension, filesize, language, year, publisher
                FROM read_parquet(?)
                WHERE title ILIKE ? OR author ILIKE ?
                LIMIT ?
                OFFSET ?
            """
            rows = conn.execute(
                search_sql, [self.parquet_path, pattern, pattern, page_size, offset]
            ).fetchall()
            columns = ["id", "title", "author", "extension", "filesize",
                        "language", "year", "publisher"]
            hits = [dict(zip(columns, row)) for row in rows]

        return {
            "hits": hits,
            "total_hits": total_hits,
            "page": page,
            "page_size": page_size,
        }

    def _get_record_count(self) -> int:
        """获取 Parquet 文件的总记录数"""
        with duckdb.connect() as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM read_parquet(?)", [self.parquet_path]
            ).fetchone()
            return result[0] if result else 0


search_service = SearchService()
```

#### 任务 4: 更新搜索端点异常处理
**文件**: `backend/app/api/v1/search.py`
**操作**:
- 移除 `from meilisearch_python_sdk.errors import MeilisearchError` 导入
- 移除 `import httpx`（不再需要）
- 将 `except (MeilisearchError, ConnectionError, TimeoutError, httpx.HTTPError)` 改为 `except (RuntimeError, OSError)` 或 `except Exception`

```python
# 第 5 行：移除
# from meilisearch_python_sdk.errors import MeilisearchError

# 第 4 行：移除 httpx 导入（如果仅此处使用）
# import httpx

# 第 25 行：替换异常类型
except (RuntimeError, OSError) as e:
    logger.error("搜索服务不可用: query=%s, error=%s: %s", q, type(e).__name__, e)
    raise HTTPException(status_code=503, detail="搜索服务暂时不可用，请稍后重试")
```

#### 任务 5: 更新 lifespan
**文件**: `backend/app/main.py`
**操作**:
- 移除 `configure_index()` 调用（第 67-72 行）
- 更新日志消息中的 "Meilisearch" 为 "DuckDB 搜索服务"

```python
# 移除整个块：
# # 4. 配置 Meilisearch 索引
# try:
#     logger.info("正在配置 Meilisearch 索引...")
#     await search_service.configure_index()
#     logger.info("Meilisearch 索引配置完成")
# except Exception as e:
#     logger.warning("Meilisearch 索引配置失败: %s", e)

# 更新第 58-65 行日志消息
# "正在初始化 Meilisearch 客户端..." → "正在初始化 DuckDB 搜索服务..."
# "Meilisearch 客户端初始化成功" → "DuckDB 搜索服务初始化成功"
# "Meilisearch 客户端初始化失败" → "DuckDB 搜索服务初始化失败"
# "Meilisearch 客户端已关闭" → "DuckDB 搜索服务已关闭"（第 85 行）
```

### 阶段 2: 健康检查和 Schema 更新

#### 任务 6: 更新 HealthResponse Schema
**文件**: `backend/app/schemas/search.py`
**操作**:
- `HealthResponse.meilisearch` 字段改为 `duckdb`
- 更新注释

```python
class HealthResponse(BaseModel):
    status: str
    database: str
    duckdb: str  # 原 meilisearch
```

#### 任务 7: 更新健康检查端点
**文件**: `backend/app/api/v1/health.py`
**操作**:
- 移除 Meilisearch 健康检查
- 新增 DuckDB/Parquet 文件检查
- 移除 `from app.services.search_service import search_service` 导入（如果不需要）

```python
from pathlib import Path
from app.config import settings

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """系统健康检查"""
    db_status = "ok"
    duckdb_status = "ok"

    # 检查 PostgreSQL（保留用于 ETL 场景，生产可 skip）
    try:
        if async_session_maker:
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        db_status = "error"

    # 检查 DuckDB Parquet 文件
    parquet_path = Path(settings.DUCKDB_PARQUET_PATH)
    if not parquet_path.exists():
        duckdb_status = "error"
        logger.error("Parquet file not found: %s", parquet_path)

    overall = "ok" if db_status == "ok" and duckdb_status == "ok" else "degraded"
    logger.info("健康检查: overall=%s, db=%s, duckdb=%s", overall, db_status, duckdb_status)

    return HealthResponse(
        status=overall,
        database=db_status,
        duckdb=duckdb_status,
    )
```

### 阶段 3: ETL 数据管线

#### 任务 8: 创建 PostgreSQL → Parquet 导出脚本
**文件**: `backend/etl/export_parquet.py`（新建）
**操作**: 从本地 PostgreSQL 读取 books 表，导出为 Parquet 文件

```python
"""
PostgreSQL → Parquet 导出脚本

用法:
    cd backend
    uv run python -m etl.export_parquet [--output ./data/books.parquet]

将本地 PostgreSQL 中的 books 表导出为 DuckDB 可直接查询的 Parquet 文件。
"""
import argparse
import logging
import time
from pathlib import Path

import duckdb

from app.config import settings

logger = logging.getLogger(__name__)


def export_to_parquet(output_path: str) -> int:
    """将 PostgreSQL books 表导出为 Parquet 文件，返回导出记录数"""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # 使用同步 PostgreSQL URL
    pg_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    start = time.time()
    logger.info("开始导出: PG → %s", output_path)

    with duckdb.connect() as conn:
        # 安装并加载 PostgreSQL 扩展
        conn.install_extension("postgres")
        conn.load_extension("postgres")

        # 附加 PostgreSQL 数据库
        conn.execute(f"ATTACH '{pg_url}' AS pg (TYPE POSTGRES, READ_ONLY)")

        # 导出为 Parquet（选择搜索需要的字段）
        conn.execute(f"""
            COPY (
                SELECT md5, title, author, extension, filesize,
                       language, year, publisher
                FROM pg.public.books
                WHERE md5 IS NOT NULL AND md5 != ''
                  AND title IS NOT NULL AND title != ''
            ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION SNAPPY, ROW_GROUP_SIZE 100000)
        """)

        # 获取导出记录数
        count = conn.execute(
            f"SELECT COUNT(*) FROM read_parquet('{output_path}')"
        ).fetchone()[0]

    elapsed = time.time() - start
    logger.info("导出完成: %d 条记录, 耗时 %.1f 秒, 文件: %s",
                count, elapsed, output_path)
    return count


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="PostgreSQL → Parquet 导出")
    parser.add_argument(
        "--output", "-o",
        default="./data/books.parquet",
        help="输出 Parquet 文件路径 (默认: ./data/books.parquet)",
    )
    args = parser.parse_args()
    export_to_parquet(args.output)


if __name__ == "__main__":
    main()
```

#### 任务 9: 创建 data 目录和 .gitignore
**操作**:
- 创建 `backend/data/` 目录
- 创建 `backend/data/.gitignore`，内容为 `*.parquet`（Parquet 文件不纳入 git）

### 阶段 4: 部署配置更新

#### 任务 10: 更新 docker-compose.yml
**文件**: `docker-compose.yml`
**操作**:
- 移除 `meilisearch` 服务定义
- 移除 `meili_data` volume
- 移除 backend 的 `MEILI_URL` 和 `MEILI_MASTER_KEY` 环境变量
- 新增 backend 的 `DUCKDB_PARQUET_PATH` 环境变量
- 新增 backend 的 `./data:/app/data` volume 挂载
- 移除 backend 的 `depends_on.meilisearch`

```yaml
# backend 服务改动
backend:
  environment:
    DATABASE_URL: "postgresql+asyncpg://easybook:easybook@postgres:5432/easybook"
    DUCKDB_PARQUET_PATH: /app/data/books.parquet
    DUCKDB_MEMORY_LIMIT: "256MB"
    DUCKDB_THREADS: "2"
    LOG_LEVEL: "INFO"
  volumes:
    - ./data:/app/data
  depends_on:
    postgres:
      condition: service_healthy
    # meilisearch 已移除
```

#### 任务 11: 更新后端 Dockerfile
**文件**: `backend/Dockerfile`
**操作**:
- 新增 `RUN mkdir -p /data`（Volume 挂载点的目标目录）
- 无其他改动（启动命令不变）

#### 任务 12: 更新后端 .env 模板
**文件**: `backend/.env`（或 `.env.example`）
**操作**:
- 移除 `MEILI_URL` 和 `MEILI_MASTER_KEY`
- 新增 `DUCKDB_PARQUET_PATH=./data/books.parquet`
- 新增 `DUCKDB_MEMORY_LIMIT=256MB`
- 新增 `DUCKDB_THREADS=2`

### 阶段 5: 测试更新

#### 任务 13: 更新搜索测试
**文件**: `backend/tests/test_search.py`
**操作**:
- 更新 mock 目标：`app.services.search_service.duckdb` → 直接 mock `SearchService.search` 方法
- 移除 Meilisearch 相关的 mock 和 import
- 保持格式合并测试逻辑不变（`test_merge_same_book_formats` 等）
- 保持 `sample_meilisearch_hits` fixture 数据格式不变（可重命名为 `sample_search_hits`）

#### 任务 14: 更新 conftest.py（如需要）
**文件**: `backend/tests/conftest.py`
**操作**:
- 如有 Meilisearch 相关的 fixture，替换为 DuckDB 兼容版本
- 搜索结果 fixture 数据格式保持不变

#### 任务 15: 运行完整测试套件
**操作**:
```bash
cd backend
uv run pytest tests/ -v
uv run ruff check app/ etl/
```

### 阶段 6: 本地端到端验证

#### 任务 16: 本地 PostgreSQL → Parquet 导出验证
**操作**:
1. 确保本地 PostgreSQL 运行且 books 表有数据
2. 执行 `cd backend && uv run python -m etl.export_parquet`
3. 验证 `data/books.parquet` 文件生成且大小合理
4. 用 DuckDB CLI 或 Python 验证文件可查询

#### 任务 17: 本地搜索服务验证
**操作**:
1. 更新 `backend/.env`，设置 `DUCKDB_PARQUET_PATH=./data/books.parquet`
2. 启动后端：`cd backend && uv run uvicorn app.main:app --reload --port 8000`
3. 测试搜索 API：`curl "http://localhost:8000/api/search?q=python"`
4. 验证返回格式与 Meilisearch 版本一致
5. 验证健康检查：`curl "http://localhost:8000/api/health"`

#### 任务 18: 前端兼容性验证
**操作**:
1. 启动前端：`cd frontend && pnpm dev`
2. 在浏览器中执行搜索，验证结果正常显示
3. 验证分页功能
4. 验证下载按钮跳转 Anna's Archive 正常

### 阶段 7: Railway 生产部署

#### 任务 19: Railway 环境变量更新
**操作**:
1. 移除 `easybook-api` 的 `MEILI_URL` 和 `MEILI_MASTER_KEY` 环境变量
2. 新增 `DUCKDB_PARQUET_PATH=/data/books.parquet`
3. 新增 `DUCKDB_MEMORY_LIMIT=256MB`
4. 新增 `DUCKDB_THREADS=2`

#### 任务 20: Railway Volume 配置
**操作**:
1. 为 `easybook-api` 服务添加 Volume，Mount Path 设为 `/data`
2. 将 Parquet 文件上传到 Volume（可通过临时脚本或 CLI 完成）

#### 任务 21: 上传 Parquet 到 Railway Volume
**操作**: 需要一个启动时运行的初始化逻辑或手动上传
- **方案 A**: 在后端启动脚本中加入"如果 Parquet 不存在则从备用 URL 下载"逻辑
- **方案 B**: 通过 Railway CLI 或 SSH 手动上传
- **方案 C**: 将 Parquet 文件放入 Docker 镜像（不推荐，镜像会很大）

建议采用 **方案 B**，首次手动上传后 Volume 会持久化。

#### 任务 22: 验证生产部署
**操作**:
1. 推送代码到 master 触发自动部署
2. 验证 `https://easybook-api.up.railway.app/api/health` 返回 `{"status":"ok","database":"...","duckdb":"ok"}`
3. 验证 `https://easybook-api.up.railway.app/api/search?q=python` 返回正常结果
4. 验证前端 `https://easybook.up.railway.app` 搜索功能正常

### 阶段 8: 清理（可选）

#### 任务 23: 考虑移除 Railway 上的 Meilisearch 服务
**操作**: 确认搜索迁移稳定后，在 Railway 项目中删除 `getmeili/meilisearch:v1.9.0` 服务
**风险**: 不可逆，需确认不再需要

#### 任务 24: 考虑移除 Railway 上的 PostgreSQL 服务
**操作**: 如果 ETL 只在本地运行，生产 PostgreSQL 不再需要
**风险**: 不可逆，确认 database.py 中的连接失败不会影响应用启动（当前代码已有容错）

---

## 不变项清单

以下内容在迁移过程中 **完全不变**：

| 模块 | 文件 | 原因 |
|------|------|------|
| 搜索 API 契约 | `api/v1/search.py` 的格式合并逻辑 | 前端依赖此格式 |
| 响应 Schema | `schemas/search.py` 的 BookFormat/BookResult/SearchResponse | 前端类型定义匹配 |
| SQLAlchemy 模型 | `models/book.py` | ETL 导入仍使用 |
| 数据库连接 | `database.py` | ETL 和健康检查仍使用 |
| 前端全部代码 | `frontend/src/**` | API 契约不变 |
| ETL 导入脚本 | `etl/import_annas.py` | 仍从 JSONL.zst 导入 PostgreSQL |

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| ILIKE 全表扫描慢（千万级数据） | 中 | 搜索响应 >3 秒 | 1. 限制 page_size ≤100 2. 后续可加 DuckDB FTS 索引 |
| Parquet 文件损坏 | 低 | 搜索完全不可用 | 保留本地备份 + 重新导出脚本 |
| Railway Volume 不稳定 | 低 | 重部署后文件丢失 | 实际测试 Volume 持久性 + 备份 |
| DuckDB 内存超限 | 低 | OOM kill | 配置 memory_limit + temp_directory |

## 回滚策略

如果迁移失败，可通过以下步骤回滚：
1. 恢复 `pyproject.toml` 中的 `meilisearch-python-sdk` 依赖
2. 恢复 `search_service.py` 到 Meilisearch 版本
3. 恢复 Railway 环境变量（MEILI_URL、MEILI_MASTER_KEY）
4. 重启 Meilisearch 服务并重新同步索引
