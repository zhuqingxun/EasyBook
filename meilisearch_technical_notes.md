# Meilisearch 技术笔记

## 1. 最新稳定版本和 Docker 镜像

### 版本信息
- **最新稳定版本**: v1.35.0（发布于 2026 年 2 月 2 日）
- **Docker 镜像标签**:
  - `getmeili/meilisearch:v1.35.0`（指定版本）
  - `getmeili/meilisearch:latest`（最新版本）

### v1.35.0 主要特性
- **性能可观测性**: 搜索路由现在接受 `showPerformanceDetails` 参数，返回详细的时间追踪
- **多线程稳定化**: 多核机器上的分面和前缀多线程后处理现在默认启用
- **重大变更**: `POST /indexes/<index_uid>/fields` 路由现在返回分页字段而非纯数组

---

## 2. 中文分词支持

### 内置支持
Meilisearch **原生支持中文分词**，无需额外插件或配置。它使用基于脚本检测的分词器，对中文、日文、韩文等语言提供了优化支持。

### 分词原理
1. **语言检测**: 使用 `whatlang` 库自动检测文本的语言和脚本
2. **分词器选择**: 根据检测结果选择专门的分词器
3. **中文分词**: 使用 **Jieba** 分词器处理中文文本
4. **标准化**: 统一繁体中文和简体中文

### 配置说明
**无需手动配置**。Meilisearch 会自动：
- 检测文档中的中文内容
- 应用 Jieba 分词器
- 处理中文查询

