---
description: "功能实施计划: download-architecture-migration"
status: completed
created_at: 2026-02-08T12:30:00
updated_at: 2026-02-08T13:30:00
archived_at: null
related_files:
  - rpiv/requirements/prd-download-architecture-migration.md
---

# 功能：下载架构迁移（IPFS -> Anna's Archive 跳转）

以下计划应该是完整的，但在开始实施之前，验证文档和代码库模式以及任务合理性非常重要。

特别注意现有工具、类型和模型的命名。从正确的文件导入等。

## 功能描述

将 EasyBook 的下载架构从不可行的 IPFS CID + 公共网关方案迁移为 Anna's Archive slow_download 外链跳转方案。用户点击格式按钮后，前端直接在新标签页打开 Anna's Archive 下载页面。同时清理所有 IPFS 相关的无效代码、数据库字段和依赖。

## 用户故事

作为电子书搜索用户
我想要点击格式按钮后直接跳转到下载页面
以便快速获取电子书文件

## 问题陈述

zlib3 数据集中不包含 ipfs_cid 字段，导致 IPFS 下载方案完全不可行。当前系统中大量 IPFS 相关代码（网关服务、健康检查调度器、数据库模型等）均为无效代码，增加了维护负担和启动时间。

## 解决方案陈述

1. 前端直接用 MD5 拼接 Anna's Archive URL 并 `window.open()` 跳转，无需后端参与
2. 完全移除 IPFS 相关代码（gateway_service、scheduler、gateway_health 模型/表、download API）
3. Anna's Archive base URL 通过 Vite 环境变量 `VITE_ANNAS_ARCHIVE_URL` 配置化

## 功能元数据

**功能类型**：重构（架构替换 + 代码清理）
**估计复杂度**：中
**主要受影响的系统**：后端 API、前端组件、数据库模型、ETL 脚本
**依赖项**：无新增依赖，移除 `apscheduler`

---

## 上下文参考

### 相关代码库文件 重要：在实施之前必须阅读这些文件！

**将被删除的文件**：
- `backend/app/services/gateway_service.py` (全文) - 原因：IPFS 网关服务，完全移除
- `backend/app/services/scheduler_service.py` (全文) - 原因：APScheduler 调度器，仅用于网关健康检查，完全移除
- `backend/app/models/gateway_health.py` (全文) - 原因：网关健康状态 ORM 模型，完全移除
- `backend/app/api/v1/download.py` (全文) - 原因：下载 API 端点，完全移除

**将被修改的文件（后端）**：
- `backend/app/main.py` (第 27-28, 77-93, 100-115 行) - 原因：移除 gateway_service/scheduler 导入和 lifespan 中的初始化/关闭逻辑
- `backend/app/config.py` (第 18-24, 46-48 行) - 原因：移除 IPFS_GATEWAYS、HEALTH_CHECK_* 配置和 ipfs_gateway_list 属性
- `backend/app/api/v1/router.py` (第 3, 7 行) - 原因：移除 download 路由导入和注册
- `backend/app/api/v1/search.py` (第 7, 33, 42-49 行) - 原因：移除 gateway_service 依赖，download_url 改为空字符串（前端不再使用）
- `backend/app/api/v1/health.py` (第 7, 40-48 行) - 原因：移除 GatewayHealth 导入和最后网关检查时间查询
- `backend/app/schemas/search.py` (第 28-31 行) - 原因：移除 DownloadResponse schema
- `backend/app/schemas/search.py` (第 33-38 行) - 原因：移除 HealthResponse.last_health_check 字段
- `backend/app/models/book.py` (第 20 行) - 原因：移除 ipfs_cid 字段
- `backend/app/core/logging_config.py` (第 35 行) - 原因：移除 apscheduler 日志级别设置
- `backend/etl/create_tables.py` (第 14 行) - 原因：移除 GatewayHealth 导入
- `backend/etl/import_annas.py` (第 119, 141, 146 行) - 原因：移除 ipfs_cid 相关字段
- `backend/etl/sync_meilisearch.py` (第 154, 171 行) - 原因：移除 ipfs_cid 字段查询和文档映射
- `backend/pyproject.toml` (第 19 行) - 原因：移除 apscheduler 依赖

**将被修改的文件（测试）**：
- `backend/tests/test_gateway.py` (第 1-108 行) - 原因：移除 TestGatewayService 类（保留 TestETLCleansing 第 110-225 行）
- `backend/tests/test_search.py` (第 23-25, 57-61 行) - 原因：移除 ipfs_cid 相关 download_url 构建逻辑
- `backend/tests/conftest.py` (第 15, 26, 37 行) - 原因：移除 ipfs_cid 字段

