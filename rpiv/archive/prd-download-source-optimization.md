---
description: "产品需求文档: 架构迁移 — DuckDB 轻量搜索 + 异步代理下载 + R2 中转"
status: archived
created_at: 2026-02-08T20:30:00
updated_at: 2026-02-09T17:00:00
archived_at: 2026-02-09T17:00:00
supersedes: null
revision_note: "2026-02-09 下载链路验证结论：服务端代理下载不可行（所有下载源有反爬保护），范围缩减为仅 DuckDB 搜索迁移。详见 scripts/test_fixtures.json 和 rpiv/plans/plan-duckdb-search-migration.md"
---

# 架构迁移：DuckDB 轻量搜索 + 异步代理下载 + R2 中转

## 1. 执行摘要

EasyBook 当前架构存在两个根本性问题：

1. **下载方案无效**：当前的"前端跳转外站"方案（LibGen/Anna's Archive）对中国大陆用户完全无效，因为这些站点在国内被墙，用户无法直接访问。
2. **搜索引擎过重**：Meilisearch 在 Railway Hobby Plan 上的内存和存储需求（20GB+ 数据索引）远超平台承载能力。

本次迁移的核心目标：**从"全量搜索引擎 + 前端跳转"转型为"DuckDB 轻量索引 + 异步代理下载 + R2 中转"，让中国大陆用户真正能搜索并下载到电子书。**

关键技术决策：
- **DuckDB + Parquet** 替代 Meilisearch（零常驻进程，1-3GB 文件即可承载千万级元数据）
- **后端代理下载** 替代前端跳转（服务器代用户从 LibGen 下载，绕过网络封锁）
- **Cloudflare R2** 作为中转存储（出口流量免费，预签名链接交付，7 天自动清理）
- **移除 PostgreSQL 和 Meilisearch**，Railway 上只保留 API 容器 + Volume

## 2. 使命

**使命声明**：让中国大陆用户搜索电子书后，无需翻墙即可完成下载，整个过程在 EasyBook 内闭环完成。

**核心原则**：

1. **Bridge the Wall** — 服务器作为中转代理，解决用户无法连接数据源的问题
2. **Store Metadata, Fetch Content** — 本地只存元数据（Parquet 文件），电子书文件按需获取
3. **Async by Default** — 用户请求 → 任务队列 → 后台下载 → 中转存储 → 通知用户
4. **极低成本** — 零数据库服务、R2 出口流量免费、Railway Hobby Plan 可承载
5. **MD5 为锚** — 所有操作基于 MD5 定位，与数据源天然兼容

## 3. 目标用户

**主要用户角色**：中国大陆电子书读者

- **网络环境**：无法直接访问 LibGen、Anna's Archive、IPFS 等国外资源站
- **技术舒适度**：基础互联网用户，能理解"点击下载 → 等待准备 → 获取链接"的流程
- **关键需求**：搜索到书后，能在 EasyBook 内直接获得可下载的链接
- **痛点**：
  - 当前下载链接跳转到外站，打不开
  - 不会翻墙或不愿为偶尔的下载需求付费购买 VPN
  - 搜索体验尚可，但"最后一公里"的下载体验断裂

**次要用户角色**：平台运维人员

- **关键需求**：当 LibGen 镜像域名变更时，通过环境变量快速切换
- **痛点**：LibGen 镜像偶尔宕机，需要能快速切换到备用镜像

**规模假设**：~100 用户，日均 <100 次搜索请求，<50 次下载请求。

## 4. MVP 范围

### 范围内

**后端核心**
- 新增 DuckDB + Parquet 搜索模块，替代 Meilisearch
- 新增异步下载任务系统（SQLite job queue + background worker）
- 新增 LibGen 资源解析器（MD5 → 真实下载链接）
- 新增 Cloudflare R2 上传模块（预签名链接生成）
- 新增下载任务 API 端点（创建任务、查询状态）
- 移除 Meilisearch 相关代码和依赖
- 移除 PostgreSQL 相关代码和依赖（生产环境）

**前端变更**
- 重构下载交互：从"跳转外站"改为"异步下载 + 状态轮询"
- 新增下载状态 UI（准备中 → 下载中 → 可下载 → 已过期）
- 移除所有外站跳转相关代码
- 搜索 API 对接 DuckDB 后端

**数据管线**
- 新增 PostgreSQL → Parquet 导出脚本（本地执行）
- Parquet 文件部署到 Railway Volume