### 注意事项
- Jieba 分词可能创建较长的词，可能减少相关文档的匹配数量
- 如需自定义分词行为，可通过 [charabia](https://github.com/meilisearch/charabia) 库贡献自定义分词器

---

## 3. Python SDK

### 安装

**官方 SDK 包名**: `meilisearch`
**最新版本**: v0.40.0（2026 年 1 月 15 日）
**Python 版本要求**: Python 3.9+

```bash
pip install meilisearch
```

### 基本用法示例

#### 初始化客户端
```python
import meilisearch

# 创建客户端连接
client = meilisearch.Client('http://127.0.0.1:7700', 'masterKey')

# 获取索引对象
index = client.index('movies')
```

#### 创建索引和添加文档
```python
# 添加文档（索引不存在时会自动创建）
documents = [
    {'id': 1, 'title': 'Carol', 'genres': ['Romance', 'Drama']},
    {'id': 2, 'title': 'Wonder Woman', 'genres': ['Action', 'Adventure']},
    {'id': 3, 'title': 'Life of Pi', 'genres': ['Adventure', 'Drama']},
]

# 批量添加文档
index.add_documents(documents)
```

#### 基本搜索
```python
# 简单搜索（支持拼写容错）
results = index.search('caorl')  # 即使拼错也能找到 'Carol'
print(results)
```

#### 高级搜索：过滤和排序

```python
# 1. 配置可过滤和可排序属性
index.update_filterable_attributes(['id', 'genres'])
index.update_sortable_attributes(['id', 'title'])

# 2. 使用过滤器搜索
results = index.search('wonder', {
    'filter': ['id > 1 AND genres = Action']
})

# 3. 排序搜索结果
results = index.search('drama', {
    'sort': ['id:desc']
})

# 4. 复合查询：过滤 + 排序 + 分页
results = index.search('movie', {
    'filter': ['genres = Drama'],
    'sort': ['id:asc'],
    'limit': 10,
    'offset': 0
})
```

#### 混合搜索（关键词 + 语义）
```python
results = index.search('action movie', {
    'hybrid': {
        'semanticRatio': 0.5,
        'embedder': 'default'
    }
})
```

---

## 4. 索引配置

### 配置方式对比

#### 方式一：Python SDK
```python
import meilisearch

client = meilisearch.Client('http://127.0.0.1:7700', 'masterKey')
index = client.index('books')

# 配置可搜索属性（影响排序优先级）
index.update_searchable_attributes(['title', 'author', 'description'])

# 配置可过滤属性
index.update_filterable_attributes(['genres', 'author', 'publishYear'])

# 配置可排序属性
index.update_sortable_attributes(['publishYear', 'rating', 'price'])
```

#### 方式二：REST API
```bash
# 配置可搜索属性
curl -X PUT 'http://localhost:7700/indexes/books/settings/searchable-attributes' \
  -H 'Authorization: Bearer masterKey' \
  -H 'Content-Type: application/json' \
  --data-binary '["title", "author", "description"]'

# 配置可过滤属性
curl -X PUT 'http://localhost:7700/indexes/books/settings/filterable-attributes' \
  -H 'Authorization: Bearer masterKey' \
  -H 'Content-Type: application/json' \
  --data-binary '["genres", "author", "publishYear"]'

# 配置可排序属性
curl -X PUT 'http://localhost:7700/indexes/books/settings/sortable-attributes' \
  -H 'Authorization: Bearer masterKey' \
  -H 'Content-Type: application/json' \
  --data-binary '["publishYear", "rating", "price"]'
```

### 属性说明

#### searchableAttributes（可搜索属性）
- **作用**: 指定哪些字段参与搜索，并决定字段的排序优先级
- **默认值**: `["*"]`（所有字段按出现顺序）
- **影响**: 排在前面的字段匹配结果排序更靠前
- **示例**: `["title", "author"]` 表示标题匹配优先于作者匹配

#### filterableAttributes（可过滤属性）
- **作用**: 允许在搜索时使用 `filter` 参数过滤结果
- **默认值**: `[]`（无可过滤字段）
- **影响**: 更新此配置会触发重新索引
- **示例**: 配置后可使用 `filter: ['genres = Sci-Fi']`

#### sortableAttributes（可排序属性）
- **作用**: 允许在搜索时使用 `sort` 参数排序结果
- **默认值**: `[]`（无可排序字段）
- **影响**: 更新此配置会触发重新索引
- **示例**: 配置后可使用 `sort: ['price:asc', 'rating:desc']`

### 最佳实践
1. **先配置再添加数据**: 在添加大量文档前配置好这些属性，避免重复索引降低内存消耗
2. **精简配置**: 只配置真正需要的字段，减少索引体积
3. **避免过度配置**: filterableAttributes 和 sortableAttributes 会增加内存占用

---

## 5. 模糊搜索和容错（Typo Tolerance）

### 默认行为
Meilisearch 自动启用拼写容错：
- **5-8 个字符**: 允许 1 个拼写错误
- **9+ 个字符**: 允许最多 2 个拼写错误

### 配置容错规则

#### Python SDK 方式
```python
# 获取当前配置
typo_settings = index.get_typo_tolerance()

# 更新容错配置
index.update_typo_tolerance({
    'enabled': True,
    'minWordSizeForTypos': {
        'oneTypo': 4,    # 4+ 字符允许 1 个错误
        'twoTypos': 10   # 10+ 字符允许 2 个错误
    },
    'disableOnWords': ['iphone', 'api'],  # 这些词不容错
    'disableOnAttributes': ['isbn', 'sku']  # 这些字段不容错
})
```

#### REST API 方式
```bash
curl -X PATCH 'http://localhost:7700/indexes/movies/settings/typo-tolerance' \
  -H 'Authorization: Bearer masterKey' \
  -H 'Content-Type: application/json' \
  --data-binary '{
    "enabled": true,
    "minWordSizeForTypos": {
      "oneTypo": 4,
      "twoTypos": 10
    },
    "disableOnWords": ["iphone", "api"],
    "disableOnAttributes": ["isbn"]
  }'
```

### 配置约束
- `oneTypo` 范围: 0 ≤ oneTypo ≤ twoTypos
- `twoTypos` 范围: oneTypo ≤ twoTypos ≤ 255
- **推荐值**: oneTypo 在 2-8 之间，twoTypos 在 4-14 之间

### 高级选项

#### 禁用数字容错
```python
index.update_typo_tolerance({
    'disableOnNumbers': True  # 数字查询必须精确匹配
})
```

#### 按属性禁用
```python
# 对 ISBN 等精确字段禁用容错
index.update_typo_tolerance({
    'disableOnAttributes': ['isbn', 'productCode', 'serialNumber']
})
```

---

## 6. 分页

### 两种分页方式

#### 方式一：offset + limit（推荐，性能更好）
适用于"上一页/下一页"按钮的简单分页

```python
# 第 1 页（每页 20 条）
results = index.search('query', {
    'offset': 0,
    'limit': 20
})

# 第 2 页
results = index.search('query', {
    'offset': 20,
    'limit': 20
})

# 第 3 页
results = index.search('query', {
    'offset': 40,
    'limit': 20
})
```

#### 方式二：page + hitsPerPage（用于页码跳转）
适用于需要显示总页数和跳转到任意页的场景

```python
# 第 1 页（每页 20 条）
results = index.search('query', {
    'page': 1,
    'hitsPerPage': 20
})

# 第 5 页
results = index.search('query', {
    'page': 5,
    'hitsPerPage': 20
})
```

### 重要区别

| 特性 | offset + limit | page + hitsPerPage |
|------|----------------|-------------------|
| **性能** | 更快 | 较慢（资源密集） |
| **使用场景** | 简单分页导航 | 需要总页数和页码跳转 |
| **优先级** | 低 | 高（会覆盖 offset/limit） |
| **总结果数** | 不返回总页数 | 返回 `totalPages` 和 `totalHits` |

### 注意事项
1. **参数冲突**: 如果同时提供两种参数，`page + hitsPerPage` 优先生效，`offset + limit` 被忽略
2. **性能影响**: `page + hitsPerPage` 尤其在 `maxTotalHits` 设置较高时会影响性能
3. **默认限制**: 默认最多返回 1000 条结果

### 完整示例
```python
# 使用 offset/limit 的分页实现
def paginate_results(query, page_num, page_size=20):
    offset = (page_num - 1) * page_size
    return index.search(query, {
        'offset': offset,
        'limit': page_size
    })

# 使用 page/hitsPerPage 获取总页数
def paginate_with_total(query, page_num, page_size=20):
    result = index.search(query, {
        'page': page_num,
        'hitsPerPage': page_size
    })
    return {
        'hits': result['hits'],
        'currentPage': result.get('page'),
        'totalPages': result.get('totalPages'),
        'totalHits': result.get('totalHits')
    }
```

---

## 7. 数据量限制

### 索引文档数量限制
- **单个索引最大文档数**: 4,294,967,296（2^32 - 1）
- 这是 32 位无符号整数的最大值

### 文档大小限制
- **默认 payload 大小**: 100 MB
- **Meilisearch Cloud 上传限制**: 20 MB（通过 Web 界面）
- **修改限制**: 可通过 `--http-payload-size-limit` 启动参数调整

```bash
# 启动时设置 payload 限制为 200MB
meilisearch --http-payload-size-limit=209715200
```

### 大批量上传注意事项
⚠️ **警告**: 索引超过 3.5GB 的单个 JSON 文件可能导致文件描述符耗尽，触发内部错误。

**推荐做法**:
1. 将大文件拆分为多个小批次
2. 每批次控制在 100MB 以内
3. 使用分批上传而非一次性上传

```python
# 分批上传示例
def batch_upload(documents, batch_size=1000):
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        index.add_documents(batch)
        print(f"已上传 {i + len(batch)}/{len(documents)} 条文档")
```

---

## 8. Docker Compose 配置示例

### 基础配置（开发环境）
```yaml
version: '3.8'

services:
  meilisearch:
    image: getmeili/meilisearch:v1.35.0
    container_name: meilisearch
    ports:
      - "7700:7700"
    environment:
      - MEILI_MASTER_KEY=your-secure-master-key-at-least-16-chars
      - MEILI_ENV=development
    volumes:
      - ./meili_data:/meili_data
    restart: unless-stopped
```

### 完整配置（生产环境）
```yaml
version: '3.8'

services:
  meilisearch:
    image: getmeili/meilisearch:v1.35.0
    container_name: meilisearch_production
    ports:
      - "7700:7700"
    environment:
      # 必需：主密钥（生产环境必须设置）
      - MEILI_MASTER_KEY=${MEILI_MASTER_KEY}

      # 环境设置
      - MEILI_ENV=production

      # 日志配置
      - MEILI_LOG_LEVEL=INFO

      # 数据库路径
      - MEILI_DB_PATH=/meili_data/data.ms

      # 禁用匿名数据收集
      - MEILI_NO_ANALYTICS=true

      # 性能优化
      - MEILI_MAX_INDEXING_MEMORY=2Gb
      - MEILI_MAX_INDEXING_THREADS=4

      # Payload 大小限制（可选）
      - MEILI_HTTP_PAYLOAD_SIZE_LIMIT=104857600  # 100MB

    volumes:
      # 持久化数据卷
      - meilisearch_data:/meili_data

    restart: always

    # 健康检查
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7700/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    # 资源限制
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

# 命名卷（推荐用于生产环境）
volumes:
  meilisearch_data:
    driver: local
```

### 配置说明

#### 环境变量详解

| 变量 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `MEILI_MASTER_KEY` | 主密钥，用于 API 认证 | 无 | 生产环境必需（至少 16 字符） |
| `MEILI_ENV` | 运行环境 | `development` | 否 |
| `MEILI_DB_PATH` | 数据库存储路径 | `/meili_data` | 否 |
| `MEILI_NO_ANALYTICS` | 禁用匿名数据收集 | `false` | 否 |
| `MEILI_LOG_LEVEL` | 日志级别 | `INFO` | 否 |
| `MEILI_HTTP_PAYLOAD_SIZE_LIMIT` | Payload 大小限制（字节） | 104857600 (100MB) | 否 |
| `MEILI_MAX_INDEXING_MEMORY` | 索引最大内存 | 系统内存的 2/3 | 否 |

#### 数据持久化方式

**方式一：绑定挂载（开发环境）**
```yaml
volumes:
  - ./meili_data:/meili_data
```
- 数据存储在宿主机的 `./meili_data` 目录
- 便于开发时直接访问数据文件

**方式二：命名卷（生产环境推荐）**
```yaml
volumes:
  - meilisearch_data:/meili_data

volumes:
  meilisearch_data:
    driver: local
```
- 由 Docker 管理存储位置
- 更好的性能和可移植性

### 使用示例

#### 启动服务
```bash
# 使用环境变量
export MEILI_MASTER_KEY="your-super-secret-key-min-16-chars"

# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f meilisearch
```

#### 使用 .env 文件（推荐）
创建 `.env` 文件：
```bash
MEILI_MASTER_KEY=your-super-secret-key-min-16-chars
```

在 `docker-compose.yml` 中引用：
```yaml
environment:
  - MEILI_MASTER_KEY=${MEILI_MASTER_KEY}
```

#### 验证服务
```bash
# 检查健康状态
curl http://localhost:7700/health

# 使用 master key 访问
curl -H "Authorization: Bearer your-master-key" \
  http://localhost:7700/indexes
```

---

## 参考资源

### 官方文档
- [Meilisearch 官方文档](https://www.meilisearch.com/docs)
- [Python SDK 文档](https://python-sdk.meilisearch.com/)
- [GitHub 仓库](https://github.com/meilisearch/meilisearch)

### API 参考
- [Settings API](https://www.meilisearch.com/docs/reference/api/settings)
- [Search API](https://www.meilisearch.com/docs/reference/api/search)
- [Documents API](https://www.meilisearch.com/docs/reference/api/documents)

### 相关文章
- [Language Support](https://www.meilisearch.com/docs/learn/resources/language)
- [Typo Tolerance](https://www.meilisearch.com/docs/learn/relevancy/typo_tolerance_settings)
- [Pagination Guide](https://www.meilisearch.com/docs/guides/front_end/pagination)
- [Docker Guide](https://www.meilisearch.com/docs/guides/docker)

---

**文档创建时间**: 2026-02-06
**Meilisearch 版本**: v1.35.0
**Python SDK 版本**: v0.40.0
