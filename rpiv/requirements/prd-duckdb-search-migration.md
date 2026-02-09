---
description: "产品需求文档: DuckDB + Parquet 搜索迁移（替代 Meilisearch + PostgreSQL）"
status: completed
created_at: 2026-02-09T17:30:00
updated_at: 2026-02-09T20:00:00
archived_at: null
---

# DuckDB + Parquet 搜索迁移

## 1. 执行摘要

EasyBook 当前使用 Meilisearch + PostgreSQL 作为搜索基础设施，在 Railway Hobby Plan 上运行 2000 万+ 书籍元数据索引，内存和存储压力大，且需要维护两个有状态服务（Meilisearch 和 PostgreSQL）。

本次迁移用 DuckDB + Parquet 文件替代 Meilisearch 全文搜索引擎，移除生产环境对 Meilisearch 和 PostgreSQL 的运行时依赖。搜索通过 DuckDB 直接查询预生成的 Parquet 文件实现，零常驻进程，资源占用大幅降低。

**MVP 目标**：搜索 API 契约完全不变（前端零改动），用 DuckDB 查询 Parquet 文件替代 Meilisearch 索引查询，并在 Railway 上成功部署验证。

## 2. 使命

**使命声明**：以最小架构复杂度提供可靠的电子书搜索服务，降低运维成本和资源占用。

**核心原则**：

1. **API 契约不变** — 搜索接口的请求参数和响应格式完全保持一致，前端零改动
2. **极简架构** — 移除有状态服务依赖，从"FastAPI + Meilisearch + PostgreSQL"简化为"FastAPI + Parquet 文件"
3. **资源高效** — DuckDB 按需查询、无常驻进程，适合低流量场景（用户量 <100）
4. **数据管线分离** — ETL（PostgreSQL → Parquet 导出）在本地执行，生产环境只需 Parquet 文件

## 3. 目标用户

**主要用户**：EasyBook 终端用户（搜索电子书的普通用户）
- 通过 Web 界面搜索书名或作者名
- 期望搜索响应时间 <5 秒（可接受范围）
- 使用频率低，并发用户 <10

**次要用户**：EasyBook 运维者（开发者本人）
- 期望降低 Railway 月度资源费用
- 期望减少维护的有状态服务数量
- 期望简化部署流程

## 4. MVP 范围

### 范围内

- ✅ DuckDB 搜索服务替代 Meilisearch（`SearchService` 完全重写）
- ✅ 配置项迁移（移除 `MEILI_*`，新增 `DUCKDB_*`）
- ✅ 健康检查端点更新（`meilisearch` → `duckdb` 字段）
- ✅ 搜索异常处理更新（移除 Meilisearch SDK 异常类型）
- ✅ `lifespan` 启动流程更新（移除 `configure_index()`）
- ✅ PostgreSQL → Parquet 导出脚本（`etl/export_parquet.py`）
- ✅ `docker-compose.yml` 更新（移除 Meilisearch 服务）
- ✅ 后端 Dockerfile 更新（Volume 挂载点）
- ✅ 测试套件更新（mock 目标替换）
- ✅ Railway 环境变量和 Volume 配置
- ✅ 生产部署验证

### 范围外

- ❌ DuckDB Full-Text Search 扩展（FTS）索引优化 — 后续按需引入
- ❌ Parquet 文件自动更新/增量同步机制 — 手动重新导出即可
- ❌ 前端任何改动 — API 契约不变
- ❌ 搜索结果排序优化 — 当前 ILIKE 匹配顺序即可
- ❌ 移除本地开发的 PostgreSQL — ETL 导入仍需要
- ❌ 多文件分片 Parquet — 单文件足够
- ❌ 搜索缓存层 — 用户量极少，无需缓存

## 5. 用户故事

**US-1**：作为搜索用户，我想要搜索书名或作者名找到电子书，以便获取下载链接。
- 示例：搜索"三体"返回《三体》系列的 epub/pdf/mobi 等格式
- 验证：搜索结果格式、分页、多格式合并与迁移前完全一致