**将被修改的文件（前端）**：
- `frontend/src/components/BookItem.vue` (全文重构) - 原因：移除网关弹窗，改为 window.open() 跳转
- `frontend/src/api/modules/search.ts` (第 8-10 行) - 原因：移除 getDownloadUrl 函数
- `frontend/src/types/search.ts` (第 8-12 行) - 原因：移除 DownloadResponse 类型
- `frontend/Dockerfile` (第 6-7 行) - 原因：添加 VITE_ANNAS_ARCHIVE_URL ARG
- `frontend/.env` (第 1 行) - 原因：添加 VITE_ANNAS_ARCHIVE_URL 默认值
- `frontend/.env.production` - 原因：添加 VITE_ANNAS_ARCHIVE_URL

### 要创建的新文件

- `backend/etl/migrate_remove_ipfs.py` - 数据库迁移脚本：删除 ipfs_cid 列和 gateway_health 表

### 相关文档

- Anna's Archive slow_download URL 格式：`https://zh.annas-archive.li/slow_download/{md5}/0/0`

### 要遵循的模式

**Vite 环境变量注入模式**（参考现有 `VITE_API_BASE_URL`）：
- `frontend/.env`: `VITE_ANNAS_ARCHIVE_URL=https://zh.annas-archive.li`
- `frontend/Dockerfile`: `ARG VITE_ANNAS_ARCHIVE_URL` + `ENV VITE_ANNAS_ARCHIVE_URL=${VITE_ANNAS_ARCHIVE_URL}`
- 前端代码中使用: `import.meta.env.VITE_ANNAS_ARCHIVE_URL`

**搜索结果 download_url 构建模式**（`search.py` 第 42-49 行当前逻辑）：
- 当前用 ipfs_cid + gateway 构建 URL
- 修改后直接传空字符串（前端不再依赖后端的 download_url，自行拼接）

---

## 实施计划

### 阶段 1：后端代码清理

移除所有 IPFS 相关的后端代码、配置和依赖。这是最大的变更阶段，按依赖关系从叶子节点向根节点清理。

### 阶段 2：ETL 脚本清理 + 数据库迁移

修改 ETL 脚本移除 ipfs_cid 引用，创建数据库迁移脚本。

### 阶段 3：测试修复

修复因后端变更导致的测试代码。

### 阶段 4：前端重构

将下载交互从网关弹窗改为直接跳转，添加 Anna's Archive 环境变量。

---

## 逐步任务

重要：按顺序从上到下执行每个任务。每个任务都是原子的且可独立测试。

### 任务 1: REMOVE `backend/app/services/gateway_service.py`

- **IMPLEMENT**：删除整个文件
- **VALIDATE**：文件已不存在

### 任务 2: REMOVE `backend/app/services/scheduler_service.py`

- **IMPLEMENT**：删除整个文件
- **VALIDATE**：文件已不存在

### 任务 3: REMOVE `backend/app/models/gateway_health.py`

- **IMPLEMENT**：删除整个文件
- **VALIDATE**：文件已不存在

### 任务 4: REMOVE `backend/app/api/v1/download.py`

- **IMPLEMENT**：删除整个文件
- **VALIDATE**：文件已不存在

### 任务 5: UPDATE `backend/app/main.py`

- **IMPLEMENT**：
  - 移除 `from app.services.gateway_service import gateway_service`（第 27 行）
  - 移除 `from app.services.scheduler_service import scheduler, setup_scheduler`（第 28 行）
  - 移除 lifespan 中"5. 启动定时调度器"代码块（第 77-84 行）
  - 移除 lifespan 中"6. 异步执行首次网关健康检查"代码块（第 87-92 行）
  - 移除 `health_check_task` 相关变量声明
  - 移除关闭阶段中 `health_check_task` 取消逻辑（第 103-109 行）
  - 移除关闭阶段中 `scheduler.shutdown()` 逻辑（第 111-115 行）
  - 保留 `import asyncio` （其他地方可能用到，检查后如无用也移除）
