# Anna's Archive 数据集技术笔记

## 1. 数据集获取方式

### 主要访问入口
- **数据集页面**: [https://annas-archive.li/datasets](https://annas-archive.li/datasets)
- **Torrents 下载**: [https://annas-archive.li/torrents](https://annas-archive.li/torrents)
- **预计算数据库**: [https://annas-archive.se/torrents#aa_derived_mirror_metadata](https://annas-archive.se/torrents#aa_derived_mirror_metadata)

### 数据格式

**主要格式类型**:
1. **JSONL + Zstandard 压缩** (`.jsonl.zst`)
   - 元数据文件标准格式
   - 文件命名规范: `annas_archive_meta__[AACID范围].jsonl.zst`
   - 采用逐行 JSON (JSON Lines) 格式,便于流式处理

2. **AAC 格式** (Anna's Archive Containers)
   - 包含元数据和可选的二进制数据
   - 所有数据不可变
   - 二进制数据文件夹命名: `annas_archive_data__[AACID范围]`

3. **数据库导出**
   - **MariaDB** 数据库 dump
     - 只读数据使用 MyISAM 存储引擎
     - 读写数据(用户账户、日志、评论)使用标准引擎
   - **ElasticSearch** 索引
     - 用于期刊论文、数字借阅、元数据搜索

### 数据获取方式
- **Torrent 批量下载**: 完整数据集通过 BitTorrent 协议分发
- **数据库预生成文件**: 跳过本地计算步骤,直接下载预计算的数据库
- **JSON 预览**: 在运行本地脚本前可先查看 JSON 样本文件

---

## 2. 数据结构

### AACID 唯一标识符结构
格式: `aacid__{collection}__{ISO 8601时间戳}__{集合特定ID}__{shortuuid}`

**组成部分**:
- **集合名称**: 仅 ASCII 字母、数字、下划线(不允许双下划线)
- **ISO 8601 时间戳**: UTC 格式如 `20220723T194746Z`,单调递增
- **集合特定 ID**: 可选,若 AACID 超过 150 字符可截断
- **shortuuid**: 压缩 UUID,使用 base57 ASCII 编码

**示例**:
```
aacid__zlib3_records__20230808T014342Z__22433983__URsJNGy5CjokTsNT6hUmmj
```

### 元数据 JSON 顶层字段 (必需)
```json
{
  "aacid": "唯一标识符",
  "metadata": {
    // 集合特定的任意元数据
  },
  "data_folder": "可选: 对应的二进制数据位置引用"
}
```

### 典型书籍元数据字段 (基于 Z-Library 示例)
```json
{
  "zlibrary_id": "Z-Library ID",
  "date_added": "添加日期",
  "date_modified": "修改日期",
  "extension": "文件扩展名 (pdf/epub/mobi 等)",
  "filesize_reported": "报告的文件大小 (字节)",
  "md5_reported": "文件 MD5 哈希",
  "title": "书名",
  "author": "作者",
  "publisher": "出版社",
  "language": "语言代码",
  "series": "系列名",
  "volume": "卷号",
  "edition": "版本",
  "year": "出版年份",
  "pages": "页数",
  "description": "描述",
  "ipfs_cid": "IPFS 内容标识符 (可选)",
  "server_path": "服务器路径",
  "torrent": "Torrent 信息"
}
```

### 文件识别码体系
**主键标识**:
- **MD5**: 所有影子图书馆的主要文件标识符
- **IPFS CID**: 用于 IPFS 网络的内容寻址标识符
- **AACID**: Anna's Archive 全局唯一容器 ID

**附加标识符** (由源库决定):
- ISBN (国际标准书号)
- DOI (数字对象标识符)
- Open Library ID
- Google Books ID
- Amazon ID

**分类代码**:
- Dewey Decimal (杜威十进制分类法)
- UDC (国际十进制分类法)
- LCC (美国国会图书馆分类法)
- RVK, GOST 等

---

## 3. 数据量

### 截至 2026 年 1 月统计
- **书籍总数**: 61,654,285 本
- **论文总数**: 95,687,150 篇
- **Torrents 总大小**: 约 **1.1 PB** (1100 TB)

### 中文资源数据量
- **DuXiu 读秀**: 298 TB (元数据 + 部分文件)
  - 覆盖 1949 年以来 95% 以上的中文出版物
  - 主要包含学术书籍
- **CADAL**: 60 万+ 文件 (约一半为书籍或杂志)
- **国学大师资源库**: 约 8 万 PDF + 4000 EPUB
- **万方新方志**: 45,616 种地方志
- **台湾图书馆**: 约 2 TB

### Torrents 组织结构
分为三部分:
1. **Anna's Archive 自管理**: Z-Library、Internet Archive 的书籍/论文/杂志
2. **他人管理**: Library Genesis、Sci-Hub 等
3. **元数据记录**: WorldCat、ISBNdb 等网站的元数据

---

## 4. 中文书籍覆盖

### 主要来源
| 数据源 | 特点 | 备注 |
|--------|------|------|
| **DuXiu (读秀)** | 7.2M 元数据,95%+ 1949 后中文出版物 | 主要学术书籍,大部分为扫描件 |
| **Z-Library 中文集合** | 与 DuXiu 重叠但 MD5 不同 | 可能经过重新处理 |
| **CADAL** | 30 万+ 书籍/杂志 | 学术和历史文献 |
| **国学大师资源库** | 古籍为主 | 部分转换质量不佳 |
| **地方志** | 45,616 种 | 地方历史档案 |

### 质量评估
- **优点**:
  - DuXiu 覆盖广泛,元数据相对完整
  - 包含大量学术和古籍资源
- **缺点**:
  - 大多数为扫描 PDF,无 OCR 文本层
  - 部分文件格式转换失败 (如 PDG→PDF)
  - 元数据完整度取决于原始来源

---

## 5. IPFS CID 字段

### MD5 与 IPFS CID 的关系

**映射存在性**:
- Anna's Archive 的记录中**同时包含** MD5 和 IPFS CID
- **不需要转换**: 数据集中直接提供 IPFS CID 字段
- 映射文件格式: CSV 格式 `源库ID,IPFS_CID`

**示例映射**:
```csv
1,bafk2bzacedrabzierer44yu5bm7faovf5s4z2vpa3ry2cx6bjrhbjenpxifio
```

### IPFS 技术参数

**生成命令**:
```bash
ipfs add --progress=false --nocopy --recursive \
  --hash=blake2b-256 --chunker=size-1048576
```

**关键参数**:
- `--hash=blake2b-256`: 使用 BLAKE2b-256 哈希算法
- `--chunker=size-1048576`: 1MB (1048576 字节) 分块大小

**注意事项**:
- 必须使用**完全相同的参数**才能生成匹配的 CID
- 文件被切分为 1MB 块,每块获得独立 CID
- 文件本身获得一个引用所有块 CID 的顶层 CID

### IPFS 状态
- **历史**: Anna's Archive 曾尝试将约 600 万本 Z-Library 书籍放到 IPFS
- **现状**: 由于 IPFS 未达到生产就绪,团队后来放弃 IPFS,转向 **Torrents**
- **当前**: 部分记录仍保留 IPFS CID 字段,但主要分发通过 BitTorrent

---

## 6. LibGen 和 Z-Library 数据

### 数据源关系
- **Z-Library**: 2009 年作为 LibGen 的分支创建
- **共享来源**: 两者从相同源抓取电子书,内容高度重叠
- **差异**:
  - Z-Library 改进了搜索功能
  - 添加了新书目
  - 用户界面和元数据展示不同

### 元数据格式差异

**LibGen**:
- 使用 SQL 数据库 (scimag 表用于科学论文)
- 主要字段: 书名、作者、出版社、出版年、文件大小、文件类型、MD5
- `TimeAdded` 字段实际存储修改日期而非创建日期

**Z-Library**:
- 元数据更详细 (包含 `date_added`, `date_modified`)
- 包含 `zlibrary_id` 作为内部标识
- 更结构化的系列(series)和卷号(volume)字段

**Anna's Archive 处理方式**:
- **不合并记录**: 保留各源库的原始元数据
- **提取标识符**: 从文件名、描述中提取 ISBN、DOI 等
- **多源展示**: 同一本书可能有多条来自不同源的记录

---

## 7. 数据更新频率

### 更新机制
- **持续索引**: 从连接的影子图书馆持续获取新内容
- **无固定周期**: 更新取决于源库的数据可用性
- **元数据刷新**: 需要 **几周时间** 才能反映到 Anna's Archive

### 具体流程
1. 从源库(LibGen、Sci-Hub、Z-Library 等)下载最新数据 dump
2. 重新生成搜索索引 (ElasticSearch)
3. 更新 MariaDB 数据库
4. 生成新的 Torrent 文件

### 自行同步建议
- 定期下载预计算数据库的最新 Torrent
- 监控 [datasets 页面](https://annas-archive.li/datasets) 的更新公告
- 通过 [Anna's Blog](https://annas-archive.li/blog) 获取重大变更通知

---

## 8. ETL 注意事项

### 编码问题

**常见陷阱**:
1. **混合编码**: 同一数据集可能包含 UTF-8、GBK、Big5 编码的中文
2. **元数据损坏**: 部分扫描书籍的 PDF 元数据编码错误
3. **JSON 转义**: JSONL 中的非 ASCII 字符可能 Unicode 转义或原始保存

**解决方案**:
```python
import chardet

# 自动检测编码
def safe_decode(byte_data):
    detected = chardet.detect(byte_data)
    try:
        return byte_data.decode(detected['encoding'])
    except:
        return byte_data.decode('utf-8', errors='ignore')
```

### JSONL + Zstd 解压问题

**挑战**:
1. **窗口大小**: 部分 zstd 文件使用超大窗口 (>27),需调整参数
   ```bash
   zstd -d --long=31 input.jsonl.zst
   ```
2. **流式处理**: 解压后的 JSONL 可能数十 GB,不能一次性加载到内存
3. **逐行解析**: 必须使用流式 JSON 解析器

**推荐工具**:
- [zstd-jsonl-filter](https://github.com/uniQIndividual/zstd-jsonl-filter) (Rust 工具,边解压边过滤)
- Python: `zstandard` 库 + `ijson` (流式 JSON)

**示例代码**:
```python
import zstandard as zstd
import json

def stream_jsonl_zst(filepath):
    dctx = zstd.ZstdDecompressor(max_window_size=2**31)
    with open(filepath, 'rb') as f:
        with dctx.stream_reader(f) as reader:
            text_stream = reader.read()  # 或分块读取
            for line in text_stream.decode('utf-8').split('\n'):
                if line.strip():
                    yield json.loads(line)
```

### 字段缺失与不一致

**常见问题**:
| 字段 | 问题 | 处理方式 |
|------|------|----------|
| `language` | 可能为空、错误、不标准代码 | 使用 `langdetect` 重新检测 |
| `filesize_reported` | 与实际文件大小不符 | 下载后验证实际大小 |
| `year` | 格式混乱 (YYYY/MM-DD/纯文本) | 正则提取四位年份 |
| `author` | 多作者分隔符不统一 (`;` `/` `,`) | 统一化处理 |
| `md5` | 大小写混用 | 强制小写 `md5.lower()` |
| `ipfs_cid` | 大量记录为空 | 检查非空再使用 |

### 数据库导入优化

**MariaDB 导入**:
```sql
-- 使用 MyISAM 加速批量插入
ALTER TABLE books ENGINE=MyISAM;

-- 禁用索引更新
ALTER TABLE books DISABLE KEYS;

-- 批量插入
LOAD DATA INFILE 'data.csv' INTO TABLE books;

-- 重建索引
ALTER TABLE books ENABLE KEYS;
```

**ElasticSearch 索引**:
- 使用 `bulk` API 批量写入 (建议 1000-5000 条/批)
- 设置 `refresh_interval=-1` 关闭自动刷新
- 导入完成后执行 `POST _refresh`

### 重复数据处理

**场景**:
- 同一本书在 LibGen、Z-Library、CADAL 中都有记录
- MD5 相同但元数据不同

**去重策略**:
1. **按 MD5 聚合**: 优先保留元数据最完整的记录
2. **保留多源**: 存储 `source_libraries` 数组,记录所有来源
3. **元数据合并**: 取各源非空字段的并集

### 文件提取挑战

**核心难点**:
- 从数千种文件格式提取纯文本 (PDF/DJVU/CHM/PDG 等)
- 扫描 PDF 缺少 OCR 文本层
- 加密或损坏的文件

**工具推荐**:
- **PDF**: `pdfplumber` (带 OCR), `PyMuPDF`
- **DJVU**: `djvulibre` 命令行工具
- **EPUB/MOBI**: `ebooklib`, `calibre` 的 `ebook-convert`
- **OCR**: `tesseract` (中文需安装 `chi_sim`/`chi_tra` 语言包)

---

## 9. 实用代码片段

### 快速验证 MD5
```python
import hashlib

def verify_md5(filepath, expected_md5):
    """验证下载文件的 MD5 是否匹配"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest().lower() == expected_md5.lower()
```

### 解析 AACID
```python
def parse_aacid(aacid: str) -> dict:
    """解析 AACID 结构"""
    parts = aacid.split('__')
    if len(parts) < 4 or parts[0] != 'aacid':
        raise ValueError(f"Invalid AACID: {aacid}")

    return {
        'collection': parts[1],
        'timestamp': parts[2],
        'collection_id': parts[3] if len(parts) > 4 else None,
        'shortuuid': parts[-1]
    }
```

### 处理中文书名排序
```python
from pypinyin import lazy_pinyin

def chinese_sort_key(text: str) -> list:
    """生成中文拼音排序键"""
    return lazy_pinyin(text)

# 使用
books.sort(key=lambda x: chinese_sort_key(x['title']))
```

---

## 10. 参考资源

### 官方资源
- [Anna's Archive 主站](https://annas-archive.li/)
- [数据集页面](https://annas-archive.li/datasets)
- [官方博客](https://annas-archive.li/blog)
- [开源代码仓库](https://software.annas-archive.li/AnnaArchivist/annas-archive)

### 技术文档
- [AAC 标准规范](https://annas-archive.li/blog/annas-archive-containers.html)
- [IPFS 上传说明](https://annas-archive.li/blog/putting-5,998,794-books-on-ipfs.html)
- [中文资源完成公告](https://annas-archive.li/blog/finished-chinese-release.html)

### 社区工具
- [Anna's Archive MCP Server](https://github.com/iosifache/annas-mcp)
- [Torrents 帮助工具](https://github.com/cparthiv/annas-torrents)
- [Zstd-JSONL 过滤器](https://github.com/uniQIndividual/zstd-jsonl-filter)

### 元数据示例
- 访问任意书籍页面的 "Technical details" 标签查看原始 JSON
- 下载 [预计算数据库 Torrents](https://annas-archive.se/torrents#aa_derived_mirror_metadata)

---

## 数据来源说明

本笔记基于以下来源编写:
- [Anna's Archive - Wikipedia](https://en.wikipedia.org/wiki/Anna's_Archive)
- [Datasets - Anna's Archive](https://annas-archive.li/datasets)
- [AAC 容器标准](https://annas-archive.li/blog/annas-archive-containers.html)
- [IPFS 书籍上传](https://annas-archive.li/blog/putting-5,998,794-books-on-ipfs.html)
- [中文资源发布](https://annas-archive.li/blog/finished-chinese-release.html)
- [Torrents 页面](https://annas-archive.li/torrents)
- 公开的技术讨论和社区项目

最后更新: 2026-02-06