**部署变更**
- Railway 移除 PostgreSQL 和 Meilisearch 服务
- Railway easybook-api 挂载 Volume（存储 Parquet + SQLite）
- 新增 Cloudflare R2 bucket 配置

### 范围外

- 用户注册/登录系统（MVP 无身份认证）
- 下载次数限制/配额管理
- 多 Worker 并行下载（MVP 单 Worker 足够）
- 电子书格式转换
- 搜索结果排序优化（如按相关度、年份排序）
- 书籍封面、简介等元数据增强
- 前端 PWA / 离线支持

## 5. 用户故事

### US-1：中国大陆用户完整下载体验

作为中国大陆的电子书读者，我想要在 EasyBook 内搜索并下载电子书，无需访问任何被墙的外部网站。

**流程**：
1. 用户搜索"三体" → 看到结果列表
2. 点击 EPUB 格式的"下载"按钮 → 按钮变为"准备中..."
3. 等待 10-60 秒（后台从 LibGen 下载并上传到 R2）
4. 状态变为"可下载" → 用户点击获得 R2 预签名链接
5. 浏览器开始从 Cloudflare R2 下载文件

### US-2：DuckDB 搜索体验

作为电子书读者，我想要通过关键词搜索中英文电子书，并看到匹配的结果列表。

**示例**：用户搜索"python" → DuckDB 在 Parquet 中执行 ILIKE 查询 → 返回书名或作者包含"python"的所有中英文书籍，按年份降序排列。

### US-3：下载任务状态查询

作为电子书读者，我想要实时了解我的下载请求进度，以便知道何时可以下载。

**状态流转**：`pending`（已提交）→ `processing`（下载中）→ `done`（可下载，附带 R2 链接）→ `expired`（链接已过期）/ `failed`（下载失败）

### US-4：环境变量切换镜像

作为运维人员，我想要通过修改环境变量来切换 LibGen 镜像地址，以便在镜像宕机时快速恢复。

**示例**：`library.lol` 宕机 → 修改 `LIBGEN_MIRROR_URL` 为 `https://libgen.li` → 服务自动使用新镜像。

### US-5：R2 文件自动清理

作为系统，我应该自动清理 R2 中过期的文件，以便控制存储成本。

**规则**：R2 对象生命周期设为 7 天，过期后自动删除。对应的 SQLite 任务记录标记为 `expired`。

## 6. 核心架构

### 6.1 高级架构

```
用户（中国大陆）
    ↓ HTTPS
Vue3 前端（Railway / nginx）
    ↓ API 调用
FastAPI 后端（Railway 容器）
    ├── GET /api/v1/search → DuckDB 查询 Parquet 文件
    ├── POST /api/v1/download-tasks → 创建下载任务（写入 SQLite）
    ├── GET /api/v1/download-tasks/{id} → 查询任务状态
    └── Background Worker（APScheduler / asyncio loop）
         ├── 1. 从 SQLite 取 pending 任务
         ├── 2. 请求 library.lol/main/{MD5}，解析真实下载链接
         ├── 3. 流式下载文件到 /tmp
         ├── 4. 上传至 Cloudflare R2
         └── 5. 生成预签名 URL，更新任务状态为 done

Railway Volume（挂载到容器）
    ├── books.parquet        ← DuckDB 查询的数据文件
    └── jobs.db              ← SQLite 任务队列

Cloudflare R2（外部对象存储）
    └── ebooks/{md5}.{ext}   ← 7 天自动过期
         ↑
用户通过预签名 URL 直接从 R2 下载
```

### 6.2 后端模块划分

```
backend/app/
├── main.py                          # FastAPI app + lifespan（初始化 Worker）
├── config.py                        # Pydantic Settings（新增 R2、LibGen 配置）
├── services/
│   ├── search_service.py            # 重构：DuckDB + Parquet 查询
│   ├── download_task_service.py     # 新增：任务创建、状态查询
│   ├── libgen_resolver.py           # 新增：MD5 → 真实下载链接解析
│   ├── r2_service.py                # 新增：R2 上传 + 预签名链接生成
│   └── worker_service.py            # 新增：后台 Worker（任务消费循环）
├── api/v1/
│   ├── search.py                    # 重构：对接 DuckDB 搜索
│   └── download_tasks.py            # 新增：下载任务 API
├── schemas/
│   ├── search.py                    # 调整：移除 Meilisearch 特有字段
│   └── download.py                  # 新增：任务请求/响应模型
└── db/
    └── sqlite.py                    # 新增：SQLite 连接管理 + 表定义
```

