---
description: "系统审查报告: ebook-search-platform"
status: archived
created_at: 2026-02-06T21:30:00
updated_at: 2026-02-06T21:50:00
archived_at: 2026-02-06T21:50:00
related_files:
  - rpiv/plans/plan-ebook-search-platform.md
  - rpiv/validation/code-review-ebook-search-platform.md
---

# 系统审查报告

## 元信息

- **审查的计划**：`rpiv/plans/plan-ebook-search-platform.md`
- **执行报告**：无（执行阶段未生成 execution-report，本身是一个流程偏离）
- **代码审查**：`rpiv/validation/code-review-ebook-search-platform.md`
- **日期**：2026-02-06

---

## 整体对齐分数：8/10

**理由**：实施高度忠实于计划，27 个任务全部完成，架构和文件结构完全匹配。代码审查发现的 18 个问题中 17 个已修复（94%），且修复方向与审查建议一致。扣分原因：(1) 执行报告缺失，无法追溯执行过程中的决策；(2) 计划中存在 6 处技术细节与执行时发现的实际情况不符，需要在执行时偏离。

---

## 偏离分析

### 偏离 1：异常捕获范围

```yaml
divergence: search 路由异常处理从 bare Exception 改为特定异常类型
planned: 计划任务 13 未指定异常捕获类型，代码示例中隐含使用通用 try/except
actual: 捕获 (MeilisearchError, ConnectionError, TimeoutError) 三种特定异常
reason: 代码审查问题 1 指出 bare Exception 会捕获编程错误（AttributeError 等），应区分业务异常和编程异常
classification: good ✅
justified: yes
root_cause: 计划中异常处理描述不够精确，仅给出路由签名和调用逻辑，未明确指定 except 子句的异常类型
```

### 偏离 2：搜索响应增加 total_books 字段

```yaml
divergence: SearchResponse 模型新增 total_books 字段
planned: 计划任务 9 定义 SearchResponse 只有 total/page/page_size/results 四个字段
actual: 增加了 total_books 字段，返回合并后的实际书籍数量
reason: 代码审查问题 2 指出 total（Meilisearch 原始命中数）与合并后的结果数不一致会导致分页混乱
classification: good ✅
justified: yes
root_cause: 计划在设计多格式合并逻辑时，未充分考虑合并对分页计数的影响。计划任务 13 描述了合并逻辑，但任务 9 的 schema 定义未同步更新
```

### 偏离 3：HEAD 请求状态码判断简化

```yaml
divergence: gateway_service 健康检查状态码判断从多状态码改为仅 200
planned: 计划任务 11 明确写 "状态码 200/301/302/307/308 视为可用"
actual: 使用 follow_redirects=True 后仅判断 status_code == 200
reason: 代码审查问题 4 指出 follow_redirects=True 会自动跟随重定向，最终拿到的是目标状态码，永远不会看到 3xx
classification: good ✅
justified: yes
root_cause: 计划中的 GOTCHA 列出了两个相互矛盾的指令：同时使用 follow_redirects=True 和检查 301/302/307/308。follow_redirects 与非200状态码检查是逻辑冲突的
```

### 偏离 4：get_db() 移除自动 commit

```yaml
divergence: 数据库 session 管理从自动 commit 改为不自动 commit
planned: 计划任务 6 代码示例中 get_db() 在 yield 后执行 await session.commit()
actual: 移除了自动 commit，仅在异常时 rollback
reason: 代码审查问题 6 指出纯读操作不需要 commit，且二次 commit 可能导致不可预期行为
classification: good ✅
justified: yes
root_cause: 计划直接复制了 fastapi_best_practices.md 的通用模式，未针对本项目以读操作为主（搜索、下载查询）的特点调整事务策略
```

### 偏离 5：env_file 从相对路径改为绝对路径

```yaml
divergence: config.py 中 env_file 使用绝对路径构建
planned: 计划任务 4 使用 env_file="../.env" 相对路径
actual: 使用 Path(__file__).resolve().parent.parent.parent / ".env" 绝对路径
reason: 代码审查问题 7 指出相对路径依赖工作目录，从不同位置启动会找不到 .env
classification: good ✅
justified: yes
root_cause: 计划中已在 GOTCHA 中提到 "env_file 路径是相对于运行目录的"，但给出的代码示例仍使用相对路径，GOTCHA 和代码示例不一致
```