- **PATTERN**：保持 lifespan 结构，只移除步骤 5 和 6，步骤编号不需要重新排列
- **GOTCHA**：移除 `health_check_task` 后，关闭阶段中引用它的代码也要一并移除，否则 NameError
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run python -c "from app.main import app; print('OK')"`

### 任务 6: UPDATE `backend/app/config.py`

- **IMPLEMENT**：
  - 移除 `IPFS_GATEWAYS` 配置项（第 18-21 行，含注释）
  - 移除 `HEALTH_CHECK_INTERVAL_HOURS` 配置项（第 23 行）
  - 移除 `HEALTH_CHECK_FAIL_THRESHOLD` 配置项（第 24 行）
  - 移除 `ipfs_gateway_list` 属性方法（第 46-48 行）
- **GOTCHA**：检查注释行是否关联正确，确保不误删其他配置项之间的空行
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run python -c "from app.config import settings; print(settings.MEILI_URL)"`

### 任务 7: UPDATE `backend/app/api/v1/router.py`

- **IMPLEMENT**：
  - 移除 `from app.api.v1 import download`（修改第 3 行导入，只保留 `health, search`）
  - 移除 `api_router.include_router(download.router, tags=["Download"])`（第 7 行）
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run python -c "from app.api.v1.router import api_router; print('OK')"`

### 任务 8: UPDATE `backend/app/api/v1/search.py`

- **IMPLEMENT**：
  - 移除 `from app.services.gateway_service import gateway_service`（第 7 行）
  - 移除 `best_gateway = await gateway_service.get_best_gateway()`（第 33 行）
  - 简化 download_url 构建逻辑（第 42-49 行）：移除 ipfs_cid 相关代码，download_url 直接设为空字符串 `""`
  - 修改后的合并循环中，每个 hit 的处理变为：
    ```python
    extension = hit.get("extension", "")
    filesize = hit.get("filesize")

    fmt = BookFormat(
        extension=extension,
        filesize=filesize if filesize else None,
        download_url="",
        md5=hit.get("id", ""),
    )
    ```
- **PATTERN**：保持 `search_books` 函数整体结构不变，只简化内部逻辑
- **GOTCHA**：`download_url` 字段在 `BookFormat` schema 中仍存在（前端不再使用但 schema 保持兼容），设为空字符串即可
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run python -c "from app.api.v1.search import router; print('OK')"`

### 任务 9: UPDATE `backend/app/api/v1/health.py`

- **IMPLEMENT**：
  - 移除 `from app.models.gateway_health import GatewayHealth`（第 7 行）
  - 移除"获取最近一次网关健康检查时间"代码块（第 40-48 行）
  - 移除 `last_health_check` 从 `HealthResponse` 返回值中（或让它始终为 None）
- **PATTERN**：保持 health_check 函数结构，只移除网关相关部分
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run python -c "from app.api.v1.health import router; print('OK')"`

### 任务 10: UPDATE `backend/app/schemas/search.py`

- **IMPLEMENT**：
  - 移除 `DownloadResponse` 类（第 28-31 行）
  - 移除 `HealthResponse.last_health_check` 字段（第 38 行）
- **GOTCHA**：确认 `HealthResponse` 移除 `last_health_check` 后，`health.py` 中的返回值也不再传该字段
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run python -c "from app.schemas.search import SearchResponse, HealthResponse; print('OK')"`

### 任务 11: UPDATE `backend/app/models/book.py`

- **IMPLEMENT**：
  - 移除 `ipfs_cid: Mapped[Optional[str]] = mapped_column(String(255))`（第 20 行）
  - 如果 `Optional` 不再被使用，移除 `from typing import Optional` 中的 `Optional`（检查其他字段是否用到）
- **GOTCHA**：`Optional` 在其他字段（author、filesize、language、year、publisher）的类型注解中也被使用，因此 `from typing import Optional` 必须保留
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run python -c "from app.models.book import Book; print([c.name for c in Book.__table__.columns])"`

### 任务 12: UPDATE `backend/app/core/logging_config.py`

- **IMPLEMENT**：移除 `logging.getLogger("apscheduler").setLevel(logging.INFO)`（第 35 行）
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run python -c "from app.core.logging_config import setup_logging; print('OK')"`

### 任务 13: UPDATE `backend/etl/create_tables.py`