**US-2**：作为搜索用户，我想要分页浏览搜索结果，以便在大量结果中找到目标。
- 示例：搜索"Python"返回数千结果，每页 20 条，可翻页
- 验证：`page` 和 `page_size` 参数正常工作

**US-3**：作为运维者，我想要用 DuckDB + Parquet 替代 Meilisearch + PostgreSQL，以便降低 Railway 资源占用。
- 验证：生产环境仅运行 FastAPI 后端 + Parquet 文件，无 Meilisearch/PostgreSQL 服务

**US-4**：作为运维者，我想要从本地 PostgreSQL 导出 Parquet 文件，以便上传到生产环境。
- 示例：`uv run python -m etl.export_parquet` 生成 `data/books.parquet`
- 验证：导出文件可被 DuckDB 正常查询

**US-5**：作为运维者，我想要通过健康检查端点确认搜索服务状态，以便监控系统可用性。
- 示例：`GET /api/health` 返回 `{"status":"ok","database":"ok","duckdb":"ok"}`

**US-6**：作为运维者，我想要在搜索服务异常时收到 503 错误（而非 500），以便区分服务不可用和内部错误。
- 验证：Parquet 文件缺失时返回 503，代码 bug 返回 500

## 6. 核心架构与模式

### 架构变更

```
迁移前:
Vue3 前端 (:3000) → FastAPI 后端 (:8000) → Meilisearch (全文检索)
                                           → PostgreSQL (元数据持久化)

迁移后:
Vue3 前端 (:3000) → FastAPI 后端 (:8000) → DuckDB (查询 Parquet 文件)
                                           PostgreSQL 仅保留本地 ETL 用途
```

### 关键设计决策

| 决策 | 方案 | 理由 |
|------|------|------|
| DuckDB 连接策略 | 每次请求创建新连接 | DuckDB 单连接非线程安全，每请求新连接是并发场景最安全的方式 |
| 搜索实现 | `ILIKE '%keyword%'` 子串匹配 | 等效 Meilisearch 模糊搜索，DuckDB 1.3+ 有 memchr 优化 |
| async 桥接 | `asyncio.to_thread()` | DuckDB 是同步 API，通过线程桥接到 async FastAPI |
| Parquet 压缩 | Snappy | 默认格式，解压速度快 |
| Row Group 大小 | 100,000+ 行 | DuckDB 最优扫描粒度 |
| 数据 ID | md5 字段 | 与现有搜索结果的 `id` 字段映射一致 |

### 搜索性能预期

- 千万级数据 ILIKE 全表扫描：约 1-3 秒
- 用户量 <100，并发 <10，性能完全可接受
- 后续可通过 DuckDB FTS 索引进一步优化

## 7. 工具/功能

### 7.1 SearchService 重写

完全重写 `backend/app/services/search_service.py`，接口保持不变：

| 方法 | 功能 | 变更 |
|------|------|------|
| `init()` | 验证 Parquet 文件存在、获取记录数 | 替代 Meilisearch 客户端初始化 |
| `close()` | 空操作 | DuckDB 每请求新建连接，无需清理 |
| `search(query, page, page_size)` | 搜索书籍 | DuckDB ILIKE 查询替代 Meilisearch SDK |

返回格式完全一致：
```python
{
    "hits": [{"id", "title", "author", "extension", "filesize", "language", "year", "publisher"}],
    "total_hits": int,
    "page": int,
    "page_size": int,
}
```

### 7.2 ETL 导出脚本

新增 `backend/etl/export_parquet.py`：

- 从本地 PostgreSQL `books` 表读取数据
- 使用 DuckDB 的 PostgreSQL 扩展直连读取
- 导出为 Snappy 压缩的 Parquet 文件
- 字段：md5, title, author, extension, filesize, language, year, publisher
- 过滤：`md5 IS NOT NULL AND title IS NOT NULL`

### 7.3 健康检查更新

`GET /api/health` 响应 Schema 变更：
```python
class HealthResponse(BaseModel):
    status: str       # "ok" | "degraded"
    database: str     # "ok" | "error"
    duckdb: str       # "ok" | "error"（原 meilisearch 字段）
```

DuckDB 健康检查逻辑：验证 Parquet 文件存在且可读。

## 8. 技术栈