### 6.3 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 搜索引擎 | DuckDB + Parquet | 零常驻进程，文件级部署，Railway Volume 可承载 |
| 下载模式 | 后端代理 | 用户在中国大陆无法直连 LibGen |
| 中转存储 | Cloudflare R2 | 出口流量免费，S3 兼容，预签名链接 |
| 任务队列 | SQLite | 并发极低（<50/天），无需 Redis |
| 生产数据库 | 无 | 移除 PG 和 Meilisearch，降低成本 |
| 文件解析 | HTML 解析 library.lol | 两步跳转获取真实下载链接 |

## 7. 功能详细规范

### 7.1 DuckDB 搜索

**数据文件**：`books.parquet`，存储在 Railway Volume

**Parquet schema**：

| 列名 | 类型 | 说明 |
|------|------|------|
| `md5` | string | 主键，文件 MD5 |
| `title` | string | 书名（已 OpenCC 简体化） |
| `author` | string | 作者 |
| `year` | string | 出版年份 |
| `extension` | string | 文件格式（epub/pdf/mobi/azw3） |
| `filesize` | int64 | 文件大小（bytes） |
| `language` | string | 语言（zh/en） |

**查询逻辑**：

```python
import duckdb

def search_books(query: str, page: int = 1, page_size: int = 20):
    con = duckdb.connect()  # 每次查询瞬时连接，无常驻进程
    offset = (page - 1) * page_size

    # 子串匹配，对中文和英文均有效
    sql = """
        SELECT md5, title, author, year, extension, filesize, language
        FROM 'data/books.parquet'
        WHERE title ILIKE ? OR author ILIKE ?
        ORDER BY year DESC NULLS LAST
        LIMIT ? OFFSET ?
    """
    pattern = f"%{query}%"
    results = con.execute(sql, [pattern, pattern, page_size, offset]).fetchall()

    # 总数查询
    count_sql = """
        SELECT COUNT(*)
        FROM 'data/books.parquet'
        WHERE title ILIKE ? OR author ILIKE ?
    """
    total = con.execute(count_sql, [pattern, pattern]).fetchone()[0]

    return results, total
```

**结果合并**：保持现有逻辑，按 `(title.lower(), author.lower())` 分组，同一本书的不同格式合并为 `formats` 数组。

**性能预期**：
- Parquet 列式存储 + DuckDB 向量化执行，1000 万级数据 ILIKE 查询预计 100-500ms
- 首次查询需要加载 Parquet 到内存映射，后续查询更快
- 可通过 DuckDB 持久化连接 + 预热进一步优化

### 7.2 异步下载任务系统

**SQLite 表结构**（`jobs.db`）：

```sql
CREATE TABLE IF NOT EXISTS download_tasks (
    id TEXT PRIMARY KEY,           -- UUID
    md5 TEXT NOT NULL,
    extension TEXT NOT NULL,       -- epub/pdf/mobi/azw3
    title TEXT,                    -- 书名（用于日志和前端展示）
    status TEXT NOT NULL DEFAULT 'pending',  -- pending/processing/done/failed/expired
    download_url TEXT,             -- R2 预签名 URL（status=done 时填充）
    error_message TEXT,            -- 失败原因（status=failed 时填充）
    created_at TEXT NOT NULL,      -- ISO 8601
    updated_at TEXT NOT NULL,
    expires_at TEXT                -- R2 链接过期时间
);

CREATE INDEX IF NOT EXISTS idx_status ON download_tasks(status);
CREATE INDEX IF NOT EXISTS idx_md5 ON download_tasks(md5);
```

**任务去重**：同一 MD5 + extension 如果已有 `done` 且未过期的任务，直接返回已有链接，不重复下载。

### 7.3 LibGen 资源解析器

**解析流程**（两步跳转）：

1. **Step 1**：`GET {LIBGEN_MIRROR_URL}/main/{MD5}`
2. **Step 2**：解析 HTML，提取 `<a>` 标签中的真实下载链接（通常指向 `GET` 或 `Cloudflare` 镜像）
3. **Step 3**：流式下载文件到 `/tmp/{md5}.{ext}`