- **IMPLEMENT**：移除 `from app.models.gateway_health import GatewayHealth  # noqa: F401`（第 14 行）
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run python -c "from etl.create_tables import create_tables; print('OK')"`

### 任务 14: UPDATE `backend/etl/import_annas.py`

- **IMPLEMENT**：
  - 移除 `parse_record` 返回字典中的 `"ipfs_cid"` 键（第 119 行）
  - 修改 `INSERT_SQL` 移除 `ipfs_cid` 列（第 141 行）：
    ```python
    INSERT_SQL = """
        INSERT INTO books (title, author, extension, filesize, language, md5, year, publisher)
        VALUES %s
        ON CONFLICT (md5) DO NOTHING
    """
    ```
  - 修改 `COLUMNS` 元组移除 `"ipfs_cid"`（第 146-147 行）：
    ```python
    COLUMNS = ("title", "author", "extension", "filesize", "language", "md5", "year", "publisher")
    ```
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run python -c "from etl.import_annas import parse_record; print('OK')"`

### 任务 15: UPDATE `backend/etl/sync_meilisearch.py`

- **IMPLEMENT**：
  - 修改 SELECT 语句移除 `ipfs_cid`（第 153-155 行）：
    ```python
    "SELECT id, title, author, extension, filesize, language, "
    "md5, year, publisher FROM books "
    ```
  - 移除文档映射中的 `"ipfs_cid"` 字段（第 171 行）
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run python -c "from etl.sync_meilisearch import sync; print('OK')"`

### 任务 16: UPDATE `backend/pyproject.toml`

- **IMPLEMENT**：移除 `"apscheduler>=3.10.0,<4.0.0",` 依赖（第 19 行）
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv sync`

### 任务 17: UPDATE `backend/tests/test_gateway.py`

- **IMPLEMENT**：
  - 移除整个 `TestGatewayService` 类（第 1-108 行，包括文件头部的导入）
  - 保留 `TestETLCleansing` 类（第 110-225 行）
  - 修改文件头部：移除不再需要的导入（`unittest.mock.AsyncMock/MagicMock/patch`、`httpx`、`GatewayService`）
  - 保留 `pytest` 和 `opencc` 相关导入
  - 更新文件头部 docstring 为 `"""ETL 数据清洗逻辑测试"""`
  - 修改 `test_parse_record_valid` 中的测试数据：移除 `"ipfs_cid": "QmTest"` 字段（第 179 行）
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run pytest tests/test_gateway.py -v`

### 任务 18: UPDATE `backend/tests/test_search.py`

- **IMPLEMENT**：
  - 修改 `test_merge_same_book_formats`（第 13-54 行）：
    - 移除 `ipfs_cid = hit.get("ipfs_cid") or ""`（第 23 行）
    - 修改 `download_url` 逻辑：直接设为空字符串 `download_url = ""`（替换第 24-26 行）
  - 修改 `test_empty_cid_produces_empty_download_url`（第 56-61 行）：
    - 重命名为 `test_download_url_is_empty_string`
    - 简化为验证 BookFormat 的 download_url 为空字符串
    - 移除 ipfs_cid 相关逻辑
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run pytest tests/test_search.py -v`

### 任务 19: UPDATE `backend/tests/conftest.py`

