这是一个为您整理好的系统设计方案文档，专注于**“静态索引+去中心化交付”**的 MVP（最小可行性产品）模式。此方案移除了复杂的实时爬虫和客户端 GUI（PyQt），转而采用更轻量、稳健的 Web 架构。

您可以直接复制以下内容保存为 `ebook_system_design.md`。

---

```markdown
# 电子书聚合搜索平台设计方案 (MVP 版)

**版本:** 1.0
**核心策略:** 静态索引入库 + IPFS/磁力交付 + Web 聚合检索
**排除项:** 暂不涉及实时全网爬取、暂不开发桌面客户端 (PyQt)

---

## 1. 项目背景与目标
构建一个电子书聚合搜索应用，核心解决两个痛点：
1.  **资源汇聚:** 提供统一入口检索 epub, pdf, mobi 等格式书籍。
2.  **有效性保障:** 确保提供的下载链接真实可用，避免“死链”。

由于初期不进行实时爬取，本项目将采用**“已归档元数据 (Metadata Dumps)”**作为主要数据源，利用去中心化协议（IPFS/Torrent）解决资源存储和死链问题。

---

## 2. 系统架构设计

采用经典的 **BFF (Backend for Frontend)** 架构，前后端分离。

### 2.1 架构图示
```mermaid
graph TD
    User[用户 (Web/Mobile)] -->|搜索请求| API[后端 API (FastAPI/Go)]
    API -->|查询| SearchEngine[搜索引擎 (Meilisearch)]
    API -->|元数据详情| DB[(PostgreSQL)]
    
    User -->|点击下载| Gateway[IPFS 公共网关 / 磁力下载器]
    
    subgraph "数据处理管道 (离线/定时)"
        Dump[数据源: Anna's Archive / Z-Lib Dumps] -->|清洗 & 提取| ETL[ETL 脚本]
        ETL -->|写入| DB
        ETL -->|建立索引| SearchEngine
    end

```

### 2.2 核心模块说明

1. **数据层 (Data Layer):**
* 存储清洗后的书籍元数据（书名、作者、ISBN、格式、大小、IPFS CID、MD5）。


2. **搜索层 (Search Layer):**
* 提供高性能的全文检索、模糊匹配、拼写容错。


3. **应用层 (Application Layer):**
* 处理用户请求，聚合搜索结果，生成可用的下载链接（拼接网关地址）。


4. **交付层 (Delivery Layer):**
* 不直接存储文件，而是提供指向 IPFS 网络或 BT 网络的哈希链接。



---

## 3. 数据获取方案 (No-Crawl Strategy)

既然不做实时爬取，我们需要利用开源社区已整理好的**“种子数据库”**。

### 3.1 数据源推荐

* **Anna's Archive Torrents:**
* **内容:** 它是目前最全的元数据聚合，提供 `.jsonl` 或 SQL 格式的元数据下载（包含 Z-Library, LibGen, Sci-Hub 数据）。
* **获取方式:** 访问其官网的 "Datasets" 部分下载最新的种子文件。


* **Z-Library SQL Dumps:**
* **内容:** 历史归档的元数据，包含大量中文书籍信息。



### 3.2 数据处理 (ETL) 流程

1. **下载:** 下载几十 GB 的元数据压缩包。
2. **清洗 (Python Script):**
* 过滤非电子书格式（保留 epub, pdf, mobi, azw3）。
* 过滤无有效哈希（CID/MD5）的条目。
* *(可选)* 针对中文书名进行简繁体转换，统一索引。


3. **入库:** 将清洗后的数据存入 PostgreSQL（做持久化备份）并同步到 Meilisearch（做即时搜索）。

---

## 4. 关键技术选型

| 模块 | 推荐技术栈 | 选择理由 |
| --- | --- | --- |
| **后端框架** | **FastAPI (Python)** | 开发快，异步性能好，适合处理高并发的搜索请求。 |
| **搜索引擎** | **Meilisearch** | 比 Elasticsearch 轻量，对**中文分词**开箱即用，配置极简，非常适合中小型项目（<1亿条记录）。 |
| **数据库** | **PostgreSQL** | 关系型数据库标杆，能够稳定存储元数据。 |
| **前端框架** | **Next.js** 或 **Vue3** | 易于构建 SEO 友好且交互流畅的搜索界面。 |
| **下载协议** | **IPFS** | 解决“死链”的核心。只要网络中有一个节点存有文件，链接即有效。 |

---

## 5. “有效下载”的实现机制

这是本项目的核心难点。传统 HTTP 链接容易失效，我们采用 **Content-Addressed (基于内容寻址)** 的方式。

### 5.1 链接生成逻辑

数据库中存储的是文件的 **CID (Content ID)** 或 **MD5**。用户点击下载时，后端动态拼接公共网关地址：

* **原始 CID:** `bafykbz...`
* **生成下载链接 (轮询/随机):**
* `https://ipfs.io/ipfs/{CID}?filename={BookName}.epub`
* `https://cloudflare-ipfs.com/ipfs/{CID}?filename={BookName}.epub`
* `https://dweb.link/ipfs/{CID}?filename={BookName}.epub`



### 5.2 可用性检测 (Health Check)

为了确保用户点进去能下，可以在后端实现一个轻量的**预检接口**：

* **动作:** 当用户在详情页停留时，JS 触发后端检测。
* **逻辑:** 后端对几个主流 IPFS 网关发起 `HEAD` 请求检测该 CID 的响应速度。
* **反馈:** 在前端显示“高可用网关”或“推荐节点”。

---

## 6. 数据库设计 (简易版)

### 表结构：`books`

```sql
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,        -- 书名
    author VARCHAR(255),                -- 作者
    extension VARCHAR(10),              -- 格式 (epub/pdf)
    filesize BIGINT,                    -- 大小 (Bytes)
    language VARCHAR(10),               -- 语言 (zh/en)
    ipfs_cid VARCHAR(255),              -- IPFS 内容哈希 (核心)
    md5 VARCHAR(32),                    -- MD5 校验
    cover_url TEXT,                     -- 封面图链接
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 索引优化
CREATE INDEX idx_books_search ON books USING GIN (to_tsvector('simple', title));

```

---

## 7. 下一步实施计划 (Roadmap)

1. **环境准备:** 使用 Docker Compose 部署 Meilisearch 和 PostgreSQL。
2. **数据导入:** 下载一份小规模的 Dataset (例如 Anna's Archive 的前 100 万条数据) 编写 Python 脚本跑通入库流程。
3. **API 开发:** 写一个简单的 `/search` 接口对接 Meilisearch。
4. **前端验证:** 写一个简单的 HTML 页面测试搜索和 IPFS 链接的跳转下载。

```

您可以将此内容复制到您的笔记软件中。如果您准备开始开发，可以随时开启新会话，我可以为您提供具体的 **Docker Compose 配置文件** 或 **数据清洗脚本**。

```