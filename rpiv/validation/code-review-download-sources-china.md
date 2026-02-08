---
description: "代码审查报告: download-sources-china"
status: completed
created_at: 2026-02-08T12:00:00
updated_at: 2026-02-08T13:00:00
archived_at: null
---

# 代码审查报告

## 变更摘要

替换前端 `BookItem.vue` 中不可用的下载源（LibGen library.lol、LibGen libgen.li、Z-Library）为中国大陆可访问的站点（鸠摩搜索、24h搜书）。

**统计：**

- 修改的文件：1
- 添加的文件：0
- 删除的文件：0
- 新增行：4
- 删除行：8

## 验证结果

- **TypeScript 类型检查**：`vue-tsc --noEmit` 通过，无错误
- **后端测试**：10/10 通过（变更不涉及后端）
- **前端构建**：正常

## 发现的问题

### 问题 1

```
severity: medium
status: fixed
file: frontend/src/components/BookItem.vue
line: 10
issue: v-for 的 key 使用 fmt.extension 可能重复导致渲染错误
detail: 同一本书可以有多个相同 extension 的 format（如两个不同 MD5 的 PDF）。
        搜索 API 按 (title, author) 合并格式，但同一 extension 可能出现多次
        （不同 filesize/MD5 的同格式）。此时 :key="fmt.extension" 重复，
        Vue 会发出警告且 popover 状态可能混乱。
        这是既有问题，非本次变更引入，但值得记录。
suggestion: 改用 fmt.md5 作为 key，MD5 保证唯一：
        :key="fmt.md5"
```

### 问题 2

```
severity: low
status: fixed
file: frontend/src/components/BookItem.vue
line: 76-80
issue: 鸠摩搜索和 24h搜书的 URL 仅使用书名搜索，未利用 MD5
detail: Anna's Archive 使用 MD5 直接定位到具体文件，但鸠摩搜索和 24h搜书
        只能按书名搜索，搜索结果可能包含多个版本或无关结果。
        这是设计层面的限制而非代码错误——这两个站点不支持 MD5 查询。
        用户体验上，点击特定格式（如 EPUB 2.0MB）后跳转到的搜索页
        不一定能找到对应的文件。
suggestion: 考虑在 popover 中对非 MD5 直链的源标注"(搜索)"后缀，
        让用户知道这是搜索跳转而非精确下载链接。当前 Anna's Archive
        是精确链接，其他两个是模糊搜索，用户预期可能不一致。
```

### 问题 3

```
severity: low
status: fixed
file: frontend/src/components/BookItem.vue
line: 76
issue: 鸠摩搜索的搜索 URL 格式未经官方文档确认
detail: 鸠摩搜索官网使用 AJAX 动态加载搜索结果，
        URL https://www.jiumodiary.com/search?q=xxx 的行为未经充分验证。
        调研阶段 curl 测试返回 HTTP 200，但页面可能需要 JS 渲染
        才能显示搜索结果，或可能触发验证码/微信验证。
suggestion: 在浏览器中实际测试该 URL 是否能正确展示搜索结果。
        如果需要交互式验证，考虑改用首页 URL 让用户自行搜索。
```

## 未发现的问题类别

- **安全问题**：无。外部 URL 通过 `<a>` 标签带 `rel="noopener noreferrer"` 打开，`encodeURIComponent` 正确编码书名，无 XSS 风险
- **性能问题**：无。`getDownloadSources` 为纯计算函数，无网络请求
- **类型错误**：无。TypeScript 类型检查通过
- **逻辑错误**：无。`md5` 空值检查正确，`encodeURIComponent` 处理特殊字符正确