- **IMPLEMENT**：
  - 移除三条测试数据中的 `"ipfs_cid"` 字段（第 15, 26, 37 行）
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run pytest tests/conftest.py --collect-only`

### 任务 20: CREATE `backend/etl/migrate_remove_ipfs.py`

- **IMPLEMENT**：创建数据库迁移脚本
  ```python
  """数据库迁移：移除 IPFS 相关字段和表

  用法：
      uv run python -m etl.migrate_remove_ipfs
      uv run python -m etl.migrate_remove_ipfs --dry-run
  """

  import argparse
  import logging

  from sqlalchemy import create_engine, text

  from app.config import settings

  logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  )
  logger = logging.getLogger(__name__)

  MIGRATIONS = [
      ("删除 books.ipfs_cid 列", "ALTER TABLE books DROP COLUMN IF EXISTS ipfs_cid"),
      ("删除 gateway_health 表", "DROP TABLE IF EXISTS gateway_health"),
  ]


  def migrate(dry_run: bool = False) -> None:
      engine = create_engine(settings.sync_database_url)

      with engine.begin() as conn:
          for desc, sql in MIGRATIONS:
              logger.info("执行迁移: %s", desc)
              if dry_run:
                  logger.info("  [DRY RUN] SQL: %s", sql)
              else:
                  conn.execute(text(sql))
                  logger.info("  完成")

      engine.dispose()
      logger.info("迁移%s完成", "预览" if dry_run else "")


  def main() -> None:
      parser = argparse.ArgumentParser(description="移除 IPFS 相关数据库字段和表")
      parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行")
      args = parser.parse_args()
      migrate(dry_run=args.dry_run)


  if __name__ == "__main__":
      main()
  ```
- **PATTERN**：参考 `etl/create_tables.py` 的脚本模式，使用同步引擎
- **GOTCHA**：使用 `IF EXISTS` 确保幂等性，重复执行不会报错
- **VALIDATE**：`cd D:/CODE/EasyBook/backend && uv run python -m etl.migrate_remove_ipfs --dry-run`

### 任务 21: UPDATE `frontend/src/components/BookItem.vue`

- **IMPLEMENT**：大幅简化组件
  - **模板 `<template>`**：
    - 保留 `n-card`、`book-info`、`book-formats` 结构
    - 移除整个 `n-modal` 网关选择弹窗（第 24-66 行）
    - 下载按钮移除 `:loading` 和 `loadingMd5` 相关绑定
    - 下载按钮的 `@click` 改为直接调用 `handleDownload(fmt)`
  - **脚本 `<script setup>`**：
    - 移除 `useMessage` 导入
    - 移除 `getDownloadUrl` 导入
    - 移除 `GatewayResult` 接口
    - 移除所有 ref：`loadingMd5`、`showModal`、`modalTitle`、`gatewayResults`、`currentExtension`、`downloadingUrl`
    - 移除函数：`extractGatewayName`、`checkGateway`、`openDownload`
    - 简化 `handleDownload(fmt)` 为：
      ```typescript
      function handleDownload(fmt: BookFormat) {
        if (!fmt.md5) return
        const baseUrl = import.meta.env.VITE_ANNAS_ARCHIVE_URL || 'https://zh.annas-archive.li'
        const url = `${baseUrl}/slow_download/${fmt.md5}/0/0`
        window.open(url, '_blank', 'noopener,noreferrer')
      }
      ```
    - 保留 `formatColor` 和 `formatFileSize` 函数
  - **样式 `<style scoped>`**：
    - 移除 `.gateway-list`、`.gateway-row`、`.gateway-available`、`.gateway-icon`、`.gateway-name`、`.gateway-latency` 样式
    - 保留 `.book-item`、`.book-info`、`.book-title`、`.book-author`、`.book-formats`、`.filesize` 样式
- **GOTCHA**：
  - `import.meta.env.VITE_ANNAS_ARCHIVE_URL` 在 Vite 中自动注入，无需额外配置
  - `window.open` 的第三个参数 `'noopener,noreferrer'` 确保安全性
  - 下载按钮不再需要 `:disabled="!fmt.download_url"` 判断，因为只要有 md5 就能跳转
- **VALIDATE**：`cd D:/CODE/EasyBook/frontend && pnpm build`

### 任务 22: UPDATE `frontend/src/api/modules/search.ts`

- **IMPLEMENT**：
  - 移除 `DownloadResponse` 类型导入（第 2 行中的部分）
  - 移除 `getDownloadUrl` 函数（第 8-10 行）
- **VALIDATE**：`cd D:/CODE/EasyBook/frontend && pnpm build`

### 任务 23: UPDATE `frontend/src/types/search.ts`

- **IMPLEMENT**：
  - 移除 `DownloadResponse` 接口（第 8-12 行）
- **GOTCHA**：`BookFormat.download_url` 字段保留（后端仍返回，只是始终为空字符串），保持前后端接口兼容
- **VALIDATE**：`cd D:/CODE/EasyBook/frontend && pnpm build`

### 任务 24: UPDATE `frontend/.env`

- **IMPLEMENT**：
  - 添加 `VITE_ANNAS_ARCHIVE_URL=https://zh.annas-archive.li`
- **VALIDATE**：文件内容正确

### 任务 25: UPDATE `frontend/.env.production`

- **IMPLEMENT**：
  - 添加注释和变量：
    ```
    # Anna's Archive base URL（Railway 部署时通过构建参数 ARG 注入）
    VITE_ANNAS_ARCHIVE_URL=https://zh.annas-archive.li
    ```
- **VALIDATE**：文件内容正确

### 任务 26: UPDATE `frontend/Dockerfile`

- **IMPLEMENT**：
  - 在现有 `ARG VITE_API_BASE_URL` 后添加：
    ```dockerfile
    ARG VITE_ANNAS_ARCHIVE_URL
    ENV VITE_ANNAS_ARCHIVE_URL=${VITE_ANNAS_ARCHIVE_URL}
    ```
- **PATTERN**：与 `VITE_API_BASE_URL` 完全相同的 ARG + ENV 模式
- **VALIDATE**：`cd D:/CODE/EasyBook/frontend && pnpm build`

