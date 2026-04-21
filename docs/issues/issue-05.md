# Issue #5: OnCallAgent项目结构详解

| 属性 | 值 |
|------|-----|
| 状态 | 🟢 open |
| 标签 | 无标签 |
| 创建时间 | 2026-04-20 |
| 更新时间 | 2026-04-20 |
| 关闭时间 | 未关闭 |
| 评论数 | 0 |
| 链接 | [https://github.com/LittleParis/AgentTestingHelper/issues/5](https://github.com/LittleParis/AgentTestingHelper/issues/5) |

---

## 内容

# SuperBizAgent 项目分析报告

> 生成时间：2026-04-20

---

## 一、项目概览

| 属性 | 内容 |
|------|------|
| **项目名称** | SuperBizAgent |
| **定位** | 企业级智能业务代理系统 |
| **核心能力** | RAG 智能问答 + AIOps 智能运维 |
| **服务端口** | 9900 |
| **开发语言** | Java 17 |
| **主框架** | Spring Boot 3.2.0 |

---

## 二、技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Java | 17 | 开发语言 |
| Spring Boot | 3.2.0 | 应用框架 |
| Spring AI | 1.1.0 | AI Agent 框架 |
| Spring AI Alibaba | 1.1.0.0-RC2 | 阿里云 AI 集成 |
| DashScope SDK | 2.17.0 | 阿里云大模型 & 向量化服务 |
| Milvus SDK | 2.6.10 | 向量数据库 |
| Lombok | 1.18.30 | 代码生成 |
| Jackson | 2.17.0 | JSON 序列化 |
| OkHttp3 | 内置 | HTTP 客户端 |

---

## 三、项目目录结构

```
SuperBizAgent/
├── src/main/java/org/example/
│   ├── Main.java                          # 启动入口
│   ├── controller/                        # 控制器层
│   │   ├── ChatController.java            # 核心 API 入口（对话、运维）
│   │   ├── FileUploadController.java      # 文件上传
│   │   └── MilvusCheckController.java     # 向量库健康检查
│   ├── service/                           # 服务层
│   │   ├── ChatService.java               # 对话服务（ReactAgent 封装）
│   │   ├── RagService.java                # RAG 检索增强生成
│   │   ├── AiOpsService.java              # AIOps 多 Agent 运维
│   │   ├── VectorEmbeddingService.java    # 向量嵌入
│   │   ├── VectorIndexService.java        # 向量索引（文档入库）
│   │   ├── VectorSearchService.java       # 向量搜索
│   │   └── DocumentChunkService.java      # 文档分片
│   ├── agent/tool/                        # Agent 工具集
│   │   ├── DateTimeTools.java             # 时间工具
│   │   ├── InternalDocsTools.java         # 内部文档检索
│   │   ├── QueryMetricsTools.java         # Prometheus 告警查询
│   │   └── QueryLogsTools.java            # 云日志查询（CLS）
│   ├── config/                            # 配置类
│   │   ├── DashScopeConfig.java           # DashScope 客户端配置
│   │   ├── MilvusConfig.java              # Milvus 客户端配置
│   │   ├── MilvusProperties.java          # Milvus 连接属性
│   │   ├── DocumentChunkConfig.java       # 文档分片参数
│   │   ├── FileUploadConfig.java          # 文件上传配置
│   │   ├── WebConfig.java                 # Web 编码配置
│   │   └── WebMvcConfig.java              # CORS & 静态资源
│   ├── constant/
│   │   └── MilvusConstants.java           # Milvus 常量（集合名、维度等）
│   ├── client/
│   │   └── MilvusClientFactory.java       # Milvus 连接工厂
│   ├── dto/                               # 数据传输对象
│   │   ├── AIOpsRequest.java
│   │   ├── DocumentChunk.java
│   │   └── FileUploadRes.java
│   └── tool/
│       └── DropCollection.java            # 删除 Milvus Collection 工具
├── src/main/resources/
│   ├── application.yml                    # 应用配置
│   └── static/                            # 前端静态资源
│       ├── index.html
│       ├── app.js
│       └── styles.css
├── aiops-docs/                            # 运维知识文档库
│   ├── cpu_high_usage.md
│   ├── disk_high_usage.md
│   ├── memory_high_usage.md
│   ├── service_unavailable.md
│   └── slow_response.md
├── docs/
│   └── technical-doc-rag-agent-requirements.md  # 项目改造需求文档
├── vector-database.yml                    # Milvus Docker Compose 配置
├── pom.xml
└── Makefile
```

---

## 四、核心模块详解

### 4.1 控制器层（Controller）

#### ChatController — 核心 API 入口

所有对话和运维请求的统一入口，路径前缀 `/api`。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 普通对话，返回完整结果 |
| `/api/chat_stream` | POST | 流式对话，SSE 实时推送 |
| `/api/ai_ops` | POST | AIOps 智能运维，SSE 推送报告 |
| `/api/chat/clear` | POST | 清空指定会话历史 |
| `/api/chat/session/{sessionId}` | GET | 查询会话信息 |

**会话管理机制**：
- 基于 `sessionId` 隔离不同用户
- 内存存储（`ConcurrentHashMap`），重启后丢失
- 最多保留 6 对消息（用户 + AI 各一条为一对）
- 线程安全（`ReentrantLock`）

#### FileUploadController

- `POST /api/upload`：接收 txt/md 文件，自动触发向量化入库

#### MilvusCheckController

- `GET /milvus/health`：检查 Milvus 连接状态

---

### 4.2 服务层（Service）

#### ChatService — 对话服务

封装 ReactAgent 的创建和调用逻辑：

1. 创建 `DashScopeApi` 实例
2. 创建 `DashScopeChatModel`（支持自定义 temperature、maxToken、topP）
3. 动态构建系统提示词（注入历史消息）
4. 创建 `ReactAgent` 并绑定工具
5. 执行对话，返回结果

#### RagService — RAG 检索增强生成

直接调用 DashScope SDK（非 Spring AI 封装），实现流式 RAG 问答：

1. 向量检索相关文档片段
2. 拼接上下文 Prompt
3. 调用大模型（`qwen3-30b-a3b-thinking-2507`）流式生成答案

#### AiOpsService — 多 Agent 运维

采用 **Planner-Executor-Supervisor** 三层 Agent 架构：

- **Planner Agent**：拆解告警任务，制定排查计划，支持再规划
- **Executor Agent**：执行 Planner 分配的单步任务，调用工具收集证据
- **Supervisor Agent**：调度 Planner 和 Executor，控制整体流程直到输出最终报告

#### 向量服务三件套

| 服务 | 职责 |
|------|------|
| `VectorEmbeddingService` | 调用 DashScope Embedding API 生成向量（1024 维） |
| `VectorIndexService` | 文档切分 → 向量化 → 写入 Milvus |
| `VectorSearchService` | 查询向量 → Milvus L2 距离搜索 → 返回 TopK 结果 |

#### DocumentChunkService — 文档分片

智能分片策略（优先级从高到低）：

1. 按 Markdown 标题（`#`、`##`、`###`）分割
2. 按段落分割
3. 按最大长度（800 字符）截断，支持 100 字符重叠

---

### 4.3 Agent 工具层（agent/tool）

| 工具类 | 工具名 | 功能 |
|--------|--------|------|
| `DateTimeTools` | `getCurrentDateTime` | 获取当前日期时间 |
| `InternalDocsTools` | `queryInternalDocs` | 向量检索内部知识库 |
| `QueryMetricsTools` | `queryPrometheusAlerts` | 查询 Prometheus 告警（支持 Mock） |
| `QueryLogsTools` | `queryLogs` / `getAvailableLogTopics` | 查询腾讯云 CLS 日志（支持 Mock） |

`QueryLogsTools` 通过 MCP（Model Context Protocol）协议接入腾讯云 CLS，`required = false` 注入，Mock 模式下不需要真实连接。

---

### 4.4 配置层（Config）

| 配置类 | 关键参数 |
|--------|----------|
| `DashScopeConfig` | 超时 180s，OkHttpClient 配置 |
| `MilvusConfig` | 创建 `MilvusServiceClient` Bean，应用关闭时释放连接 |
| `MilvusProperties` | host=localhost, port=19530, database=default |
| `DocumentChunkConfig` | maxSize=800, overlap=100 |
| `FileUploadConfig` | path=./uploads, 允许 txt/md |
| `WebMvcConfig` | CORS 全域放行，静态资源映射 |

---

### 4.5 常量与工具

**MilvusConstants**：
```
集合名：biz
向量维度：1024（DashScope text-embedding-v3）
内容最大长度：8192
分片数：2
```

**MilvusClientFactory**：启动时自动检查并创建 Collection 和索引（IVF_FLAT）。

**DropCollection**：独立工具类，用于手动清空向量库（重建时使用）。

---

## 五、核心业务流程

### 5.1 文档入库流程

```
用户上传文件（txt/md）
        ↓
FileUploadController 接收文件，保存到 ./uploads
        ↓
VectorIndexService.indexSingleFile()
        ├── 读取文件内容
        ├── 删除 Milvus 中同名旧数据
        ├── DocumentChunkService.chunkDocument()
        │       ├── 按 Markdown 标题分割
        │       └── 按段落 + 长度限制分片
        ├── VectorEmbeddingService.generateEmbeddings()
        │       └── 调用 DashScope text-embedding-v3 API
        └── 批量插入向量 + 元数据到 Milvus
```

### 5.2 RAG 问答流程

```
用户发送问题（携带 sessionId）
        ↓
ChatController 获取/创建会话，读取历史消息
        ↓
ChatService.createReactAgent()（绑定所有工具）
        ↓
ReactAgent 自动决策是否调用工具
        ├── InternalDocsTools.queryInternalDocs()
        │       └── VectorSearchService 向量检索 TopK 文档片段
        └── 其他工具（时间、告警、日志）
        ↓
DashScope 大模型结合上下文生成答案
        ↓
返回答案（普通 / SSE 流式）
        ↓
ChatController 更新会话历史（滑动窗口 6 对）
```

### 5.3 AIOps 运维流程

```
触发 /api/ai_ops
        ↓
AiOpsService.executeAiOpsAnalysis()
        ↓
SupervisorAgent 启动编排
        ├── Planner Agent：分析告警，制定排查步骤
        │       └── 调用：QueryMetricsTools、DateTimeTools
        ├── Executor Agent：执行单步任务
        │       └── 调用：QueryLogsTools、InternalDocsTools
        ├── Planner Agent：基于执行结果再规划
        └── 循环直到 decision=FINISH
        ↓
提取 Markdown 格式《告警分析报告》
        ↓
SSE 流式推送给前端
```

---

## 六、前端架构

前端为纯静态页面，内嵌于 Spring Boot，无需独立部署。

**布局**：
- 左侧边栏：新建对话、历史会话列表（localStorage 持久化）
- 主内容区：欢迎语、消息气泡、输入框
- 模式切换：快速模式（普通请求）/ 流式模式（SSE）

**核心类 `SuperBizAgentApp`**：

| 方法 | 功能 |
|------|------|
| `sendMessage()` | 根据模式分发请求 |
| `sendQuickMessage()` | 调用 `/api/chat` |
| `sendStreamMessage()` | 调用 `/api/chat_stream`，监听 SSE |
| `addMessage()` | 渲染消息气泡 |
| `renderMarkdown()` | Markdown 渲染 + 代码高亮 |

---

## 七、知识文档库

### aiops-docs（运维知识库）

| 文件 | 告警类型 | 内容 |
|------|----------|------|
| `cpu_high_usage.md` | HighCPUUsage | CPU 高负载排查步骤与常见原因 |
| `memory_high_usage.md` | HighMemoryUsage | 内存泄漏、JVM 参数排查 |
| `disk_high_usage.md` | DiskHighUsage | 磁盘占用排查 |
| `service_unavailable.md` | ServiceUnavailable | 服务不可用排查（依赖、网络、资源） |
| `slow_response.md` | SlowResponse | 慢响应排查（DB、缓存、线程池） |

这些文档会被向量化入库，供 `InternalDocsTools` 检索使用。

### docs/technical-doc-rag-agent-requirements.md

项目改造需求文档，描述了将当前系统从"AIOps 运维平台"改造为"技术文档智能问答系统"的方向：
- 去除 AIOps 运维能力
- 强化 RAG 知识问答
- 面向初级 Java 后端开发者
- 增加用户账号体系和后台管理

---

## 八、关键配置（application.yml 摘要）

```yaml
server:
  port: 9900

milvus:
  host: localhost
  port: 19530

spring:
  ai:
    dashscope:
      api-key: <your-api-key>
      chat.options.timeout: 180000   # 3 分钟超时
    mcp:
      client:
        enabled: true                # 腾讯云 CLS MCP 接入

rag:
  top-k: 3                           # 检索 TopK 文档片段
  model: qwen3-30b-a3b-thinking-2507

document:
  chunk:
    max-size: 800
    overlap: 100
```

---

## 九、已知问题与改进建议

### 已知问题

| 问题 | 说明 |
|------|------|
| 会话内存存储 | 应用重启后会话历史全部丢失 |
| DashScope API 弃用警告 | 部分 `DashScopeChatOptions` 方法已标记 `@Deprecated` |
| OkHttp3 弃用警告 | `OkHttp3ClientHttpRequestFactory` 已弃用 |
| Mock 数据 | 告警和日志数据为模拟数据，非真实环境 |
| 无用字段 | `QueryLogsTools` 中 `VALID_REGIONS`、`DEFAULT_REGION` 未使用 |

### 改进建议

1. **持久化会话**：引入 MySQL 保存会话和消息历史
2. **用户认证**：添加 JWT 登录和权限管理
3. **后台管理**：文档管理、知识库统计、向量库可视化
4. **扩展文档格式**：支持 PDF、Word、HTML 等格式
5. **知识库分类**：支持多知识库和标签管理
6. **向量检索优化**：引入缓存，减少重复向量化开销
7. **监控接入**：添加 Actuator + Prometheus 应用监控

---

## 十、快速启动

```bash
# 1. 启动 Milvus 向量数据库
docker compose -f vector-database.yml up -d

# 2. 配置 DashScope API Key（application.yml 或环境变量）
export DASHSCOPE_API_KEY=your-api-key

# 3. 构建并启动
mvn clean package -DskipTests
mvn spring-boot:run

# 4. 访问 Web 界面
open http://localhost:9900
```

---

*本文档由 Kiro 自动分析生成，基于项目源码和配置文件。*

