---
description: "产品需求文档: 下载架构迁移（IPFS → Anna's Archive 跳转）"
status: completed
created_at: 2026-02-08T12:00:00
updated_at: 2026-02-08T12:45:00
archived_at: null
---

# 下载架构迁移：IPFS → Anna's Archive 跳转

## 1. 执行摘要

EasyBook 电子书聚合搜索平台原有设计采用 IPFS CID + 公共网关的方式提供电子书下载。经调研确认，zlib3 数据集中**不包含 ipfs_cid 字段**，导致 IPFS 下载方案完全不可行。当前系统中与 IPFS 相关的代码（网关服务、健康检查调度器、数据库模型等）均为无效代码。

本次架构调整将下载方案替换为 **Anna's Archive slow_download 外链跳转**。用户点击格式按钮后，前端直接在新标签页打开 Anna's Archive 下载页面，用户在该页面点击"立即下载"即可获取文件。

核心目标：**移除不可行的 IPFS 方案，替换为简单可靠的 Anna's Archive 跳转方案，同时清理所有无效代码和数据库字段。**

## 2. 使命

**使命声明**：让用户从搜索到下载的路径尽可能短、尽可能可靠。

**核心原则**：

1. **简单直接** — 点击即跳转，无需中间步骤（弹窗、网关选择）
2. **可维护** — 移除所有不可行的 IPFS 代码，减少技术债务
3. **可配置** — Anna's Archive 域名通过环境变量配置，域名变更时无需改代码
4. **最小变更** — 只改必要的部分，不引入新的复杂度

## 3. 目标用户

- **主要用户**：电子书搜索用户，通过 EasyBook 搜索并下载电子书
- **技术水平**：普通互联网用户，能理解"点击跳转到外部网站下载"的交互模式
- **核心需求**：搜索到书后，能快速、可靠地获取下载链接
- **痛点（当前）**：IPFS 方案不可行，下载功能实际上无法使用

## 4. MVP 范围

### 范围内

**核心功能变更**：
- ✅ 前端下载按钮改为 `window.open()` 直接跳转到 Anna's Archive
- ✅ Anna's Archive base URL 通过 `VITE_ANNAS_ARCHIVE_URL` 环境变量配置
- ✅ URL 格式：`${VITE_ANNAS_ARCHIVE_URL}/slow_download/${md5}/0/0`

**代码清理**：
- ✅ 移除 `backend/app/services/gateway_service.py`（整个文件）
- ✅ 移除 `backend/app/services/scheduler_service.py`（整个文件）
- ✅ 移除 `backend/app/models/gateway_health.py`（整个文件）
- ✅ 移除 `backend/app/api/v1/download.py`（整个文件）
- ✅ 移除 `backend/tests/test_gateway.py` 中的 `TestGatewayService` 测试类
- ✅ 清理 `backend/app/main.py` 中的 scheduler/gateway 初始化逻辑
- ✅ 清理 `backend/app/config.py` 中的 IPFS 相关配置项
- ✅ 移除前端 `getDownloadUrl` API 调用和 `DownloadResponse` 类型
- ✅ 移除前端 `BookItem.vue` 中的网关选择弹窗

**数据库变更**：
- ✅ 移除 `Book` 模型的 `ipfs_cid` 字段
- ✅ 创建数据库 migration 删除 `ipfs_cid` 列
- ✅ 移除 `gateway_health` 表（migration）

**部署配置**：
- ✅ Railway 前端服务添加 `VITE_ANNAS_ARCHIVE_URL` 环境变量
- ✅ 前端 Dockerfile 添加 `VITE_ANNAS_ARCHIVE_URL` ARG

### 范围外

- ❌ 下载次数统计
- ❌ 下载链接有效性检测
- ❌ 多下载源选择
- ❌ 本地缓存/代理下载

## 5. 用户故事

### US-1：一键跳转下载
**作为**电子书搜索用户，**我想要**点击格式按钮后直接跳转到下载页面，**以便**快速获取电子书文件。