### 新增依赖

| 包 | 版本 | 用途 |
|------|------|------|
| `duckdb` | >=1.0.0 | 查询 Parquet 文件 |

### 移除依赖

| 包 | 原用途 |
|------|------|
| `meilisearch-python-sdk` | Meilisearch 异步客户端 |

### 保留依赖（ETL 本地使用）

| 包 | 用途 |
|------|------|
| `asyncpg` | PostgreSQL 异步驱动 |
| `psycopg2-binary` | PostgreSQL 同步驱动（ETL） |
| `sqlalchemy[asyncio]` | ORM（ETL 导入） |

### 生产运行时依赖

迁移后生产环境仅需：FastAPI + uvicorn + duckdb + Parquet 文件。不再需要 Meilisearch 和 PostgreSQL 服务。

## 9. 安全与配置

### 配置变更

**移除：**
- `MEILI_URL` — Meilisearch 连接地址
- `MEILI_MASTER_KEY` — Meilisearch 认证密钥

**新增：**
| 配置项 | 默认值 | 说明 |
|------|------|------|
| `DUCKDB_PARQUET_PATH` | `./data/books.parquet` | Parquet 文件路径 |
| `DUCKDB_MEMORY_LIMIT` | `256MB` | DuckDB 查询内存上限 |
| `DUCKDB_THREADS` | `2` | DuckDB 查询线程数 |

**保留：**
- `DATABASE_URL` — 本地 ETL 使用，生产可省略
- `CORS_ORIGINS` — 不变
- 其他应用配置 — 不变

### 部署配置

| 环境 | Parquet 路径 | 说明 |
|------|------|------|
| 本地开发 | `./data/books.parquet` | 相对于 backend 目录 |
| Railway 生产 | `/data/books.parquet` | Volume 挂载点 |

### Railway Volume

- Mount Path: `/data`
- 容量需求：约 3-5 GB（2000 万条元数据）
- 持久化：Volume 跨部署持久存在

## 10. API 规范

### 搜索端点（不变）

```
GET /api/search?q={keyword}&page={n}&page_size={n}
```

**响应格式（完全不变）：**
```json
{
  "total": 12345,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "id": "abc123md5",
      "title": "书名",
      "author": "作者",
      "formats": [
        {"extension": "epub", "filesize": 1234567, "download_url": "", "md5": "abc123md5"},
        {"extension": "pdf", "filesize": 2345678, "download_url": "", "md5": "def456md5"}
      ]
    }
  ],
  "total_books": 15
}
```

### 健康检查端点（字段变更）

```
GET /api/health
```

**响应格式（meilisearch → duckdb）：**
```json
{
  "status": "ok",
  "database": "ok",
  "duckdb": "ok"
}
```

## 11. 成功标准

### 功能要求

- ✅ 搜索 API 返回格式与迁移前完全一致
- ✅ 分页功能正常（page + page_size 参数）
- ✅ 多格式合并逻辑正常（同 title+author 合并为 formats 数组）
- ✅ 健康检查端点正常返回 DuckDB 状态
- ✅ 下载跳转功能不受影响
- ✅ 前端零改动，搜索和浏览体验无变化

### 质量指标

- ✅ 搜索响应时间 <5 秒（千万级数据）
- ✅ 全部现有测试通过
- ✅ ruff lint 检查通过
- ✅ Railway 部署后健康检查返回 ok

### 资源指标

- ✅ 移除 Meilisearch 服务（节省约 512MB-1GB 内存）
- ✅ 移除生产 PostgreSQL 服务（节省约 256MB 内存）
- ✅ Railway 仅运行 1 个后端服务 + 1 个 Volume

## 12. 实施阶段

### 阶段 1：核心搜索替换

**目标**：用 DuckDB 替换 Meilisearch 搜索服务

**交付物**：
- ✅ 新增 `duckdb` 依赖，移除 `meilisearch-python-sdk`
- ✅ 更新 `config.py`（移除 MEILI_*，新增 DUCKDB_*）
- ✅ 重写 `search_service.py`（DuckDB ILIKE 查询）
- ✅ 更新 `search.py` 异常处理
- ✅ 更新 `main.py` lifespan（移除 configure_index）