**错误处理**：
- library.lol 返回 403/500 → 记录 WARNING，标记任务 `failed`
- 解析不到下载链接 → 标记任务 `failed`，附带错误信息
- 下载超时（默认 300 秒）→ 标记任务 `failed`
- 文件大小校验：如果下载文件 < 1KB，视为无效，标记 `failed`

**备用镜像**：通过环境变量 `LIBGEN_FALLBACK_URL` 配置备用镜像，主镜像失败时自动尝试备用。

### 7.4 Cloudflare R2 集成

**Bucket 配置**：
- Bucket 名称：`easybook-downloads`（通过环境变量配置）
- 对象路径：`ebooks/{md5}.{ext}`
- 生命周期规则：7 天后自动删除

**上传流程**：
1. Worker 下载文件到 `/tmp`
2. 使用 boto3（S3 兼容）上传到 R2
3. 设置 `Content-Disposition: attachment; filename="{title}.{ext}"`
4. 生成预签名 GET URL（有效期 24 小时）
5. 删除 `/tmp` 临时文件

**R2 缓存复用**：上传前先检查 R2 中是否已存在 `ebooks/{md5}.{ext}`，如存在则直接生成新的预签名链接，跳过下载和上传。

### 7.5 后台 Worker

**运行模式**：FastAPI lifespan 中启动 asyncio 后台任务，每 10 秒轮询 SQLite 中的 `pending` 任务。

**并发控制**：MVP 阶段单任务串行执行（一次只处理一个下载），避免 LibGen 限流。

**处理流程**：
1. 查询 `status='pending'` 且 `created_at` 最早的任务
2. 更新状态为 `processing`
3. 检查 R2 缓存 → 命中则直接生成链接
4. 调用 LibGen 解析器获取真实链接
5. 流式下载到 `/tmp`
6. 上传至 R2
7. 生成预签名 URL
8. 更新状态为 `done`，填充 `download_url` 和 `expires_at`
9. 异常时更新状态为 `failed`，填充 `error_message`

**过期清理**：每小时扫描 `done` 状态的任务，将 `expires_at < now()` 的标记为 `expired`。

## 8. 技术栈

### 后端变更

| 组件 | 技术 | 说明 |
|------|------|------|
| 搜索引擎 | `duckdb`（新增） | 查询 Parquet 文件，替代 Meilisearch |
| 任务队列 | `sqlite3`（标准库） | 下载任务管理，无需额外依赖 |
| HTTP 客户端 | `httpx`（已有） | LibGen 页面请求 + 文件下载 |
| HTML 解析 | `beautifulsoup4`（新增） | 解析 LibGen 中间页提取下载链接 |
| 对象存储 | `boto3`（新增） | Cloudflare R2 上传（S3 兼容 API） |
| 定时任务 | `asyncio`（标准库） | 后台 Worker 循环，替代 APScheduler |
| 数据导出 | `pyarrow` / `pandas`（本地脚本） | PG → Parquet 导出 |

**移除的依赖**：
- `meilisearch-python-sdk`
- `sqlalchemy` + `asyncpg`（生产环境不再需要 PG）
- `apscheduler`（用 asyncio 替代）

### 前端变更

| 组件 | 说明 |
|------|------|
| `BookItem.vue` | 重构下载交互：移除外站跳转，改为异步下载按钮 |
| `composables/useDownloadTask.ts` | 新增：下载任务创建 + 状态轮询 |
| `types/download.ts` | 新增：下载任务类型定义 |
| `api/request.ts` | 已有 axios 实例，直接复用 |

无需新增前端依赖。

## 9. API 规范

### 9.1 搜索 API（重构）

**`GET /api/v1/search`**

保持现有接口契约不变，后端实现从 Meilisearch 切换为 DuckDB。

| 参数 | 类型 | 说明 |
|------|------|------|
| `q` | string | 搜索关键词 |
| `page` | int | 页码（默认 1） |
| `page_size` | int | 每页条数（默认 20） |

**响应格式**：保持现有 `SearchResponse` 格式不变（`books` 数组 + `total` + `page` 等）。

### 9.2 创建下载任务

**`POST /api/v1/download-tasks`**

请求体：
```json
{
  "md5": "a1b2c3d4e5f6...",
  "extension": "epub",
  "title": "三体"
}
```

响应：
```json
{
  "task_id": "uuid-xxx",
  "status": "pending",
  "message": "下载任务已提交，请稍候查询状态"
}
```

