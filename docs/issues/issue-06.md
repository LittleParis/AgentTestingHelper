# Issue #6: OncallAgent学习路线

| 属性 | 值 |
|------|-----|
| 状态 | 🟢 open |
| 标签 | 无标签 |
| 创建时间 | 2026-04-20 |
| 更新时间 | 2026-04-20 |
| 关闭时间 | 未关闭 |
| 评论数 | 0 |
| 链接 | [https://github.com/LittleParis/AgentTestingHelper/issues/6](https://github.com/LittleParis/AgentTestingHelper/issues/6) |

---

## 内容

# SuperBizAgent 项目学习路径

> 适合有 Java 基础、想系统学习 Spring AI + RAG + Agent 的开发者

---

## 学习前提

在开始之前，确保你具备以下基础：

- Java 基础语法（集合、泛型、Lambda）
- Spring Boot 基础（`@Component`、`@Service`、`@Autowired`、`@Value`）
- 了解 HTTP 和 REST API 概念
- 了解 Maven 依赖管理

不需要提前了解向量数据库或 AI 相关知识，项目本身就是最好的教材。

---

## 总体学习顺序

```
第一阶段：基础设施层（读懂项目骨架）
    ↓
第二阶段：向量数据库层（理解数据存储）
    ↓
第三阶段：RAG 核心链路（理解检索增强生成）
    ↓
第四阶段：Agent 工具层（理解工具调用机制）
    ↓
第五阶段：对话与编排层（理解完整业务流程）
    ↓
第六阶段：AIOps 多 Agent（进阶：多 Agent 协作）
```

---

## 第一阶段：基础设施层

> 目标：搞清楚项目怎么启动、配置怎么加载、各个 Bean 怎么组织

### Step 1 — `application.yml`

**文件路径**：`src/main/resources/application.yml`

这是整个项目的配置中心，先读它，你才知道项目依赖哪些外部服务。

重点关注：
- `server.port: 9900` — 服务端口
- `milvus.*` — 向量数据库连接配置
- `spring.ai.dashscope.api-key` — 阿里云大模型 API Key
- `rag.top-k` — 检索时返回几条相似文档
- `prometheus.*` / `cls.*` — AIOps 相关配置，`mock-enabled` 控制是否用假数据

**学习重点**：理解 `@Value("${xxx}")` 和 `@ConfigurationProperties` 两种注入方式的区别。

---

### Step 2 — `MilvusProperties.java`

**文件路径**：`src/main/java/org/example/config/MilvusProperties.java`

```java
@Configuration
@ConfigurationProperties(prefix = "milvus")
public class MilvusProperties { ... }
```

这是最简单的配置类，只有 getter/setter，没有任何业务逻辑。

**学习重点**：`@ConfigurationProperties` 如何把 yml 里的 `milvus.host`、`milvus.port` 自动绑定到 Java 字段上。这比 `@Value` 更适合管理一组相关配置。

---

### Step 3 — `MilvusConstants.java`

**文件路径**：`src/main/java/org/example/constant/MilvusConstants.java`

```java
public static final String MILVUS_COLLECTION_NAME = "biz";
public static final int VECTOR_DIM = 1024;
```

最简单的常量类，私有构造器防止实例化。

**学习重点**：为什么向量维度是 1024？这是由 DashScope `text-embedding-v3` 模型决定的，向量维度必须和 Milvus Collection 定义时保持一致，否则插入会报错。

---

### Step 4 — `DocumentChunkConfig.java` 和 `FileUploadConfig.java`

**文件路径**：`src/main/java/org/example/config/`

两个简单的配置 Bean，分别管理文档分片参数（maxSize=800, overlap=100）和文件上传参数。

**学习重点**：配置类和业务类分离的设计思想——业务类通过 `@Autowired` 注入配置类，而不是直接 `@Value` 散落在各处。

---

### Step 5 — `Main.java`

**文件路径**：`src/main/java/org/example/Main.java`

Spring Boot 启动入口，通常只有几行代码。

**学习重点**：`@SpringBootApplication` 背后做了什么（组件扫描、自动配置、Bean 注册）。

---

## 第二阶段：向量数据库层

> 目标：理解 Milvus 是什么、Collection 怎么建、向量怎么存

### Step 6 — `MilvusClientFactory.java`

**文件路径**：`src/main/java/org/example/client/MilvusClientFactory.java`

这是连接 Milvus 的工厂类，启动时自动执行：

```
连接 Milvus → 检查 Collection 是否存在 → 不存在则创建 → 创建索引
```

重点读 `createBizCollection()` 方法，它定义了 Collection 的 Schema：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | VarChar(256) | 主键，由文件路径+分片序号生成的 UUID |
| `vector` | FloatVector(1024) | 文本的向量表示 |
| `content` | VarChar(8192) | 原始文本内容 |
| `metadata` | JSON | 文件名、分片序号等元信息 |

再读 `createIndexes()`，理解 `IVF_FLAT` 索引和 `L2` 距离度量的含义：
- **IVF_FLAT**：倒排文件索引，把向量分成若干簇，搜索时只在最近的几个簇里找，速度快
- **L2（欧氏距离）**：两个向量之间的直线距离，值越小越相似

**学习重点**：向量数据库的 Collection 类似关系型数据库的 Table，但多了一个专门存向量的字段，以及专门为向量设计的索引。

---

### Step 7 — `MilvusConfig.java`

**文件路径**：`src/main/java/org/example/config/MilvusConfig.java`

把 `MilvusClientFactory` 创建的客户端注册为 Spring Bean，并在应用关闭时调用 `client.close()` 释放连接。

**学习重点**：`@Bean` + `@PreDestroy` 的资源管理模式。

---

## 第三阶段：RAG 核心链路

> 目标：理解文档怎么入库、查询时怎么检索、检索结果怎么喂给大模型

### Step 8 — `DocumentChunkService.java`

**文件路径**：`src/main/java/org/example/service/DocumentChunkService.java`

文档分片是 RAG 的第一步。这个类实现了一个智能分片策略：

```
输入：完整文档文本
    ↓
splitByHeadings()：按 Markdown 标题（#、##、###）切成若干章节
    ↓
chunkSection()：对每个章节，如果超过 800 字符则按段落进一步切分
    ↓
getOverlapText()：相邻分片保留 100 字符重叠，避免语义在边界断裂
    ↓
输出：List<DocumentChunk>，每个分片有内容、标题、起止位置、序号
```

**为什么要分片？** 大模型有 Token 限制，不能把整篇文档塞进去。分片后每次只取最相关的几段，既节省 Token 又提高精度。

**学习重点**：正则表达式 `Pattern.compile("^(#{1,6})\\s+(.+)$", Pattern.MULTILINE)` 如何匹配 Markdown 标题；重叠（overlap）的作用。

---

### Step 9 — `VectorEmbeddingService.java`

**文件路径**：`src/main/java/org/example/service/VectorEmbeddingService.java`

把文本转换成向量（Embedding）。核心调用：

```java
TextEmbeddingParam param = TextEmbeddingParam.builder()
    .model(model)           // text-embedding-v3
    .texts(contents)        // 要向量化的文本列表
    .build();
TextEmbeddingResult result = textEmbedding.call(param);
```

注意 `getFloats()` 方法：DashScope API 返回的是 `List<Double>`，而 Milvus 存储用 `List<Float>`，这里做了类型转换。

**学习重点**：什么是 Embedding？文本 → 向量的过程就是让模型把语义信息压缩成一个固定长度的数字数组，语义相近的文本，其向量在空间中距离也近。`@PostConstruct` 的作用（Bean 初始化完成后执行）。

---

### Step 10 — `VectorIndexService.java`

**文件路径**：`src/main/java/org/example/service/VectorIndexService.java`

把分片后的文档存入 Milvus，是第 8、9 步的组合：

```
读取文件内容
    ↓
deleteExistingData()：删除同名文件的旧数据（支持更新）
    ↓
DocumentChunkService.chunkDocument()：分片
    ↓
VectorEmbeddingService.generateEmbedding()：逐片向量化
    ↓
insertToMilvus()：插入向量 + 元数据
```

重点看 `insertToMilvus()` 中 ID 的生成方式：

```java
String id = UUID.nameUUIDFromBytes((source + "_" + chunkIndex).getBytes()).toString();
```

用文件路径 + 分片序号生成确定性 UUID，同一个分片每次生成的 ID 相同，方便幂等更新。

**学习重点**：`InsertParam.Field` 如何构建多字段插入；元数据（metadata）的 JSON 存储方式。

---

### Step 11 — `VectorSearchService.java`

**文件路径**：`src/main/java/org/example/service/VectorSearchService.java`

查询时的向量检索，是入库的逆过程：

```
用户问题（文本）
    ↓
VectorEmbeddingService.generateQueryVector()：问题向量化
    ↓
SearchParam：构建搜索参数（指定集合、向量字段、TopK、L2 距离）
    ↓
milvusClient.search()：在 Milvus 中找最近的 K 个向量
    ↓
SearchResultsWrapper：解析结果，提取 id、content、score、metadata
    ↓
返回 List<SearchResult>
```

注意 `score` 字段：L2 距离，**值越小表示越相似**（和余弦相似度相反）。

**学习重点**：`withOutFields()` 的作用（告诉 Milvus 除了向量还要返回哪些字段）；`nprobe` 参数（搜索时访问的簇数量，越大越精确但越慢）。

---

### Step 12 — `RagService.java`

**文件路径**：`src/main/java/org/example/service/RagService.java`

RAG 的最后一步：把检索到的文档片段拼成上下文，连同用户问题一起发给大模型。

```
用户问题
    ↓
VectorSearchService.searchSimilarDocuments()：检索 TopK 相关片段
    ↓
buildContext()：把片段拼成 "参考资料" 文本块
    ↓
buildPrompt()：构建完整 Prompt（系统提示 + 参考资料 + 历史消息 + 用户问题）
    ↓
generation.streamCall()：流式调用 DashScope 大模型
    ↓
StreamCallback 回调：逐 Token 推送给调用方
```

**学习重点**：RAG 的核心思想——不是让模型凭空回答，而是先检索相关资料，再让模型基于资料回答，减少幻觉。`Flowable`（RxJava）的流式处理模式。

---

## 第四阶段：Agent 工具层

> 目标：理解 Spring AI 的工具调用机制，以及如何定义一个 Agent 工具

### Step 13 — `DateTimeTools.java`

**文件路径**：`src/main/java/org/example/agent/tool/DateTimeTools.java`

最简单的工具类，只有一个方法：

```java
@Tool(description = "Get the current date and time in the user's timezone")
public String getCurrentDateTime() {
    return LocalDateTime.now().atZone(LocaleContextHolder.getTimeZone().toZoneId()).toString();
}
```

**学习重点**：`@Tool` 注解的作用——Spring AI 会把这个方法的签名和 description 序列化成 JSON，发给大模型，大模型决定是否调用它。这就是 Function Calling 的核心机制。

---

### Step 14 — `InternalDocsTools.java`

**文件路径**：`src/main/java/org/example/agent/tool/InternalDocsTools.java`

RAG 检索工具，是 Agent 调用向量库的入口：

```java
@Tool(description = "Use this tool to search internal documentation...")
public String queryInternalDocs(
    @ToolParam(description = "Search query describing what information you are looking for")
    String query) {
    List<VectorSearchService.SearchResult> results = vectorSearchService.searchSimilarDocuments(query, topK);
    return objectMapper.writeValueAsString(results);  // 返回 JSON 字符串给大模型
}
```

**学习重点**：`@ToolParam` 注解的 description 非常重要，大模型靠这个描述来决定传什么参数。工具的返回值是字符串（通常是 JSON），大模型会解读这个字符串再继续推理。

---

### Step 15 — `QueryMetricsTools.java`

**文件路径**：`src/main/java/org/example/agent/tool/QueryMetricsTools.java`

Prometheus 告警查询工具，展示了一个更复杂的工具实现：

- `mockEnabled` 控制是否返回真实数据
- `buildMockAlerts()` 构造模拟告警（与 `aiops-docs/` 文档对应）
- `fetchPrometheusAlerts()` 用 OkHttp 调用真实 Prometheus API
- 内部定义了多个数据模型类（`@Data` + Lombok）

**学习重点**：工具类如何封装外部 API 调用；Mock 模式的设计思路（开发阶段不依赖真实环境）；`@PostConstruct` 初始化 OkHttpClient。

---

## 第五阶段：对话与编排层

> 目标：理解 ReactAgent 如何把工具调用和大模型推理串联起来

### Step 16 — `ChatService.java`

**文件路径**：`src/main/java/org/example/service/ChatService.java`

封装了 ReactAgent 的创建和执行逻辑：

```
createDashScopeApi()        → 创建 API 连接
createStandardChatModel()   → 创建大模型实例（绑定 temperature、maxToken 等参数）
buildSystemPrompt()         → 构建系统提示词（注入历史消息）
createReactAgent()          → 创建 ReactAgent，绑定所有工具
executeChat()               → 执行对话，返回最终答案
```

**学习重点**：`ReactAgent` 是 ReAct（Reasoning + Acting）模式的实现——模型先推理（Thought），再决定调用哪个工具（Action），拿到工具结果后继续推理，直到得出最终答案（Final Answer）。

---

### Step 17 — `ChatController.java`

**文件路径**：`src/main/java/org/example/controller/ChatController.java`

所有 API 的入口，重点读三个接口：

**`/api/chat`（普通对话）**：
```
接收请求 → 获取/创建 Session → 读取历史消息
→ ChatService 创建 ReactAgent → 执行对话 → 更新历史 → 返回结果
```

**`/api/chat_stream`（流式对话）**：
```
创建 SseEmitter → 异步线程执行对话
→ ReactAgent.stream() 逐步输出 → 每个 Token 通过 SSE 推送给前端
→ 发送 [DONE] 信号 → 关闭 Emitter
```

**会话管理**：
```java
private final Map<String, SessionInfo> sessions = new ConcurrentHashMap<>();
private static final int MAX_WINDOW_SIZE = 6;  // 最多保留 6 对消息
```

**学习重点**：SSE（Server-Sent Events）的工作原理；`ConcurrentHashMap` + `ReentrantLock` 保证线程安全；滑动窗口控制历史消息长度。

---

### Step 18 — `FileUploadController.java`

**文件路径**：`src/main/java/org/example/controller/FileUploadController.java`

文件上传接口，触发文档入库流程：

```
接收 MultipartFile → 校验格式（txt/md）→ 保存到 ./uploads
→ VectorIndexService.indexSingleFile() → 返回上传结果
```

**学习重点**：`MultipartFile` 的处理；文件上传后自动触发向量化的设计（上传即入库）。

---

## 第六阶段：AIOps 多 Agent（进阶）

> 目标：理解 Planner-Executor-Supervisor 多 Agent 协作架构

### Step 19 — `AiOpsService.java`

**文件路径**：`src/main/java/org/example/service/AiOpsService.java`

多 Agent 协作的核心，理解三个角色：

```
SupervisorAgent（调度者）
    ├── PlannerAgent（规划者）
    │       职责：分析告警 → 制定排查步骤 → 基于执行结果再规划
    │       工具：QueryMetricsTools、DateTimeTools
    └── ExecutorAgent（执行者）
            职责：执行 Planner 分配的单步任务 → 收集证据
            工具：QueryLogsTools、InternalDocsTools
```

执行流程：
```
Supervisor 启动
    → Planner 分析告警，制定计划
    → Executor 执行第一步
    → Planner 基于结果再规划
    → 循环直到 decision=FINISH
    → 输出《告警分析报告》
```

**学习重点**：多 Agent 协作的价值在于任务分工——Planner 负责"想清楚做什么"，Executor 负责"真正去做"，Supervisor 负责"协调两者"。这比单个 Agent 处理复杂任务更可靠。

---

### Step 20 — `QueryLogsTools.java`

**文件路径**：`src/main/java/org/example/agent/tool/QueryLogsTools.java`

日志查询工具，通过 MCP（Model Context Protocol）协议接入腾讯云 CLS。

注意注入方式：
```java
@Autowired(required = false)  // Mock 模式下不需要真实连接
private QueryLogsTools queryLogsTools;
```

**学习重点**：`required = false` 的含义（Bean 不存在时不报错）；MCP 协议是什么（一种标准化的工具调用协议，让 AI 模型能调用外部服务）。

---

## 学习路径总览

```
application.yml          ← 先看配置，了解全局
    ↓
MilvusProperties         ← 配置绑定方式
MilvusConstants          ← 常量定义
    ↓
MilvusClientFactory      ← 向量库连接和 Schema 定义
MilvusConfig             ← Bean 注册
    ↓
DocumentChunkService     ← 文档分片（RAG 第一步）
VectorEmbeddingService   ← 文本向量化（RAG 第二步）
VectorIndexService       ← 文档入库（组合前两步）
VectorSearchService      ← 向量检索（RAG 查询）
RagService               ← 检索 + 生成（RAG 完整链路）
    ↓
DateTimeTools            ← 最简单的工具
InternalDocsTools        ← RAG 检索工具
QueryMetricsTools        ← 外部 API 工具
    ↓
ChatService              ← ReactAgent 封装
ChatController           ← API 入口 + 会话管理
FileUploadController     ← 文件上传入口
    ↓
AiOpsService             ← 多 Agent 协作（进阶）
QueryLogsTools           ← MCP 工具（进阶）
```

---

## 推荐学习方式

**边读边跑**：每读完一个类，在本地启动项目，用 curl 或前端页面验证对应功能。

```bash
# 启动 Milvus
docker compose -f vector-database.yml up -d

# 启动应用
mvn spring-boot:run

# 上传文档测试（对应 Step 17-18）
curl -X POST http://localhost:9900/api/upload -F "file=@aiops-docs/cpu_high_usage.md"

# 普通对话测试（对应 Step 16-17）
curl -X POST http://localhost:9900/api/chat \
  -H "Content-Type: application/json" \
  -d '{"Id":"test-1","Question":"CPU 使用率高怎么排查？"}'

# 流式对话测试
curl -X POST http://localhost:9900/api/chat_stream \
  -H "Content-Type: application/json" \
  -d '{"Id":"test-1","Question":"什么是向量数据库？"}'
```

**加日志**：在关键方法里加 `System.out.println` 或断点，观察数据在各层之间的流转。

**改配置**：把 `rag.top-k` 从 3 改成 1 或 5，观察回答质量的变化，直观理解 TopK 的作用。

---

## 关键概念速查

| 概念 | 在哪里体现 | 一句话解释 |
|------|-----------|-----------|
| Embedding | `VectorEmbeddingService` | 把文本转成数字向量，语义相近的文本向量距离近 |
| RAG | `RagService` + `VectorSearchService` | 先检索相关文档，再让模型基于文档回答 |
| 文档分片 | `DocumentChunkService` | 把长文档切成小块，每块独立向量化和检索 |
| Function Calling | `@Tool` 注解 | 大模型决定调用哪个函数，并传入参数 |
| ReactAgent | `ChatService.createReactAgent()` | 推理→行动→推理的循环，直到得出答案 |
| SSE | `ChatController.chatStream()` | 服务端主动推送，实现流式输出效果 |
| 多 Agent | `AiOpsService` | 多个专职 Agent 分工协作，处理复杂任务 |
| MCP | `QueryLogsTools` | 标准化工具调用协议，连接 AI 和外部服务 |

---

*祝学习顺利。遇到不懂的地方，先跑起来看效果，再回头读代码，效果最好。*