**示例**：用户搜索"Python 编程"，在结果列表中看到一本书有 EPUB 和 PDF 两种格式。点击"EPUB (2.3 MB)"按钮，浏览器新标签页打开 `https://zh.annas-archive.li/slow_download/abc123.../0/0`，用户在该页面点击"立即下载"完成下载。

### US-2：域名可配置
**作为**系统管理员，**我想要**通过环境变量配置 Anna's Archive 的域名，**以便**在域名变更时无需修改代码。

**示例**：Anna's Archive 域名从 `zh.annas-archive.li` 变更为新域名，管理员修改 Railway 环境变量 `VITE_ANNAS_ARCHIVE_URL`，触发前端重新构建即可生效。

### US-3：多格式独立跳转
**作为**电子书搜索用户，**我想要**每种格式都有独立的下载跳转按钮，**以便**选择我需要的格式下载。

**示例**：一本书同时有 EPUB、PDF、MOBI 三种格式，每种格式对应不同的 MD5，点击不同按钮跳转到各自的下载页面。

## 6. 核心架构与模式

### 变更前架构（IPFS 方案）

```
用户点击下载按钮
  → 前端调用 GET /api/v1/download/{md5}
    → 后端查 Book.ipfs_cid
    → 后端查 gateway_health 表获取最优网关
    → 返回 download_url + alternatives
  → 前端弹出网关选择弹窗
  → 用户选择网关 → 前端 fetch 下载 → blob 保存
```

### 变更后架构（Anna's Archive 跳转）

```
用户点击下载按钮
  → 前端拼接 URL: ${VITE_ANNAS_ARCHIVE_URL}/slow_download/${md5}/0/0
  → window.open() 新标签页打开
  → 用户在 Anna's Archive 页面点击"立即下载"
```

**关键变化**：
- 移除后端在下载流程中的参与
- 移除网关健康检查定时任务
- 前端从"调 API + 弹窗选择"简化为"直接跳转"

### 移除的组件

| 组件 | 文件 | 说明 |
|------|------|------|
| GatewayService | `services/gateway_service.py` | IPFS 网关管理，完全移除 |
| SchedulerService | `services/scheduler_service.py` | APScheduler 调度器，完全移除 |
| GatewayHealth 模型 | `models/gateway_health.py` | 网关健康状态表，完全移除 |
| Download API | `api/v1/download.py` | 下载链接 API，完全移除 |
| 网关选择弹窗 | `BookItem.vue` | 前端网关 UI，替换为直接跳转 |

## 7. 工具/功能

### 7.1 前端：下载按钮重构

**当前行为**：
- 点击格式按钮 → 调用 `getDownloadUrl(md5)` → 弹出网关选择弹窗 → 逐个检测网关 → 用户选择下载

**目标行为**：
- 点击格式按钮 → `window.open(url, '_blank')` 直接跳转

**URL 构建规则**：
```
${VITE_ANNAS_ARCHIVE_URL}/slow_download/${md5}/0/0
```

**环境变量**：
- 名称：`VITE_ANNAS_ARCHIVE_URL`
- 默认值：`https://zh.annas-archive.li`
- 注入方式：Vite 构建时注入（与 `VITE_API_BASE_URL` 一致）

### 7.2 前端：组件简化

`BookItem.vue` 需要：
- 移除 `GatewayResult` 接口和相关 ref（`gatewayResults`、`showModal`、`modalTitle`、`downloadingUrl`）
- 移除 `checkGateway()`、`openDownload()`、`extractGatewayName()` 函数
- 移除 `n-modal` 网关选择弹窗模板
- 移除 `getDownloadUrl` API 导入
- 简化 `handleDownload()` 为直接 `window.open()`
- 移除 `loadingMd5` ref（不再需要加载状态）

### 7.3 后端：代码清理

**完全删除的文件**：
- `backend/app/services/gateway_service.py`
- `backend/app/services/scheduler_service.py`
- `backend/app/models/gateway_health.py`
- `backend/app/api/v1/download.py`