### 偏离 6：asyncio.create_task 添加引用和清理

```yaml
divergence: lifespan 中保存 health_check_task 引用并在 shutdown 时 cancel
planned: 计划任务 17 使用 asyncio.create_task() 无变量接收
actual: health_check_task = asyncio.create_task(...)，shutdown 时检查并 cancel
reason: 代码审查问题 8 指出未被引用的 Task 可能被 GC 回收
classification: good ✅
justified: yes
root_cause: 计划中对 asyncio.create_task 的使用过于简略，未考虑 Python asyncio 的 Task 生命周期管理
```

### 偏离 7：ETL 导入脚本 dry_run 安全初始化

```yaml
divergence: engine 变量初始化为 None 而非在条件块中创建
planned: 计划任务 18 未明确 engine 的初始化策略
actual: engine = None if dry_run else create_engine(...)
reason: 代码审查问题 9 指出 dry_run 模式下 engine 未定义可能导致 NameError
classification: good ✅
justified: yes
root_cause: 计划对 dry_run 逻辑只描述了功能需求（"只解析不写入"），未设计具体的代码分支结构
```

### 偏离 8：Meilisearch 同步改用游标分页

```yaml
divergence: sync_meilisearch.py 从 OFFSET 分页改为 WHERE id > last_id 游标分页
planned: 计划任务 19 描述 "从 PostgreSQL 分批读取 books 数据（每批 5000 条）" 但未指定分页方式
actual: 使用 WHERE id > :last_id ORDER BY id LIMIT :limit 游标分页
reason: 代码审查问题 17 指出 OFFSET 分页在百万级数据上性能恶化
classification: good ✅
justified: yes
root_cause: 计划对批量读取的实现方式未做具体指定，默认的 OFFSET 方式在 MVP 数据量下可能尚可，但审查时前瞻性地优化
```

### 偏离 9：SearchPage.vue 搜索触发逻辑简化

```yaml
divergence: 移除 onMounted，仅用 watch + immediate:true 恢复搜索状态
planned: 计划任务 25 描述 "SearchPage 从 URL query 恢复搜索状态（route.query.q）" 但未指定具体实现方式
actual: 使用 watch(() => route.query, ..., { immediate: true }) 替代 onMounted + watch 双重触发
reason: 代码审查问题 18 指出 onMounted 和 watch 可能重复触发搜索请求
classification: good ✅
justified: yes
root_cause: 计划描述了功能需求但未给出 Vue3 组件生命周期层面的具体实现策略
```

### 偏离 10：GatewayHealth 添加 unique 约束

```yaml
divergence: gateway_url 字段添加 unique=True 约束
planned: 计划任务 8 中 gateway_url 只有 index=True
actual: 添加 unique=True, index=True
reason: 代码审查问题 14 指出并发执行可能插入重复记录
classification: good ✅
justified: yes
root_cause: 计划对数据完整性约束考虑不足，仅从查询性能角度添加了索引，未从并发安全角度添加唯一约束
```

### 偏离 11：缺少执行报告

```yaml
divergence: 执行完成后未生成 execution-report 文件
planned: execute.md 命令要求生成输出报告（第 85-105 行），并建议后续执行 execution-report 命令
actual: 直接跳过了 execution-report 生成，进入 code-review 阶段
reason: 未记录原因
classification: bad ❌
justified: no
root_cause: 流程跳步。execute.md 第 115 行建议 "/clear 后执行验证流程：/rpiv_loop:validation:code-review → /rpiv_loop:validation:execution-report → /rpiv_loop:validation:system-review"，但实际执行时可能因上下文切换或人工操作遗漏了 execution-report 步骤
```

### 偏离 12：计划中 OpenCC 参数错误

```yaml
divergence: 计划写 opencc.OpenCC('t2s.json') 但实际应用 opencc.OpenCC('t2s')
planned: 计划任务 18 GOTCHA 写 "OpenCC 转换：import opencc; converter = opencc.OpenCC('t2s.json')"
actual: 实际代码使用 opencc.OpenCC('t2s')（SDK 自动添加 .json 后缀）
reason: 项目记忆（MEMORY.md）明确记录 "OpenCC 初始化参数：用 't2s' 不是 't2s.json'"
classification: good ✅（执行时纠正了计划错误）
justified: yes
root_cause: 计划阶段的研究验证不充分。尽管项目记忆中已记录正确用法，计划仍写入了错误参数。规划命令缺少"交叉验证 MEMORY.md 已有记录"的步骤
```