**去重逻辑**：如果同一 `md5` + `extension` 已有 `done` 且未过期的任务，直接返回：
```json
{
  "task_id": "existing-uuid",
  "status": "done",
  "download_url": "https://r2.example.com/...",
  "expires_at": "2026-02-15T22:00:00Z"
}
```

### 9.3 查询下载任务状态

**`GET /api/v1/download-tasks/{task_id}`**

响应：
```json
{
  "task_id": "uuid-xxx",
  "md5": "a1b2c3d4e5f6...",
  "title": "三体",
  "status": "done",
  "download_url": "https://r2.example.com/presigned-url...",
  "expires_at": "2026-02-15T22:00:00Z",
  "error_message": null,
  "created_at": "2026-02-08T22:00:00Z"
}
```

**状态枚举**：

| status | 含义 | download_url |
|--------|------|-------------|
| `pending` | 排队等待 | null |
| `processing` | 正在下载 | null |
| `done` | 可下载 | 预签名 URL |
| `failed` | 下载失败 | null（有 error_message） |
| `expired` | 链接已过期 | null |

## 10. 数据管线

### 10.1 本地数据准备

```
Anna's Archive JSONL.zst
    ↓ 现有 ETL（import_annas.py）
本地 PostgreSQL（20GB 已清洗数据）
    ↓ 新增导出脚本（export_parquet.py）
books.parquet（预估 1-3GB）
    ↓ 手动上传或 CI/CD
Railway Volume /data/books.parquet
```

**导出脚本**（`backend/etl/export_parquet.py`）：
- 从 PostgreSQL 读取中英文记录
- 选取字段：md5, title, author, year, extension, filesize, language
- 导出为 Parquet 格式（snappy 压缩）
- 输出文件统计信息（记录数、文件大小）

### 10.2 数据更新流程

1. 本地下载新的 Anna's Archive dump
2. 运行 ETL 导入到本地 PG
3. 运行导出脚本生成新的 Parquet
4. 上传新 Parquet 到 Railway Volume（覆盖旧文件）
5. 重启 API 容器使 DuckDB 加载新数据

预计更新频率：每月一次或按需。

## 11. 环境变量与配置

### 后端环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `PARQUET_PATH` | `data/books.parquet` | Parquet 数据文件路径 |
| `SQLITE_PATH` | `data/jobs.db` | SQLite 任务数据库路径 |
| `LIBGEN_MIRROR_URL` | `https://library.lol` | LibGen 主镜像地址 |
| `LIBGEN_FALLBACK_URL` | `https://libgen.li` | LibGen 备用镜像地址 |
| `R2_ENDPOINT_URL` | - | Cloudflare R2 S3 兼容端点 |
| `R2_ACCESS_KEY_ID` | - | R2 访问密钥 |
| `R2_SECRET_ACCESS_KEY` | - | R2 密钥 |
| `R2_BUCKET_NAME` | `easybook-downloads` | R2 bucket 名称 |
| `R2_PUBLIC_URL` | - | R2 公开访问 URL（用于预签名链接） |
| `DOWNLOAD_TIMEOUT` | `300` | 下载超时秒数 |
| `PRESIGNED_URL_EXPIRY` | `86400` | 预签名链接有效期（秒，默认 24h） |
| `CORS_ORIGINS` | `["*"]` | CORS 允许的来源 |
| `WORKER_POLL_INTERVAL` | `10` | Worker 轮询间隔（秒） |

### Railway 部署配置

| Railway 服务 | 角色 | 变更 |
|-------------|------|------|
| `easybook-api` | 后端 API + Worker | 挂载 Volume 到 `/app/data`，新增 R2 环境变量 |
| `easybook-frontend` | 前端 nginx | 无变更 |
| ~~`Postgres`~~ | ~~数据库~~ | **移除** |
| ~~`Meilisearch`~~ | ~~搜索引擎~~ | **移除** |

**Railway Volume**：
- 挂载点：`/app/data`
- 内容：`books.parquet`（1-3GB）+ `jobs.db`（极小）
- 预估费用：$0.25/GB/月 × 3GB ≈ $0.75/月

## 12. 安全考虑

### 法律风险

- EasyBook 服务器代理下载文件，法律风险高于纯跳转方案
- R2 文件 7 天自动删除，不做长期存储
- 预签名链接有时效性，减少文件被滥用传播的风险
- 建议：在页面底部添加免责声明

