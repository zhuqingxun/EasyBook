# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

### Infrastructure
```bash
docker-compose up -d                    # 启动 PostgreSQL 16（仅用于 ETL 导入阶段）
```

### Backend (FastAPI)
```bash
cd backend
uv sync                                 # 安装依赖
uv run uvicorn app.main:app --reload --port 8000   # 开发服务器
uv run pytest tests/ -v                 # 运行所有测试（11 个）
uv run pytest tests/test_search.py -k "test_merge"  # 按关键字过滤
uv run ruff check app/ etl/             # lint 检查
uv run ruff check app/ etl/ --fix       # lint 自动修复
```

### ETL
```bash
cd backend
uv run python -m etl.create_tables                          # 初始化数据库表
uv run python -m etl.import_annas /path/to/file.jsonl.zst   # 导入 Anna's Archive → PostgreSQL
uv run python -m etl.export_parquet                         # PostgreSQL → Parquet 导出
```

### Frontend (Vue3 + Vite)
```bash
cd frontend
pnpm install                            # 安装依赖
pnpm dev                                # 开发服务器 (localhost:3000)
pnpm build                              # 生产构建（先 vue-tsc 类型检查，再 vite build）
```

## Architecture

BFF 架构，前后端分离。搜索基于 DuckDB httpfs 远程查询华为云 OBS 上的 Parquet 文件。

```
Vue3 前端 (:3000) → FastAPI 后端 (:8000) → DuckDB httpfs → 华为云 OBS (s3://easybook-parquet/books.parquet)
```

### Backend (`backend/app/`)
- **`main.py`** — FastAPI app 入口，lifespan 管理 DuckDB 搜索服务初始化
- **`config.py`** — Pydantic Settings，从 `.env` 读取配置（DuckDB、OBS S3 凭证等）
- **`services/search_service.py`** — 核心搜索逻辑：双模式（本地/远程 OBS），DuckDB httpfs + ILIKE 查询，前端负责多格式合并
- **`api/v1/search.py`** — `GET /api/v1/search?q=&page=&page_size=`，返回 `SearchResponse`
- **`api/v1/health.py`** — 健康检查，验证 SearchService 初始化状态

### ETL (`backend/etl/`)
- **`import_annas.py`** — 解压 JSONL.zst → 清洗过滤 → OpenCC 简繁转换 → 批量写入 PostgreSQL
- **`export_parquet.py`** — PostgreSQL → Parquet 导出（DuckDB postgres 扩展，Snappy 压缩，Row Group 100,000）

### Frontend (`frontend/src/`)
- **`composables/useSearch.ts`** — 搜索状态管理组合函数
- **`components/`** — SearchBox / BookList / BookItem（多格式下载按钮） / SearchPagination
- **`api/request.ts`** — Axios 实例，拦截器自动解包 `response.data`
- **`views/`** — Home（搜索入口）/ SearchPage（结果页）

## Key Technical Decisions

- **DuckDB httpfs + 华为云 OBS**：DuckDB 通过 httpfs 扩展远程查询 OBS 上的 Parquet（S3 协议），无需本地存储
- **SearchService 双模式**：优先本地 Parquet 文件，检测到 OBS 凭证时自动切换远程模式
- **DuckDB 每请求独立连接**：DuckDB 非线程安全，每次搜索创建新连接（远程模式下加载 httpfs）
- **asyncio.to_thread()**：桥接同步 DuckDB 查询与 async FastAPI
- **ILIKE 子串匹配**：远程 OBS ~55-63 秒/次，本地 ~15-38 秒（取决于线程数），已知性能瓶颈
- **OpenCC 初始化**：参数用 `"t2s"` 不是 `"t2s.json"`，SDK 内部自动加后缀
- **JSONL.zst 解压**：必须设置 `max_window_size=2**31`
- **Vue3 + Naive UI**：不能在 prop 上直接用 `v-model:value="propName"`，需用 `:value` + `@update:value`

## Production Deployment (Railway)

- **前端 URL**：`https://easybook.up.railway.app`
- **后端 API URL**：`https://easybook-api.up.railway.app`

Railway 服务与角色映射：

| Railway 服务名 | 角色 | Root Directory | 部署方式 | 端口 |
|---|---|---|---|---|
| `easybook-api` | 后端 API (FastAPI) | `/backend` | Dockerfile | 8080 |
| `easybook-frontend` | 前端 (Vue3 + nginx) | `/frontend` | Dockerfile | 80 |

- Railway 原生支持 monorepo，通过 Root Directory 设置自动检测子目录 Dockerfile
- 后端环境变量：`DUCKDB_PARQUET_PATH`、`DUCKDB_MEMORY_LIMIT`、`DUCKDB_THREADS`、`CORS_ORIGINS`、`OBS_ACCESS_KEY_ID`、`OBS_SECRET_ACCESS_KEY`、`OBS_ENDPOINT`、`OBS_BUCKET`、`OBS_PARQUET_KEY`
- 前端构建参数：`VITE_API_BASE_URL`（通过 Dockerfile ARG 在构建时注入后端 URL）
- 后端 Dockerfile 必须设置 `ENV PYTHONUNBUFFERED=1`，确保日志实时输出
- 推送 master 分支自动触发重新部署
- **Parquet 文件存储**：华为云 OBS `s3://easybook-parquet/books.parquet`（新加坡 ap-southeast-3，与 Railway 同区）

## Development Notes

- **Vite allowedHosts**：配置了 `easybook.local`，本地开发用 `localhost:3000` 访问（需确认 hosts 配置）
- **后端端口**：容器内通过 `${PORT:-8080}` 动态控制，本地开发用 8000，Railway 用 8080
- **速率限制**：后端集成 slowapi，提供 API 限流
- **JSON 序列化**：使用 orjson 高性能序列化
- **Parquet 数据**：6.8GB，59M 条记录，存储于华为云 OBS（本地副本 `backend/data/books.parquet` 已 .gitignore 排除）

## Code Conventions

- Python 3.12+，类型提示，ruff lint（line-length=100）
- Pydantic v2 schema（`model_config = ConfigDict(from_attributes=True)`）
- 服务层用全局单例模式，lifespan 中初始化
- pytest 异步模式：`asyncio_mode = "auto"`
- 前端 Vue3 组合式 API + TypeScript，Naive UI 组件自动导入（unplugin）
- Vite 代理 `/api` 到后端，前端无需处理 CORS

## Data Flow

搜索流程：用户输入查询 → FastAPI 接收 → DuckDB 通过 httpfs 扩展远程查询 OBS 上的 Parquet（ILIKE 匹配 title/author） → 返回匹配记录。前端按 `(title.lower(), author.lower())` 分组，同一本书的不同格式（epub/pdf/mobi/azw3）合并为 `formats` 数组。

ETL 流程：JSONL.zst → PostgreSQL（清洗、过滤、OpenCC 简繁转换） → Parquet（DuckDB postgres 扩展导出）。仅保留 epub/pdf/mobi/azw3 格式、中英文、有 MD5 的记录。