### 任务 27: 全量验证

- **IMPLEMENT**：运行完整测试套件和 lint 检查
- **VALIDATE**：
  ```bash
  cd D:/CODE/EasyBook/backend && uv run ruff check app/ etl/
  cd D:/CODE/EasyBook/backend && uv run pytest tests/ -v
  cd D:/CODE/EasyBook/frontend && pnpm build
  ```

---

## 测试策略

### 单元测试

**保留并修复的测试**：
- `test_search.py::TestFormatMerge` — 修改为不依赖 ipfs_cid 的合并逻辑测试
- `test_search.py::TestSearchService` — 不受影响，无需修改
- `test_gateway.py::TestETLCleansing` — 移除 ipfs_cid 测试数据字段，其余不变

**移除的测试**：
- `test_gateway.py::TestGatewayService` — 被测代码已删除

### 边缘情况

- 搜索结果中 download_url 始终为空字符串，前端不依赖此字段
- 前端 `VITE_ANNAS_ARCHIVE_URL` 未配置时使用硬编码默认值
- MD5 为空时不触发跳转

---

## 验证命令

### 级别 1：语法和样式

```bash
cd D:/CODE/EasyBook/backend && uv run ruff check app/ etl/
```

### 级别 2：单元测试

```bash
cd D:/CODE/EasyBook/backend && uv run pytest tests/ -v
```

### 级别 3：前端构建

```bash
cd D:/CODE/EasyBook/frontend && pnpm build
```

### 级别 4：手动验证

1. 启动后端：`cd D:/CODE/EasyBook/backend && uv run uvicorn app.main:app --reload --port 8000`
2. 确认 `/api/health` 返回正常（不含 `last_health_check`）
3. 确认 `/api/search?q=test` 返回结果（`download_url` 为空字符串）
4. 确认 `/api/download/xxx` 返回 404（端点已移除）
5. 启动前端：`cd D:/CODE/EasyBook/frontend && pnpm dev`
6. 搜索并点击格式按钮，确认新标签页跳转到 Anna's Archive

---

## 验收标准

- [ ] 所有 IPFS 相关后端代码已移除（gateway_service、scheduler_service、gateway_health、download API）
- [ ] `config.py` 中 IPFS 相关配置项已移除
- [ ] `Book` 模型中 `ipfs_cid` 字段已移除
- [ ] `apscheduler` 依赖已从 `pyproject.toml` 移除
- [ ] 数据库迁移脚本可正常执行（dry-run 模式验证）
- [ ] ETL 脚本（import_annas、sync_meilisearch）不再引用 ipfs_cid
- [ ] 搜索 API 不再依赖 gateway_service
- [ ] 健康检查 API 不再查询 gateway_health 表
- [ ] 前端下载按钮点击后跳转到正确的 Anna's Archive URL
- [ ] `VITE_ANNAS_ARCHIVE_URL` 环境变量已配置
- [ ] 前端 Dockerfile 支持 `VITE_ANNAS_ARCHIVE_URL` ARG 注入
- [ ] 所有后端测试通过（`uv run pytest tests/ -v`）
- [ ] 后端 lint 检查通过（`uv run ruff check app/ etl/`）
- [ ] 前端构建成功（`pnpm build`）

---

## 完成检查清单

- [ ] 所有 27 个任务按顺序完成
- [ ] 每个任务验证通过
- [ ] 全量后端测试通过
- [ ] 全量 lint 检查通过
- [ ] 前端构建成功
- [ ] 手动验证搜索和下载跳转功能正常

---

## 备注

**设计决策**：
1. `BookFormat.download_url` 字段保留在 schema 中但始终为空字符串，因为前端已不依赖后端提供的下载 URL，而是自行构建 Anna's Archive URL。这样避免了前后端接口的 breaking change。
2. 数据库迁移使用独立脚本而非 Alembic，因为项目当前不使用 Alembic（使用 `create_tables.py` 直接建表）。
3. `apscheduler` 和 `httpx` 依赖处理不同：`apscheduler` 仅用于已删除的 scheduler_service，可以安全移除；`httpx` 虽然只在已删除的 gateway_service 中直接使用，但它是 FastAPI 推荐的 HTTP 客户端，保留在依赖中不会有问题。

**风险**：
- 生产数据库需要执行迁移脚本删除 `ipfs_cid` 列和 `gateway_health` 表，建议先备份。
- Railway 前端服务需要手动添加 `VITE_ANNAS_ARCHIVE_URL` 环境变量。