**验证**：单元测试通过

### 阶段 2：健康检查和 Schema

**目标**：更新健康检查逻辑

**交付物**：
- ✅ 更新 `HealthResponse` Schema（meilisearch → duckdb）
- ✅ 重写 `health.py` 健康检查逻辑

**验证**：健康检查端点正常响应

### 阶段 3：ETL 管线

**目标**：创建 PostgreSQL → Parquet 导出流程

**交付物**：
- ✅ 新增 `etl/export_parquet.py` 导出脚本
- ✅ 创建 `backend/data/` 目录和 `.gitignore`

**验证**：导出的 Parquet 文件可被 DuckDB 正常查询

### 阶段 4：部署配置和验证

**目标**：更新部署配置，完成端到端验证

**交付物**：
- ✅ 更新 `docker-compose.yml`（移除 Meilisearch）
- ✅ 更新后端 Dockerfile
- ✅ 更新 `.env` 模板
- ✅ 更新测试套件
- ✅ 本地端到端验证
- ✅ Railway 环境变量和 Volume 配置
- ✅ 生产部署验证

**验证**：生产环境搜索功能正常、前端无异常

## 13. 未来考虑

- **DuckDB FTS 索引** — 如搜索性能不满足需求，引入 Full-Text Search 扩展建立倒排索引
- **Parquet 自动更新** — 定时从数据源刷新 Parquet 文件（当前为手动导出上传）
- **多语言搜索优化** — 简繁体统一搜索、拼音搜索等
- **搜索结果排序** — 按相关度、下载量、文件大小等排序
- **增量数据更新** — 支持不重建整个 Parquet 文件的增量更新机制

## 14. 风险与缓解措施

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| ILIKE 全表扫描响应慢（>5s） | 中 | 用户体验下降 | 限制 page_size ≤100；后续可加 DuckDB FTS 索引 |
| Parquet 文件损坏/丢失 | 低 | 搜索完全不可用 | 保留本地备份 + 重新导出脚本，快速恢复 |
| Railway Volume 重部署丢失数据 | 低 | 需重新上传 Parquet | 测试 Volume 持久性；保留本地导出文件 |
| DuckDB 内存超限导致 OOM | 低 | 容器被 kill | 配置 memory_limit=256MB + threads=2 限制资源 |
| 搜索结果顺序与 Meilisearch 不同 | 高 | 用户感知变化 | 可接受 — Meilisearch 按相关度排序，DuckDB 按存储顺序，对用户影响小 |

## 15. 附录

### 不变项清单

| 模块 | 文件 | 原因 |
|------|------|------|
| 搜索 API 契约 | `api/v1/search.py` 的格式合并逻辑 | 前端依赖此格式 |
| 响应 Schema | `schemas/search.py` 的 BookFormat/BookResult/SearchResponse | 前端类型定义匹配 |
| SQLAlchemy 模型 | `models/book.py` | ETL 导入仍使用 |
| 数据库连接 | `database.py` | ETL 和健康检查仍使用 |
| 前端全部代码 | `frontend/src/**` | API 契约不变 |
| ETL 导入脚本 | `etl/import_annas.py` | 仍从 JSONL.zst 导入 PostgreSQL |
| 下载端点 | `api/v1/download.py` | 跳转 Anna's Archive 不变 |

### 回滚策略

如果迁移失败，可通过以下步骤回滚：
1. 恢复 `pyproject.toml` 中的 `meilisearch-python-sdk` 依赖
2. 恢复 `search_service.py` 到 Meilisearch 版本（从 git 历史恢复）
3. 恢复 Railway 环境变量（MEILI_URL、MEILI_MASTER_KEY）
4. 重新启动 Meilisearch 服务并触发索引同步

### 相关文档

- 实施计划：`rpiv/plans/plan-duckdb-search-migration.md`
- 已归档 PRD：`rpiv/archive/prd-download-source-optimization.md`（revised，范围缩减）
- 已归档 Plan：`rpiv/archive/plan-duckdb-async-download-r2.md`（superseded）
- 下载链路验证数据：`scripts/test_fixtures.json`