**需要修改的文件**：
- `backend/app/main.py` — 移除 gateway_service/scheduler 导入和 lifespan 中的初始化/关闭逻辑
- `backend/app/config.py` — 移除 `IPFS_GATEWAYS`、`HEALTH_CHECK_INTERVAL_HOURS`、`HEALTH_CHECK_FAIL_THRESHOLD`、`ipfs_gateway_list` 属性
- `backend/app/models/book.py` — 移除 `ipfs_cid` 字段
- `backend/app/api/v1/router.py` — 移除 download 路由注册
- `backend/app/schemas/search.py` — 移除 `DownloadResponse` schema
- `backend/tests/test_gateway.py` — 移除 `TestGatewayService` 测试类（保留 `TestETLCleansing`）

### 7.4 数据库 Migration

需要两个 migration 操作：
1. 删除 `books` 表的 `ipfs_cid` 列
2. 删除 `gateway_health` 表

## 8. 技术栈

**无新增依赖**。本次变更为纯移除性质。

**移除的依赖**：
- `apscheduler`（如果仅用于网关健康检查，可从 `pyproject.toml` 移除）

**保留不变**：
- 后端：FastAPI、SQLAlchemy 2.0、Meilisearch Python SDK、PostgreSQL
- 前端：Vue3、Naive UI、Vite、Axios
- 部署：Railway

## 9. 安全与配置

### 配置变更

**新增环境变量**：

| 变量名 | 位置 | 默认值 | 说明 |
|--------|------|--------|------|
| `VITE_ANNAS_ARCHIVE_URL` | 前端 | `https://zh.annas-archive.li` | Anna's Archive base URL |

**移除环境变量/配置项**：

| 变量名 | 位置 | 说明 |
|--------|------|------|
| `IPFS_GATEWAYS` | 后端 | IPFS 网关列表 |
| `HEALTH_CHECK_INTERVAL_HOURS` | 后端 | 健康检查间隔 |
| `HEALTH_CHECK_FAIL_THRESHOLD` | 后端 | 健康检查失败阈值 |

**Railway 部署配置更新**：
- 前端服务：添加 `VITE_ANNAS_ARCHIVE_URL=https://zh.annas-archive.li`
- 前端 Dockerfile：添加 `ARG VITE_ANNAS_ARCHIVE_URL`

### 安全考虑

- 跳转 URL 由前端构建，MD5 来自搜索结果（已经过 Meilisearch 索引），不存在注入风险
- `window.open()` 跳转到外部站点，建议添加 `rel="noopener noreferrer"` 属性（通过 `window.open` 的第三个参数或使用 `<a>` 标签）

## 10. API 规范

### 移除的 API

**DELETE** `GET /api/v1/download/{md5}`

此端点将被完全移除，前端不再调用后端获取下载链接。

### 保留不变的 API

- `GET /api/v1/search?q=&page=&page_size=` — 搜索接口，不变
- `GET /api/v1/health` — 健康检查接口，移除 `last_health_check` 字段（该字段引用网关健康检查）

## 11. 成功标准

### MVP 成功定义

用户能够通过点击格式按钮直接跳转到 Anna's Archive 下载页面，完成电子书下载。

### 功能要求

- ✅ 前端格式按钮点击后在新标签页打开正确的 Anna's Archive URL
- ✅ URL 格式为 `${base_url}/slow_download/${md5}/0/0`
- ✅ Anna's Archive base URL 通过环境变量 `VITE_ANNAS_ARCHIVE_URL` 配置
- ✅ 所有 IPFS 相关代码已完全移除
- ✅ `ipfs_cid` 数据库字段已移除
- ✅ `gateway_health` 数据库表已移除
- ✅ APScheduler 相关代码已移除
- ✅ 现有测试（ETL 相关）仍然通过
- ✅ Railway 部署配置已更新

### 质量指标

- 代码行数净减少（移除 > 新增）
- 无新增依赖
- 后端启动时间缩短（移除了 scheduler 和网关健康检查）

