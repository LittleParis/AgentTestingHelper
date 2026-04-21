# Issue #7: 对话记录

| 属性 | 值 |
|------|-----|
| 状态 | 🟢 open |
| 标签 | 无标签 |
| 创建时间 | 2026-04-20 |
| 更新时间 | 2026-04-20 |
| 关闭时间 | 未关闭 |
| 评论数 | 0 |
| 链接 | [https://github.com/LittleParis/AgentTestingHelper/issues/7](https://github.com/LittleParis/AgentTestingHelper/issues/7) |

---

## 内容

# 学习会话上下文记录

> 本文件记录了本次学习会话的完整内容，供下次会话继续使用。
> 生成时间：2026-04-20

---

## 项目基本信息

- **项目名**：SuperBizAgent
- **项目路径**：`C:\Users\chenmz\Desktop\oncallagent`
- **定位**：企业级智能业务代理系统，包含 RAG 智能问答 + AIOps 智能运维两大模块
- **技术栈**：Java 17 + Spring Boot 3.2.0 + Spring AI 1.1.0 + Spring AI Alibaba 1.1.0.0-RC2 + DashScope SDK 2.17.0 + Milvus SDK 2.6.10
- **服务端口**：9900

已生成两份参考文档：
- `project-analysis.md`：项目完整结构分析
- `learning-path.md`：推荐学习路径（20个步骤，6个阶段）

---

## 本次会话已学习的内容

### 已完成的学习步骤（对应 learning-path.md）

| 步骤 | 文件 | 状态 |
|------|------|------|
| Step 1 | `application.yml` | ✅ 已在项目分析中覆盖 |
| Step 2 | `MilvusProperties.java` | ✅ 已在项目分析中覆盖 |
| Step 3 | `MilvusConstants.java` | ✅ 已在项目分析中覆盖 |
| Step 8 | `DocumentChunkService.java` | ✅ 深度讲解完毕 |
| Step 9 | `VectorEmbeddingService.java` | ✅ 深度讲解完毕 |
| Step 10 | `VectorIndexService.java` | ✅ 深度讲解完毕 |

**下次从 Step 11 开始**：`VectorSearchService.java`

---

## 各文件核心知识点速记

### `DocumentChunkService.java`

**分片策略两级切割**：
1. `splitByHeadings()`：用正则 `^(#{1,6})\s+(.+)$` 按 Markdown 标题切成 Section
2. `chunkSection()`：对超过 800 字的 Section，按 `\n\n` 段落继续切，每片 ≤ 800 字

**核心循环逻辑**（`chunkSection` 里）：
- 先判断加上新段落是否超限，再追加——触发切割的段落不会丢失，切割后追加到新缓冲区
- `currentChunk.length() > 0` 这个条件保证第一个段落无论多长都直接放进去

**Overlap 机制**（`getOverlapText`）：
- 取上一个分片末尾 100 字作为下一个分片的开头
- 在 overlap 的后半段找最后一个中文句号（`。？！`），从句号后开始，保证新分片从完整句子开头
- `> overlapSize / 2` 的判断：句号必须在后半段才采用，防止 overlap 被无效延长
- **局限**：只处理中文标点，英文句号 `.` 不处理

**已知局限**：
- 单个段落超过 800 字不会强制截断
- startIndex 在有 overlap 时是近似值

---

### `VectorEmbeddingService.java`

**职责**：只负责文本 → 向量，不知道 Milvus 的存在

**初始化**（`@PostConstruct init()`）：
- 校验 API Key，启动时就报错而不是运行时才发现
- `Constants.apiKey = apiKey`：DashScope 原生 SDK 用全局静态变量存 Key
- 每次调用前都重新检查 `Constants.apiKey`，防止被其他地方覆盖

**类型转换**（`getFloats()`）：
- DashScope 返回 `List<Double>`，Milvus 存储用 `List<Float>`
- Float 4字节 vs Double 8字节，1024维向量节省一半空间，精度损失可接受
- `new ArrayList<>(embeddingDoubles.size())` 预分配容量，避免扩容

**单条 vs 批量**：
- `generateEmbedding()`：单条，`Collections.singletonList(content)` 包成列表
- `generateEmbeddings()`：批量，一次 HTTP 请求处理多条，效率更高
- `generateQueryVector()`：查询时用，内部直接调 `generateEmbedding()`

**余弦相似度**（`calculateCosineSimilarity()`）：
- 项目里实际未被调用，是备用工具方法
- 公式：`cos(θ) = (A·B) / (||A|| × ||B||)`，结果 [-1,1]，越大越相似
- Milvus 实际用的是 L2 距离（越小越相似，方向相反）

---

### `VectorIndexService.java`

**职责**：总指挥，串联 DocumentChunkService + VectorEmbeddingService + Milvus 写入

**主流程** `indexSingleFile()`：
```
读文件 → 删旧数据 → 分片 → 逐片(向量化 + 写库)
```

**注意**：逐片调用 `generateEmbedding()`（非批量），有 N 个分片就发 N 次 HTTP 请求，是可优化点

**删旧数据** `deleteExistingData()`：
- 用 Milvus 表达式过滤：`metadata["_source"] == "路径"`
- Windows 路径要把 `\` 替换成 `/`，否则 Milvus 找不到记录
- 状态码 `65535` = 集合已加载（不是错误，要放行）

**元数据** `buildMetadata()`：
- 存入：`_source`（完整路径）、`_file_name`、`_extension`、`chunkIndex`、`totalChunks`、`title`
- 用途：检索后溯源，告诉用户答案来自哪个文件哪个章节

**写入 Milvus** `insertToMilvus()`：
- ID 生成：`UUID.nameUUIDFromBytes((source + "_" + chunkIndex).getBytes())`
  - 确定性 UUID：相同输入永远生成相同 ID，支持幂等更新
- 字段构建：Milvus 插入 API 按字段分别传，每个字段值包成 `singletonList`
- metadata 要转成 Gson 的 `JsonObject`，不能直接传 `Map`
- 返回值 `R<T>`：`getStatus() == 0` 成功，非 0 失败

**IndexingResult 内部类**：
- `successCount` / `failCount` 没有 `@Setter`，只能通过 `increment*()` 累加
- 防止外部随意篡改计数，是有意的封装设计

---

## 下次会话建议继续的内容

按 `learning-path.md` 的顺序，下次从 **Step 11** 开始：

### Step 11 — `VectorSearchService.java`
查询时的向量检索，是入库的逆过程：
- 问题向量化 → Milvus 搜索 → 解析结果
- 理解 `SearchParam` 的构建（`withOutFields`、`nprobe` 参数）
- 理解 L2 距离分数的含义（越小越相似）

### Step 12 — `RagService.java`
RAG 完整链路的最后一步：
- 检索结果拼成上下文 Prompt
- 流式调用 DashScope 大模型
- `Flowable`（RxJava）流式处理

### Step 13-15 — Agent 工具层
- `DateTimeTools`：最简单的 `@Tool` 注解用法
- `InternalDocsTools`：RAG 检索工具，`@ToolParam` 的作用
- `QueryMetricsTools`：外部 API 工具 + Mock 模式设计

### Step 16-17 — 对话与编排层
- `ChatService`：ReactAgent 的创建和执行
- `ChatController`：SSE 流式输出、会话管理、滑动窗口

---

## 给下次 Agent 的提示

1. 用户正在系统学习这个 Spring AI + RAG + Agent 项目的源码
2. 学习风格：逐方法深入讲解，配合具体数据举例，喜欢了解设计原因和局限性
3. 已经理解的概念：文档分片、Overlap、向量嵌入、Double→Float 转换、确定性 UUID、Milvus 表达式过滤
4. 下次直接从 `VectorSearchService.java` 开始讲，不需要重新介绍项目背景
5. 讲解时可以引用已学内容做对比（比如"和 VectorIndexService 里的插入相反"）