---

## 模式遵循

- [x] 遵循了代码库架构（BFF 分层：Route → Service → DB/External）
- [x] 使用了已记录的模式（命名约定、日志模式、错误处理）
- [x] 正确应用了测试模式（pytest + pytest-asyncio，mock 外部依赖）
- [x] 满足了验证要求（17 个测试通过，ruff 检查通过）
- [x] 文件结构完全匹配计划定义（72 个新文件）
- [x] Meilisearch SDK 使用正确（AsyncClient API / Client ETL）
- [x] 前端组件模式一致（Composition API + composable + Naive UI）

---

## 系统改进行动

### 更新 CLAUDE.md：

- [ ] 记录 Python asyncio.create_task() 必须保存返回值的规则，避免 GC 回收未完成的任务
- [ ] 记录 SQLAlchemy get_db() 不应自动 commit 的模式（以读为主的应用）
- [ ] 添加反模式警告：httpx follow_redirects=True 与非200状态码检查互斥
- [ ] 记录 pydantic-settings env_file 必须使用基于 `__file__` 的绝对路径，而非相对路径

### 更新计划命令（plan-feature.md）：

- [ ] 在阶段 2 "代码库情报收集"中添加步骤：**交叉验证 MEMORY.md**，确保计划中的技术选型和参数与已记录的经验一致
- [ ] 在任务格式指南中添加 **GOTCHA 一致性检查**：GOTCHA 描述的问题必须在对应代码示例中体现修复方案，不能 GOTCHA 说一套、代码写另一套
- [ ] 添加数据库模型检查清单：唯一约束、并发安全、NULL 排序行为
- [ ] 在计划模板的"备注"部分添加"已知的计划局限性"小节，提前声明计划未覆盖的细节

### 创建新命令：

- [ ] 无需新命令。当前偏离均为一次性的技术决策修正，未发现重复 3 次以上的手动流程

### 更新执行命令（execute.md）：

- [ ] 在"完成后续"部分（第 109-116 行）将 execution-report 从"建议"改为"必须"：执行完成后**必须**生成 execution-report，不可跳过
- [ ] 添加执行偏离日志要求：每当偏离计划时，在执行过程中即时记录偏离原因（而非仅在最终报告中回顾），可以使用内联注释或 scratch 文件
- [ ] 在验证阶段添加检查项："确认计划中 GOTCHA 描述与实际代码一致"

---

## 关键学习

### 进展顺利的部分：

- **计划质量高**：27 个任务的功能描述、文件路径、依赖顺序全部准确，执行代理一次性完成实施
- **研究文档充分**：5 篇研究文档 + IPFS 网关研究覆盖了所有核心技术点，减少了执行时的探索成本
- **代码审查有效**：18 个问题全部切中实际缺陷，17 个修复彻底，无回归引入
- **信心分数准确**：计划给出 9/10，实际对齐分数 8/10，预估非常接近

### 需要改进的部分：

- **计划代码示例与 GOTCHA 不一致**：3 处计划中 GOTCHA 正确指出了风险，但代码示例仍包含有问题的写法（env_file 相对路径、follow_redirects+3xx、get_db 自动 commit）。这会误导执行代理按错误示例实现，而非遵循 GOTCHA 的警告
- **执行报告缺失**：validation 流程三步（code-review → execution-report → system-review）中 execution-report 被跳过，导致系统审查缺少执行过程的第一手记录，只能从代码审查报告间接推断偏离
- **OpenCC 参数在计划和 MEMORY.md 中矛盾**：MEMORY.md 明确记录了正确用法，但计划仍写入错误参数，说明规划阶段没有交叉验证项目记忆

### 下次实施：

- **代码示例双重检查**：计划中每个代码示例必须通过其对应 GOTCHA 的审查——如果 GOTCHA 说"X 有问题"，代码示例必须展示修复后的版本
- **强制 execution-report**：将其从可选流程提升为必须步骤，在 execute.md 中明确标记
- **MEMORY.md 交叉验证**：规划阶段新增检查点，将 MEMORY.md 中的已知问题与计划内容逐条比对