### 配置安全

- R2 密钥通过环境变量传递，不硬编码
- 预签名 URL 通过 HTTPS 传输
- SQLite 文件在 Volume 上，容器外不可访问

### 防滥用

- MVP 阶段不设身份认证，但通过以下措施减少滥用：
  - 同一 MD5 不重复下载（R2 缓存 + 任务去重）
  - 单 Worker 串行处理，天然限流
  - 可选：后续添加 IP 级别的速率限制

## 13. 前端交互设计

### 13.1 搜索结果页（变更最小）

搜索框和结果列表保持不变。每本书的格式按钮从"跳转外站 popover"改为"下载按钮"。

### 13.2 下载按钮状态机

```
[EPUB] [PDF] [MOBI]     ← 初始状态，可点击
    ↓ 点击
[准备中...]               ← pending/processing，禁用状态，显示 loading
    ↓ 轮询（每 3 秒）
[立即下载]                ← done，可点击，跳转到预签名 URL
    或
[下载失败 ↻]             ← failed，可点击重试
```

### 13.3 轮询策略

- 用户点击下载 → 创建任务 → 立即开始轮询
- 轮询间隔：前 30 秒每 3 秒一次，之后每 10 秒一次
- 最大轮询时间：5 分钟（超时后显示"请稍后刷新查看"）
- 页面离开后停止轮询
- 页面重新进入时，如果有未完成的任务，恢复轮询

## 14. 成功标准

### MVP 成功定义

中国大陆用户（无 VPN）搜索任意中英文书籍后，点击下载按钮，等待 10-60 秒，成功获得电子书文件。

### 功能要求

- DuckDB 搜索能在 1 秒内返回结果
- 下载任务从创建到完成在 60 秒内（取决于文件大小和 LibGen 速度）
- R2 预签名链接可正常下载
- 同一文件不重复下载（R2 缓存命中）
- 环境变量修改后无需改代码即可切换镜像
- Railway 单容器 + Volume 稳定运行

### 质量指标

- 搜索 API 响应时间 < 1s（DuckDB 查询）
- 下载任务 API 响应时间 < 50ms（SQLite 写入）
- Worker 不阻塞 API 请求（异步执行）
- R2 下载速度不受服务器带宽限制（用户直连 Cloudflare CDN）

## 15. 实施阶段

### 阶段一：数据管线（本地）

**目标**：验证 DuckDB + Parquet 方案可行性

**交付物**：
- `backend/etl/export_parquet.py` — PG → Parquet 导出脚本
- 验证 DuckDB 查询性能（中文 ILIKE 子串匹配）
- 确认 Parquet 文件大小在预期范围内

**验证标准**：Parquet 文件生成成功，DuckDB 查询 1000 万级数据 < 1 秒

### 阶段二：后端核心服务

**目标**：实现搜索 + 异步下载 + R2 中转的后端完整链路

**交付物**：
- `services/search_service.py` 重构为 DuckDB
- `services/download_task_service.py` — 任务 CRUD
- `services/libgen_resolver.py` — LibGen 解析
- `services/r2_service.py` — R2 上传 + 预签名
- `services/worker_service.py` — 后台 Worker
- `db/sqlite.py` — SQLite 管理
- `api/v1/download_tasks.py` — 下载任务 API
- 移除 Meilisearch 和 PostgreSQL 依赖

**验证标准**：`curl` 测试搜索和下载全流程通过

### 阶段三：前端重构

**目标**：前端对接新的搜索和下载 API

**交付物**：
- `BookItem.vue` 重构下载交互
- `composables/useDownloadTask.ts` — 任务轮询
- `types/download.ts` — 类型定义
- 移除所有外站跳转代码

**验证标准**：本地开发环境搜索并下载全流程通过

### 阶段四：部署与验证

**目标**：Railway 生产环境部署

**交付物**：
- Railway Volume 配置 + Parquet 上传
- Cloudflare R2 bucket 创建 + 生命周期规则
- 后端环境变量配置
- Railway 移除 PG 和 Meilisearch 服务
- 生产环境端到端验证

**验证标准**：`https://easybook.up.railway.app` 搜索并下载成功

## 16. 风险与缓解措施

### 风险 1：LibGen 镜像不可用

- **概率**：中
- **影响**：所有下载任务失败
- **缓解**：`LIBGEN_FALLBACK_URL` 备用镜像自动降级；多镜像列表（未来增强）

