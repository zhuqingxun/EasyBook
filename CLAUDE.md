# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

### Infrastructure
```bash
docker-compose up -d                    # 启动 PostgreSQL 16 + Meilisearch v1.35（注意：生产用 v1.9.0）
```

### Backend (FastAPI)
```bash
cd backend
uv sync                                 # 安装依赖
uv run uvicorn app.main:app --reload --port 8000   # 开发服务器
uv run pytest tests/ -v                 # 运行所有测试（17 个）
uv run pytest tests/test_search.py -k "test_merge"  # 按关键字过滤
uv run ruff check app/ etl/             # lint 检查
uv run ruff check app/ etl/ --fix       # lint 自动修复
```

### ETL
```bash
cd backend
uv run python -m etl.create_tables                          # 初始化数据库表
uv run python -m etl.import_annas /path/to/file.jsonl.zst   # 导入 Anna's Archive
uv run python -m etl.sync_meilisearch                       # 同步到 Meilisearch
```

### Frontend (Vue3 + Vite)
```bash
cd frontend
pnpm install                            # 安装依赖
pnpm dev                                # 开发服务器 (localhost:3000)
pnpm build                              # 生产构建（先 vue-tsc 类型检查，再 vite build）
```

## Architecture

BFF 架构，前后端分离 + IPFS 去中心化交付。

```
Vue3 前端 (:3000) → FastAPI 后端 (:8000) → Meilisearch (全文检索)
                                         → PostgreSQL (元数据持久化)
                                         → IPFS 网关 (电子书下载)
```

### Backend (`backend/app/`)
- **`main.py`** — FastAPI app 入口，lifespan 管理服务初始化（Meilisearch 客户端、数据库、APScheduler）
- **`config.py`** — Pydantic Settings，从 `.env` 读取配置
- **`services/search_service.py`** — 核心搜索逻辑：调用 Meilisearch，按 `(title, author)` 合并多格式为 `formats` 数组
- **`services/gateway_service.py`** — IPFS 网关管理：定期健康检查，选最快可用网关生成下载链接
- **`services/scheduler_service.py`** — APScheduler 3.x 定时触发网关健康检查
- **`api/v1/search.py`** — `GET /api/v1/search?q=&page=&page_size=`，返回 `SearchResponse`
- **`api/v1/download.py`** — `GET /api/v1/download/{id}`，返回最优下载链接

### ETL (`backend/etl/`)
- **`import_annas.py`** — 解压 JSONL.zst → 清洗过滤 → OpenCC 简繁转换 → 批量写入 PostgreSQL
- **`sync_meilisearch.py`** — PostgreSQL → Meilisearch 全量/增量同步

### Frontend (`frontend/src/`)
- **`composables/useSearch.ts`** — 搜索状态管理组合函数
- **`components/`** — SearchBox / BookList / BookItem（多格式下载按钮） / SearchPagination
- **`api/request.ts`** — Axios 实例，拦截器自动解包 `response.data`
- **`views/`** — Home（搜索入口）/ SearchPage（结果页）

## Key Technical Decisions

- **Meilisearch 异步 SDK**：使用 `meilisearch-python-sdk`（第三方异步），不是 `meilisearch`（官方同步）
- **APScheduler**：限制 3.x 版本（`>=3.10.0,<4.0.0`），4.x 仍为 alpha
- **OpenCC 初始化**：参数用 `"t2s"` 不是 `"t2s.json"`，SDK 内部自动加后缀
- **Meilisearch 分页**：用 `page` + `hits_per_page`（返回 totalHits），不用 `offset` + `limit`
- **JSONL.zst 解压**：必须设置 `max_window_size=2**31`
- **IPFS 网关**：`cloudflare-ipfs.com` 已退役(2024.8)，不要使用
- **Vue3 + Naive UI**：不能在 prop 上直接用 `v-model:value="propName"`，需用 `:value` + `@update:value`

## Production Deployment (Railway)

- **前端 URL**：`https://easybook.up.railway.app`
- **后端 API URL**：`https://easybook-api.up.railway.app`

Railway 服务与角色映射：

| Railway 服务名 | 角色 | Root Directory | 部署方式 | 端口 |
|---|---|---|---|---|
| `easybook-api` | 后端 API (FastAPI) | `/backend` | Dockerfile | 8080 |
| `easybook-frontend` | 前端 (Vue3 + nginx) | `/frontend` | Dockerfile | 80 |
| `Postgres` | 数据库 | - | Railway 模板 | - |
| `getmeili/meilisearch:v1.9.0` | 搜索引擎 | - | Railway 模板 | 3331 |

- Railway 原生支持 monorepo，通过 Root Directory 设置自动检测子目录 Dockerfile
- 环境变量支持 `${{ServiceName.VAR}}` 跨服务引用（可靠）
- 后端环境变量：`DATABASE_URL`（引用 PostgreSQL，config.py 自动转换 asyncpg 驱动）、`MEILI_URL`、`MEILI_MASTER_KEY`、`CORS_ORIGINS`
- 前端构建参数：`VITE_API_BASE_URL`（通过 Dockerfile ARG 在构建时注入后端 URL）
- 后端 Dockerfile 必须设置 `ENV PYTHONUNBUFFERED=1`，确保日志实时输出
- 推送 master 分支自动触发重新部署

### Zeabur（已弃用，暂保留）

Zeabur 部署存在痛点：Dockerfile 必须手动粘贴、`${}` 变量引用不解析、REMOVED 部署无日志。已迁移至 Railway。

## Development Notes

- **Vite allowedHosts**：配置了 `easybook.local`，本地开发用 `localhost:3000` 访问（需确认 hosts 配置）
- **后端端口**：容器内通过 `${PORT:-8080}` 动态控制，本地开发用 8000，Railway 用 8080
- **速率限制**：后端集成 slowapi，提供 API 限流
- **JSON 序列化**：使用 orjson 高性能序列化

## Code Conventions

- Python 3.12+，类型提示，ruff lint（line-length=100）
- SQLAlchemy 2.0 ORM（`Mapped[]` + `mapped_column`），asyncpg 异步驱动
- Pydantic v2 schema（`model_config = ConfigDict(from_attributes=True)`）
- 服务层用全局单例模式，lifespan 中初始化
- pytest 异步模式：`asyncio_mode = "auto"`
- 前端 Vue3 组合式 API + TypeScript，Naive UI 组件自动导入（unplugin）
- Vite 代理 `/api` 到后端，前端无需处理 CORS

## Data Flow

搜索结果合并逻辑：Meilisearch 返回的多条记录按 `(title.lower(), author.lower())` 分组，同一本书的不同格式（epub/pdf/mobi/azw3）合并为 `formats` 数组，每个 format 包含 `extension`、`filesize`、`download_url`。

ETL 过滤规则：仅保留 epub/pdf/mobi/azw3 格式、中英文、有 MD5 的记录。简繁体通过 OpenCC `t2s` 统一为简体。