## 12. 实施阶段

### 阶段 1：后端清理

**目标**：移除所有 IPFS 相关的后端代码和配置

**交付物**：
- ✅ 删除 `gateway_service.py`、`scheduler_service.py`、`gateway_health.py`
- ✅ 删除 `download.py` API 端点
- ✅ 清理 `main.py` 中 scheduler/gateway 逻辑
- ✅ 清理 `config.py` 中 IPFS 配置项
- ✅ 移除 `router.py` 中 download 路由
- ✅ 移除 `DownloadResponse` schema
- ✅ 移除 `Book.ipfs_cid` 字段
- ✅ 清理 `test_gateway.py` 中 IPFS 测试

**验证**：后端能正常启动，搜索功能不受影响，现有 ETL 测试通过

### 阶段 2：数据库 Migration

**目标**：清理数据库中的无效字段和表

**交付物**：
- ✅ 创建 migration：删除 `books.ipfs_cid` 列
- ✅ 创建 migration：删除 `gateway_health` 表

**验证**：migration 可正常执行，不影响现有数据

### 阶段 3：前端重构

**目标**：将下载交互从网关弹窗改为直接跳转

**交付物**：
- ✅ `BookItem.vue` 移除网关弹窗，改为 `window.open()` 跳转
- ✅ 添加 `VITE_ANNAS_ARCHIVE_URL` 环境变量
- ✅ 移除 `getDownloadUrl` API 调用
- ✅ 移除 `DownloadResponse` 类型定义
- ✅ 前端 Dockerfile 添加 `ARG VITE_ANNAS_ARCHIVE_URL`

**验证**：前端构建成功，点击下载按钮能正确跳转

### 阶段 4：部署与验证

**目标**：更新 Railway 部署配置，生产环境验证

**交付物**：
- ✅ Railway 前端服务配置 `VITE_ANNAS_ARCHIVE_URL`
- ✅ 推送代码触发自动部署
- ✅ 生产环境功能验证

**验证**：生产环境搜索 + 下载跳转正常工作

## 13. 未来考虑

- **下载统计**：可在前端通过事件追踪（如 Google Analytics）记录下载点击
- **多下载源**：未来可添加其他下载源（如 Library Genesis 直链），提供多源选择
- **链接有效性**：可定期检测 Anna's Archive 域名可用性，前端显示提示
- **镜像站支持**：Anna's Archive 有多个镜像域名，可支持自动切换

## 14. 风险与缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Anna's Archive 域名变更 | 下载链接失效 | 域名通过环境变量配置，变更后修改环境变量重新构建即可 |
| Anna's Archive 服务不可用 | 用户无法下载 | 外部依赖，无法完全控制；可在前端添加提示文案 |
| slow_download URL 格式变更 | 跳转后 404 | URL 路径模板可考虑后续也配置化；当前格式稳定 |
| 数据库 migration 失败 | 部署阻塞 | migration 前备份数据库；删除列和表是低风险操作 |

## 15. 附录

### 相关文档
- 原始 PRD：`rpiv/archive/prd-ebook-search-platform.md`
- IPFS 网关调研：`rpiv/ipfs_gateway_research.md`

### Anna's Archive URL 格式
```
https://zh.annas-archive.li/slow_download/{md5}/0/0
```
- `{md5}` 为书籍的 32 位 MD5 哈希值（小写）
- `/0/0` 为固定后缀参数

### 受影响文件清单

**删除**：
- `backend/app/services/gateway_service.py`
- `backend/app/services/scheduler_service.py`
- `backend/app/models/gateway_health.py`
- `backend/app/api/v1/download.py`

**修改**：
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/models/book.py`
- `backend/app/api/v1/router.py`
- `backend/app/schemas/search.py`
- `backend/tests/test_gateway.py`
- `frontend/src/components/BookItem.vue`
- `frontend/src/api/modules/search.ts`
- `frontend/src/types/search.ts`
- `frontend/Dockerfile`
- `frontend/.env`（或 `.env.development`）