### 风险 2：DuckDB 中文搜索体验不佳

- **概率**：低（子串匹配对中文有效）
- **影响**：搜索结果不如 Meilisearch 精确
- **缓解**：ETL 阶段已做 OpenCC 简繁统一；后续可考虑 SQLite FTS5 或轻量搜索方案升级

### 风险 3：LibGen 反爬/限流

- **概率**：中
- **影响**：下载速度降低或被封 IP
- **缓解**：单 Worker 串行处理天然限流；R2 缓存减少重复请求；可增加请求间隔

### 风险 4：R2 成本超预期

- **概率**：低（出口流量免费，存储 7 天自动清理）
- **影响**：月度费用增加
- **缓解**：R2 免费额度（10GB 存储 / 月，100 万次 A 类操作）对 MVP 规模绰绰有余

### 风险 5：Railway Volume 数据丢失

- **概率**：极低
- **影响**：Parquet 文件丢失需重新上传；SQLite 任务历史丢失（可接受）
- **缓解**：Parquet 文件在本地有备份；SQLite 中的任务是临时性数据

### 风险 6：Cloudflare R2 在中国大陆的访问速度

- **概率**：低（Cloudflare 在中国有 CDN 节点）
- **影响**：下载速度可能不够快
- **缓解**：Cloudflare CDN 全球覆盖，中国大陆通常可达；如不理想可考虑其他 CDN

## 17. 未来考虑

### MVP 后增强

- **用户认证 + 配额**：添加简单的用户系统，限制每日下载次数
- **多 Worker 并行**：提升下载吞吐量
- **搜索升级**：SQLite FTS5 或轻量 Meilisearch（减少数据量后）提升搜索体验
- **Z-Library 集成**：作为 LibGen 的备用下载源
- **下载历史**：用户可查看近期下载记录

### 中长期考虑

- **书籍元数据增强**：接入 Open Library API 补充封面、简介
- **用户反馈系统**："这本书下载成功/失败"反馈，优化解析器
- **多数据源**：扩展到学术论文（Sci-Hub）等其他资源
- **本地缓存**：高频请求的书籍 Parquet 元数据热缓存

## 18. 附录

### 与前一版 PRD 的关系

本 PRD 取代 `prd-download-source-optimization.md` 的原始版本（"多源降级 + LibGen 集成"）。原始版本基于"前端跳转"假设，该假设对中国大陆用户无效。

### Gemini 建议的采纳情况

参考文档：`rpiv/requirements/Gemini.md`

| Gemini 建议 | 采纳情况 |
|------------|---------|
| DuckDB + Parquet 替代 Meilisearch | 完全采纳 |
| SQLite 替代 Redis 做任务队列 | 完全采纳 |
| Cloudflare R2 中转存储 | 完全采纳 |
| 异步代购模式 | 完全采纳 |
| library.lol HTML 两步解析 | 完全采纳 |
| Railway Volume 存储 Parquet | 完全采纳 |

### 关键文件（变更）

| 文件 | 角色 | 变更类型 |
|------|------|---------|
| `backend/app/services/search_service.py` | 搜索服务 | 重构（DuckDB） |
| `backend/app/services/download_task_service.py` | 任务管理 | 新增 |
| `backend/app/services/libgen_resolver.py` | LibGen 解析 | 新增 |
| `backend/app/services/r2_service.py` | R2 存储 | 新增 |
| `backend/app/services/worker_service.py` | 后台 Worker | 新增 |
| `backend/app/db/sqlite.py` | SQLite 管理 | 新增 |
| `backend/app/api/v1/download_tasks.py` | 下载任务 API | 新增 |
| `backend/app/config.py` | 配置 | 修改（新增 R2/LibGen/DuckDB 配置） |
| `backend/app/main.py` | 应用入口 | 修改（Worker 启动、移除 PG/Meili） |
| `backend/etl/export_parquet.py` | 数据导出 | 新增 |
| `frontend/src/components/BookItem.vue` | 下载 UI | 重构 |
| `frontend/src/composables/useDownloadTask.ts` | 下载任务 | 新增 |
| `frontend/src/types/download.ts` | 类型定义 | 新增 |

### 前置文档

- `rpiv/requirements/prd-ebook-search-platform.md`（已完成）— 原始 MVP
- `rpiv/requirements/Gemini.md` — Gemini 架构建议（参考）
