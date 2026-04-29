# GitHub Issues 列表

**仓库**: LittleParis/AgentTestingHelper
**更新时间**: 2026-04-21 22:32:47
**总数**: 8

---

## 🟢 #8: playwright cli

- **状态**: open
- **标签**: 无标签
- **创建时间**: 2026-04-21
- **链接**: [https://github.com/LittleParis/AgentTestingHelper/issues/8](https://github.com/LittleParis/AgentTestingHelper/issues/8)

### 描述

# AI 驱动的 Web 全流程自动化测试平台

> 面试讲解用文档 | 项目：UIAutoTest

---

## 一句话介绍

**基于 AI Agent + playwright-cli 的 Web 全流程自动化测试平台，能从需求文档自动生成测试用例、驱动浏览器执行、输出缺陷报告并推送飞书通知，全程零人工干预。**

---

## 项目背景

跨境支付业务官网每次迭代都需要覆盖多站点（Global/HK/CN）、多语言（中/英）、多视口（PC/平板/移动端）的回归测试，人工测试成本高、容易遗漏。这个平台的目标是：**输入需求文档，自动输出测试结论**。

---

## 整体架构（四层）

```
┌─────────────────────────────────────────────────────────┐
│                第一层：AI Agent 调度层                   │
│                                                         │
│  Kiro AI + Steering 文件（test-engineer.md）            │
│  → 定义测试工作流、角色规范、执行标准                    │
│  → 读取需求文档、生成用例、驱动执行、输出报告            │
└────────────────────┬────────────────────────────────────┘
                     ↓ 调用
┌────────────────────────────────────────────────────────┐
│                第二层：Python 工具层（BaseTool）         │
│                                                        │
│  pdf_reader.py          需求文档解析（PDF → 文本）      │
│  test_case_writer.py    生成测试用例/缺陷清单 Excel     │
│  bug_reporter.py        Bug 收集、管理、格式转换        │
│  feishu_notifier.py     飞书机器人通知                  │
│  parallel_test_runner.py 多站点并行测试执行器           │
│  kb_search.py           本地知识库/源码搜索             │
│  feiShuRobot/           Bug 按规则分发到不同飞书群      │
└────────────────────┬───────────────────────────────────┘
                     ↓ 驱动
┌────────────────────────────────────────────────────────┐
│              第三层：playwright-cli 浏览器层            │
│                                                        │
│  open / goto / click / fill / eval / screenshot        │
│  snapshot（获取页面元素快照）                           │
│  state-save / state-load（登录态持久化）                │
│  -s=<session>（多会话并行）                             │
└────────────────────┬───────────────────────────────────┘
                     ↓ 访问
┌────────────────────────────────────────────────────────┐
│                第四层：被测系统（测试环境）              │
│                                                        │
│  global.lianlianpay-inc.com  （Global 站）             │
│  hk.lianlianpay-inc.com      （HK 站）                 │
│  cn.lianlianpay-inc.com      （CN 站）                 │
└────────────────────────────────────────────────────────┘
```

---

## 测试全流程（4 个 Phase）

```
输入：需求文档（PDF）+ 测试环境 URL
         ↓
  Phase 1：需求拆解
  - AI 读取 PDF，提取功能点、字段规则、交互逻辑
  - 输出：需求拆解&测试范围说明书.md
         ↓
  Phase 2：用例生成
  - 生成 8 类用例（正向/逆向/边界/DB/日志/防回归/探索式）
  - 覆盖多站点 × 多语言 × 多视口
  - 输出：测试用例.xlsx
         ↓
  Phase 3：自动回归
  - playwright-cli 逐条执行用例
  - 三层校验：UI 文本 / Kibana 日志 / DB 查询
  - 发现 Bug 立即截图，记录完整复现步骤
  - 输出：截图（BUG_XXX.png）
         ↓
  Phase 4：报告产出
  - 生成缺陷清单.xlsx
  - 生成 Web 测试总结报告.md
  - 推送飞书通知（含完整复现步骤）
```

---

## 核心模块详解

### 1. pdf_reader.py — 需求文档解析
- 使用 **PyMuPDF** 库解析 PDF
- 逐页提取文本，保存到 `case/PDFDocs/`
- AI Agent 读取文本后进行需求分析

### 2. test_case_writer.py — Excel 生成
- 用 **openpyxl** 生成格式化 Excel
- 测试用例表：蓝色表头，10 列（编号/标题/前置条件/步骤/预期结果/优先级等）
- 缺陷清单表：红色表头，9 列（缺陷ID/模块/等级/复现步骤/截图等）

### 3. bug_reporter.py — Bug 管理
- 内存中维护 Bug 列表（`_bugs: List[Dict]`）
- 支持按严重度筛选（P0/P1/P2/P3）
- 可导出为 Excel 格式或飞书格式
- 通过 `send_to_feishu()` 一键推送

### 4. feishu_notifier.py — 飞书通知
- 读取 `.env` 文件获取 Webhook 和签名密钥
- 支持：文本消息 / 富文本消息 / 测试汇总 / Bug 汇总 / 逐条发送
- P0 级 Bug 自动 @所有人

### 5. parallel_test_runner.py — 并行测试
- 用 `ThreadPoolExecutor` 并发启动多个 playwright-cli session
- 每个 session 独立打开浏览器，执行校验，截图
- 汇总所有 session 结果，生成 JSON 报告
- 典型场景：同时测试 Global/HK/CN 三个站点

### 6. feiShuRobot/distribute_bug.py — Bug 分发
- 读取 Bug JSON + YAML 路由规则
- 按 severity/module 路由到不同飞书群
- 支持 dry-run 模式验证路由规则
- 典型场景：P0 发紧急群，P2 发普通群

### 7. kb_search.py — 知识库搜索
- 4 种模式：文件名搜索 / 内容关键词搜索 / 读取文件 / 目录树
- 支持路径别名（简化长路径输入）
- 只处理文本文件（.md/.json/.java/.py 等），不支持 Word/PDF
- AI Agent 用它检索历史需求文档和测试经验

---

## 产出文件结构

```
case/
├── PDFDocs/          需求文档解析结果（.txt）
├── TestPoint/        需求拆解说明书（.md）
├── TestCase/         测试用例（.xlsx）
├── screenshots/      截图（BUG_001.png / homepage_global.png）
├── BugReport/        缺陷清单（.xlsx）+ bugs.json
├── TestReport/       测试总结报告（.md）
├── auth/             登录状态文件（.json）
└── TestExperience/   测试经验库（.md + index.json）
```

---

## 关键技术选型

| 技术 | 用途 | 选型理由 |
|------|------|----------|
| playwright-cli | 浏览器自动化 | 命令行驱动，AI Agent 可直接调用，无需写测试代码 |
| PyMuPDF | PDF 解析 | 速度快，支持中文，纯 Python |
| openpyxl | Excel 生成 | 支持样式定制，无需安装 Office |
| requests | 飞书通知 | 轻量，直接调用飞书 Webhook API |
| ThreadPoolExecutor | 并行测试 | Python 标准库，无额外依赖 |
| Kiro AI + Steering | 测试调度 | 用自然语言定义工作流，AI 自动执行 |

---

## 安全规范（重要）

**禁止在生产环境执行自动化测试！**

| 环境 | 域名特征 | 是否允许 |
|------|----------|----------|
| 测试环境 | `*-inc.com` | ✅ 允许 |
| 生产环境 | `*.lianlianpay.com`（不含 -inc） | ❌ 禁止 |

---

## 实际执行效果（以本次测试为例）

- **需求**：连连国际官网品牌迭代（Logo 替换 + 文字替换 + 数据口径更新）
- **用例数**：29 条（自动生成）
- **执行用例**：13 条 P0 用例
- **执行结果**：13/13 PASS，0 缺陷
- **覆盖范围**：Global + HK 两个站点，首页/公司页/B2B页/登录页
- **耗时**：约 3 分钟（含多站点跳转和截图）

---

## 面试常见问题参考答案

**Q：这个平台和传统 Selenium/Pytest 方案有什么区别？**

A：传统方案需要手写测试代码，维护成本高。这个平台的核心差异是：
1. **零代码**：测试用例由 AI 从需求文档自动生成，不需要手写
2. **自然语言驱动**：playwright-cli 用自然语言指令操作浏览器，AI 可以直接调用
3. **全流程自动化**：从需求解析到报告推送，全程无需人工介入

**Q：如何保证测试覆盖率？**

A：通过三个维度保证：
1. **多站点**：Global/HK/CN 三个站点都覆盖
2. **多语言**：中文和英文两套用例
3. **多视口**：PC（1920x1080）/ 平板（768x1024）/ 移动端（375x812）

**Q：发现 Bug 后如何处理？**

A：强制规范：
1. 发现即截图（`playwright-cli screenshot --filename=BUG_XXX.png`）
2. 记录完整复现步骤（环境 + URL + 操作步骤 + 预期/实际结果）
3. 写入缺陷清单 Excel
4. 通过飞书机器人推送通知（P0 自动 @所有人）

**Q：并行测试是怎么实现的？**

A：playwright-cli 支持 `-s=<session>` 参数创建独立浏览器会话，`parallel_test_runner.py` 用 Python 的 `ThreadPoolExecutor` 并发启动多个 session，每个 session 独立执行测试，最后汇总结果。

**Q：测试经验如何积累和复用？**

A：每次测试结束后，将新发现的测试点、常见问题、最佳实践写入 `case/TestExperience/` 目录（Markdown 格式），下次测试时 AI Agent 通过 `kb_search.py` 检索历史经验，自动补充到测试用例中。


---

## 🟢 #7: 对话记录

- **状态**: open
- **标签**: 无标签
- **创建时间**: 2026-04-20
- **链接**: [https://github.com/LittleParis/AgentTestingHelper/issues/7](https://github.com/LittleParis/AgentTestingHelper/issues/7)

### 描述

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


---

## 🟢 #6: OncallAgent学习路线

- **状态**: open
- **标签**: 无标签
- **创建时间**: 2026-04-20
- **链接**: [https://github.com/LittleParis/AgentTestingHelper/issues/6](https://github.com/LittleParis/AgentTestingHelper/issues/6)

### 描述

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


---

## 🟢 #5: OnCallAgent项目结构详解

- **状态**: open
- **标签**: 无标签
- **创建时间**: 2026-04-20
- **链接**: [https://github.com/LittleParis/AgentTestingHelper/issues/5](https://github.com/LittleParis/AgentTestingHelper/issues/5)

### 描述

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


---

## 🟢 #4: 前端设计方案

- **状态**: open
- **标签**: 无标签
- **创建时间**: 2026-04-20
- **链接**: [https://github.com/LittleParis/AgentTestingHelper/issues/4](https://github.com/LittleParis/AgentTestingHelper/issues/4)

### 描述

# 前端设计方案

> 基于当前后端数据结构（AgentState、Requirement、TestCase、ReviewResult）设计，与 Enhancement #3（REST API）配合使用。

---

## 一、整体架构

### 技术选型

| 层次 | 技术 | 理由 |
|------|------|------|
| 框架 | React 18 + TypeScript | 生态成熟，类型安全 |
| 构建 | Vite | 比 CRA 快 10 倍 |
| 状态管理 | Zustand | 比 Redux 轻量，适合中型应用 |
| UI 组件库 | Ant Design 5 | 企业级组件，表格/表单/步骤条开箱即用 |
| 路由 | React Router v6 | 标准选择 |
| 请求 | TanStack Query + Axios | 自动缓存、loading 状态、错误处理 |
| 实时通信 | EventSource（SSE） | 流式推送执行进度，比 WebSocket 简单 |
| 图表 | Recharts | 轻量，适合趋势图 |
| 代码高亮 | Monaco Editor | VS Code 同款，展示生成的 TS 脚本 |

### 目录结构

```
frontend/
├── src/
│   ├── pages/              # 页面组件
│   │   ├── Dashboard/      # 首页仪表盘
│   │   ├── NewTask/        # 新建任务（需求上传）
│   │   ├── TaskDetail/     # 任务详情（执行过程）
│   │   ├── TestCases/      # 测试用例管理
│   │   ├── Reports/        # 报告中心
│   │   └── Settings/       # 设置
│   ├── components/         # 通用组件
│   │   ├── WorkflowProgress/   # 工作流进度条
│   │   ├── RequirementCard/    # 需求卡片
│   │   ├── TestCaseTable/      # 测试用例表格
│   │   ├── ReviewPanel/        # 评审结果面板
│   │   └── ScriptViewer/       # 脚本代码查看器
│   ├── stores/             # Zustand 状态
│   │   ├── taskStore.ts
│   │   └── settingsStore.ts
│   ├── api/                # API 请求封装
│   │   ├── tasks.ts
│   │   ├── testCases.ts
│   │   └── reports.ts
│   └── types/              # TypeScript 类型（与后端 Pydantic 模型对应）
│       ├── requirement.ts
│       ├── testCase.ts
│       └── review.ts
├── package.json
└── vite.config.ts
```

---

## 二、页面设计

### 页面 1：首页仪表盘（Dashboard）

**路由**：`/`

**核心内容**：

```
┌─────────────────────────────────────────────────────────┐
│  AI 测试自动化平台                    [+ 新建任务]        │
├──────────┬──────────┬──────────┬──────────────────────── │
│  总任务   │  本周运行 │  平均通过率│  节省时间估算          │
│   42     │    8     │   76.3%  │   ~120h               │
├──────────┴──────────┴──────────┴──────────────────────── │
│                                                         │
│  最近任务                                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 任务名称        状态    用例数  通过率  时间        │   │
│  │ 登录功能需求    ✅完成   12     83%    10分钟前    │   │
│  │ 百度搜索需求    🔄执行中  8      -      刚刚       │   │
│  │ 购物车功能      ❌失败    15     40%    1小时前    │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  通过率趋势（最近 7 天）                                  │
│  [折线图]                                               │
└─────────────────────────────────────────────────────────┘
```

**关键交互**：
- 点击"新建任务"跳转到新建页
- 点击任务行跳转到任务详情
- 仪表盘数据每 30 秒自动刷新

---

### 页面 2：新建任务（NewTask）

**路由**：`/tasks/new`

**核心内容**：

```
┌─────────────────────────────────────────────────────────┐
│  新建测试任务                                            │
│                                                         │
│  步骤 1/3：上传需求文档                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │                                                  │   │
│  │   📄 拖拽文件到此处，或点击选择                    │   │
│  │   支持：.md  .pdf  .docx  .txt                   │   │
│  │                                                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  或者直接粘贴需求文本：                                   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ # 用户登录功能                                    │   │
│  │ ...                                              │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  目标页面 URL：                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ https://example.com/login                        │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  高级选项 ▼                                              │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 最大迭代次数：[2]   评审通过阈值：[60]分            │   │
│  │ 执行模式：● 有头  ○ 无头                           │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│                              [取消]  [开始分析 →]        │
└─────────────────────────────────────────────────────────┘
```

**关键交互**：
- 文件拖拽上传，支持预览
- 文本框实时字数统计
- URL 格式校验
- 点击"开始分析"后跳转到任务详情页，并开始 SSE 监听

---

### 页面 3：任务详情（TaskDetail）— 核心页面

**路由**：`/tasks/:taskId`

这是整个前端最重要的页面，展示工作流的实时执行过程。

**布局设计**：

```
┌─────────────────────────────────────────────────────────┐
│  ← 返回   登录功能需求测试   🔄 执行中   [停止] [重新运行] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  工作流进度                                              │
│  ●─────●─────●─────◌─────◌─────◌                       │
│  需求   用例   评审   脚本   执行   报告                   │
│  分析   生成   ✅通过  生成   中...                        │
│                                                         │
├──────────────────────┬──────────────────────────────────┤
│                      │                                  │
│  左侧：步骤详情        │  右侧：实时日志                   │
│                      │                                  │
│  [需求分析] ✅         │  [10:23:01] 需求分析中...        │
│  ┌────────────────┐  │  [10:23:05] 识别到 3 个需求       │
│  │ REQ_001 高     │  │  [10:23:05] 开始生成测试用例...   │
│  │ 用户登录       │  │  [10:23:12] REQ_001: 生成 4 个   │
│  │ REQ_002 中     │  │  [10:23:18] REQ_002: 生成 3 个   │
│  │ 忘记密码       │  │  [10:23:24] 开始评审...           │
│  └────────────────┘  │  [10:23:31] 评审通过 82/100 ✅   │
│                      │  [10:23:31] 开始生成脚本...       │
│  [用例生成] ✅         │  [10:23:35] 脚本已生成           │
│  ┌────────────────┐  │  [10:23:35] 开始执行测试...       │
│  │ TC_001 高 ✅   │  │  ▌                               │
│  │ 正常登录       │  │                                  │
│  │ TC_002 中 ✅   │  │                                  │
│  │ 密码错误       │  │                                  │
│  │ TC_003 低 🔄   │  │                                  │
│  └────────────────┘  │                                  │
│                      │                                  │
│  [评审结果] ✅ 82分    │                                  │
│  ┌────────────────┐  │                                  │
│  │ 完整性  18/20  │  │                                  │
│  │ 覆盖率  16/20  │  │                                  │
│  │ 合理性  17/20  │  │                                  │
│  │ 独立性  15/20  │  │                                  │
│  │ 清晰度  16/20  │  │                                  │
│  └────────────────┘  │                                  │
│                      │                                  │
└──────────────────────┴──────────────────────────────────┘
```

**关键交互**：
- SSE 实时推送，日志自动滚动到底部
- 工作流进度条动态更新
- 左侧点击需求/用例可展开详情
- 评审维度用雷达图展示
- 执行完成后底部出现"查看报告"按钮

---

### 页面 4：测试用例管理（TestCases）

**路由**：`/tasks/:taskId/cases`

```
┌─────────────────────────────────────────────────────────┐
│  测试用例  共 12 个   [导出 Excel] [导出 JSON]            │
│                                                         │
│  筛选：[全部 ▼] [优先级 ▼] [类型 ▼]  🔍 搜索用例标题      │
│                                                         │
│  ┌──┬────────┬──────────────┬────┬──────┬──────┬──────┐ │
│  │  │ ID     │ 标题         │优先│ 类型 │ 状态 │ 操作 │ │
│  ├──┼────────┼──────────────┼────┼──────┼──────┼──────┤ │
│  │▶ │TC_001  │ 正常登录流程  │ 高 │ UI   │ ✅通过│ 编辑 │ │
│  │▶ │TC_002  │ 密码错误提示  │ 中 │ UI   │ ✅通过│ 编辑 │ │
│  │▶ │TC_003  │ 空字段校验    │ 中 │ UI   │ ❌失败│ 编辑 │ │
│  │▶ │TC_004  │ 忘记密码链接  │ 低 │ UI   │ ⏭跳过│ 编辑 │ │
│  └──┴────────┴──────────────┴────┴──────┴──────┴──────┘ │
│                                                         │
│  展开 TC_001：                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 前置条件：用户已注册账号                            │   │
│  │                                                  │   │
│  │ 步骤：                                            │   │
│  │  1. 打开登录页面          → 页面正常加载            │   │
│  │  2. 输入邮箱 test@xx.com  → 输入框显示内容          │   │
│  │  3. 输入密码 ******       → 密码掩码显示            │   │
│  │  4. 点击登录按钮          → 跳转到首页              │   │
│  │                                                  │   │
│  │ 预期结果：登录成功，右上角显示用户邮箱               │   │
│  │                                                  │   │
│  │ 执行截图：[截图1] [截图2] [截图3]                  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**关键交互**：
- 行展开查看步骤详情和执行截图
- 点击"编辑"可以修改用例（修改记录会被记录用于反馈闭环）
- 支持批量操作（批量删除、批量重跑）
- 导出功能

---

### 页面 5：脚本查看器（ScriptViewer）

**路由**：`/tasks/:taskId/script`

```
┌─────────────────────────────────────────────────────────┐
│  生成的测试脚本   [下载] [复制] [在 VS Code 中打开]        │
│                                                         │
│  auto_generated_20260420_103500.spec.ts                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │  1  import { test as base } from '@playwright/test'│  │
│  │  2  import { PlaywrightAiFixture } from '@midscene'│  │
│  │  3                                               │   │
│  │  4  const test = base.extend(PlaywrightAiFixture())│  │
│  │  5                                               │   │
│  │  6  test.describe('自动生成的测试用例', () => {    │   │
│  │  7    test('TC_001: 正常登录流程', async ({       │   │
│  │  8      page, ai                                 │   │
│  │  9    }) => {                                    │   │
│  │ 10      await page.goto('https://example.com')   │   │
│  │ 11      await ai('在邮箱输入框输入 "test@xx.com"') │   │
│  │ 12      ...                                      │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  执行命令：                                              │
│  ┌──────────────────────────────────────────────────┐   │
│  │ npx playwright test midscene_run/generated/...   │   │
│  │                                          [复制]  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

### 页面 6：报告中心（Reports）

**路由**：`/tasks/:taskId/report`

```
┌─────────────────────────────────────────────────────────┐
│  测试报告   登录功能需求   2026-04-20 10:35              │
│                                                         │
│  ┌──────┬──────┬──────┬──────┐                          │
│  │ 总数  │ 通过 │ 失败 │ 跳过 │                          │
│  │  12  │  9   │  2   │  1   │  通过率 75%              │
│  └──────┴──────┴──────┴──────┘                          │
│                                                         │
│  ┌──────────────────────┬──────────────────────────┐    │
│  │  按优先级分布         │  执行时间分布             │    │
│  │  [饼图]              │  [柱状图]                 │    │
│  └──────────────────────┴──────────────────────────┘    │
│                                                         │
│  失败用例详情                                            │
│  ┌──────────────────────────────────────────────────┐   │
│  │ TC_003 空字段校验  ❌                              │   │
│  │ 错误：Expected element to be visible              │   │
│  │ 截图：[查看截图]                                   │   │
│  │ AI 分析：选择器可能失效，建议检查错误提示元素的定位  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  [查看完整 Allure 报告 ↗]                               │
└─────────────────────────────────────────────────────────┘
```

---

## 三、核心组件设计

### WorkflowProgress 组件

对应后端 `AgentState.current_step`，实时展示工作流进度：

```tsx
// components/WorkflowProgress/index.tsx

type Step = {
  key: string           // 对应 AgentState.current_step
  label: string
  status: 'wait' | 'process' | 'finish' | 'error'
  detail?: string       // 如 "识别到 3 个需求"
}

const WORKFLOW_STEPS: Step[] = [
  { key: 'requirement_analyzed', label: '需求分析' },
  { key: 'test_cases_generated', label: '用例生成' },
  { key: 'reviewed',             label: '用例评审' },
  { key: 'script_generated',     label: '脚本生成' },
  { key: 'tests_executed',       label: '测试执行' },
  { key: 'report_generated',     label: '报告生成' },
]

// SSE 事件驱动更新
function WorkflowProgress({ taskId }: { taskId: string }) {
  const [steps, setSteps] = useState(WORKFLOW_STEPS)

  useEffect(() => {
    const es = new EventSource(`/api/tasks/${taskId}/stream`)
    es.onmessage = (e) => {
      const event = JSON.parse(e.data)
      // 根据 current_step 更新进度
      updateStepStatus(event.current_step, event.status)
    }
    return () => es.close()
  }, [taskId])

  return <Steps items={steps} />
}
```

### ReviewRadarChart 组件

对应后端 `ReviewDimensions`，展示五维度评分：

```tsx
// components/ReviewRadarChart/index.tsx

// 后端数据结构
type ReviewDimensions = {
  completeness: number   // 0-20
  coverage: number
  reasonability: number
  independence: number
  clarity: number
}

function ReviewRadarChart({ dimensions }: { dimensions: ReviewDimensions }) {
  const data = [
    { subject: '完整性', score: dimensions.completeness, fullMark: 20 },
    { subject: '覆盖率', score: dimensions.coverage,     fullMark: 20 },
    { subject: '合理性', score: dimensions.reasonability, fullMark: 20 },
    { subject: '独立性', score: dimensions.independence,  fullMark: 20 },
    { subject: '清晰度', score: dimensions.clarity,       fullMark: 20 },
  ]

  return (
    <RadarChart data={data}>
      <Radar dataKey="score" fill="#1677ff" fillOpacity={0.3} />
    </RadarChart>
  )
}
```

---

## 四、与后端的数据对接

### TypeScript 类型定义（与 Pydantic 模型对应）

```typescript
// types/requirement.ts
export interface Requirement {
  id: string                    // REQ_001
  title: string
  description: string
  priority: 'high' | 'medium' | 'low'
  type: 'functional' | 'non_functional' | 'business' | 'technical'
  acceptance_criteria: string[]
  ui_elements: string[]
}

// types/testCase.ts
export interface TestStep {
  step_number: number
  action: string
  data?: string
  expected: string
}

export interface TestCase {
  id: string                    // TC_001
  requirement_id: string        // REQ_001
  title: string
  priority: 'high' | 'medium' | 'low'
  type: 'functional' | 'ui' | 'api' | 'integration' | 'performance' | 'security'
  steps: TestStep[]
  expected: string
  tags: string[]
  // 执行结果（后端扩展）
  execution_status?: 'passed' | 'failed' | 'skipped' | 'pending'
  execution_duration?: number
  failure_screenshot?: string
}

// types/review.ts
export interface ReviewDimensions {
  completeness: number
  coverage: number
  reasonability: number
  independence: number
  clarity: number
}

export interface ReviewResult {
  passed: boolean
  score: number
  dimensions?: ReviewDimensions
  comments: ReviewComment[]
  suggestions: string[]
}

// types/task.ts（前端扩展，对应 AgentState）
export interface Task {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  current_step: string
  created_at: string
  // 结果
  requirements?: Requirement[]
  test_cases?: TestCase[]
  review_result?: ReviewResult
  execution_results?: ExecutionResult
  allure_report_url?: string
}
```

### API 请求封装

```typescript
// api/tasks.ts
import { useQuery, useMutation } from '@tanstack/react-query'

// 创建任务
export function useCreateTask() {
  return useMutation({
    mutationFn: async (formData: FormData) => {
      const res = await axios.post('/api/tasks', formData)
      return res.data as { task_id: string }
    }
  })
}

// 获取任务详情
export function useTask(taskId: string) {
  return useQuery({
    queryKey: ['task', taskId],
    queryFn: () => axios.get(`/api/tasks/${taskId}`).then(r => r.data as Task),
    refetchInterval: (data) =>
      data?.status === 'running' ? 2000 : false  // 运行中每 2 秒刷新
  })
}

// SSE 实时进度
export function useTaskStream(taskId: string, onEvent: (event: StreamEvent) => void) {
  useEffect(() => {
    const es = new EventSource(`/api/tasks/${taskId}/stream`)
    es.onmessage = (e) => onEvent(JSON.parse(e.data))
    es.onerror = () => es.close()
    return () => es.close()
  }, [taskId])
}
```

---

## 五、关键 UX 设计原则

**1. 进度可见性**
工作流每个节点的状态必须实时可见，用户不能盯着空白屏等待。SSE 推送是核心。

**2. 失败可追溯**
任何节点失败都要展示：失败原因 + 原始错误 + 建议操作（重试/跳过/修改参数）。

**3. 结果可编辑**
生成的测试用例要支持在线编辑，编辑记录用于反馈闭环（Enhancement #6）。

**4. 渐进式展示**
不要等全部完成才展示结果。需求分析完就展示需求，用例生成完就展示用例，不等执行完。

**5. 移动端降级**
主要功能在桌面端，移动端只需要支持查看报告和任务状态，不需要支持创建任务。

---

## 六、开发顺序建议

```
阶段 1（MVP）：
  - 新建任务页（文件上传 + URL 输入）
  - 任务详情页（工作流进度 + 实时日志）
  - 测试用例列表（只读）

阶段 2（完善）：
  - 首页仪表盘
  - 测试用例编辑
  - 报告页面（内嵌 Allure）

阶段 3（增强）：
  - 趋势图表
  - 知识库管理
  - 多项目切换
```

先做阶段 1，后端只需要实现 3 个接口：
- `POST /api/tasks` — 创建任务
- `GET /api/tasks/:id` — 获取状态
- `GET /api/tasks/:id/stream` — SSE 进度推送


---

## 🟢 #3: 可以增加的亮点

- **状态**: open
- **标签**: 无标签
- **创建时间**: 2026-04-20
- **链接**: [https://github.com/LittleParis/AgentTestingHelper/issues/3](https://github.com/LittleParis/AgentTestingHelper/issues/3)

### 描述

# 功能增强路线图

> 在修复所有已知 Bug（见 agent_optimization_issues.md）之后，这些是让平台从"能跑"变成"真正有价值"的改进方向。
> 按投入产出比排序，分三个批次推进。

---

## 第一批：核心价值提升（优先推进）

---

### Enhancement 1：测试失败智能分析 Agent

**价值**：这是 AI 测试平台最核心的差异化能力，普通测试框架做不到。

#### 问题描述

现在测试失败后只记录错误日志，工程师需要手动分析：
- 是选择器失效？页面结构变了？
- 是断言逻辑错误？预期结果写错了？
- 是网络超时？环境问题？
- 是真实 Bug？还是测试脚本本身的问题？

#### 设计方案

新增 `FailureAnalysisAgent`，在 `execute_tests_node` 之后、`generate_report_node` 之前插入：

```python
# core/agents/failure_analyzer.py

class FailureAnalysisAgent:
    """测试失败智能分析 Agent"""

    def analyze(self, failure_info: FailureInfo) -> FailureAnalysisResult:
        """
        输入：失败截图 + 错误信息 + 测试步骤
        输出：失败原因分类 + 修复建议 + 是否为真实 Bug
        """

    def classify_failure(self, error: str) -> FailureType:
        """
        分类失败原因：
        - SELECTOR_INVALID: 选择器失效
        - ASSERTION_ERROR: 断言逻辑错误
        - TIMEOUT: 超时
        - NETWORK_ERROR: 网络问题
        - REAL_BUG: 真实 Bug
        - ENVIRONMENT_ISSUE: 环境问题
        """

    def suggest_fix(self, failure: FailureInfo) -> List[str]:
        """给出具体的修复建议"""

    def auto_retry_with_fix(self, test_case, fix_suggestion) -> ExecutionResult:
        """尝试自动修复并重跑"""
```

**LangGraph 工作流扩展：**
```
execute_tests → analyze_failures → [有真实Bug?] → 标记Bug报告
                                 → [脚本问题?]  → 自动修复重跑
                                 → generate_report
```

**Allure 报告增强：**
- 失败用例附带 AI 分析结论
- 区分"脚本问题"和"真实 Bug"的统计
- 修复建议直接展示在报告中

#### 涉及文件

- `core/agents/failure_analyzer.py` — 新建
- `core/models/failure.py` — 新建（FailureInfo、FailureAnalysisResult 模型）
- `core/agents/workflow.py` — 新增节点

---

### Enhancement 2：测试策略 Agent（Strategy Agent）

**价值**：避免生成几百个低价值用例，让测试更聚焦。

#### 问题描述

现在的流程是：需求 → 直接生成用例。没有人决定：
- 这个需求应该用 E2E 测试还是 API 测试？
- 应该生成多少个用例？
- 哪些场景是高风险必须覆盖的？
- 哪些场景可以跳过？

结果是生成了大量同质化用例，真正重要的场景反而可能被稀释。

#### 设计方案

在需求分析之后、用例生成之前，插入策略制定节点：

```python
# core/agents/strategy_planner.py

class TestStrategyPlanner:
    """测试策略规划 Agent"""

    def plan(self, requirements: List[Requirement]) -> TestStrategy:
        """
        输入：需求列表
        输出：测试策略
        """

class TestStrategy(BaseModel):
    """测试策略"""
    # 每个需求的测试重点
    requirement_strategies: List[RequirementStrategy]
    # 总用例数量上限
    max_test_cases: int = 20
    # 必须覆盖的场景类型
    required_coverage: List[str]  # ["happy_path", "error_handling", "boundary"]
    # 测试类型分配
    test_type_distribution: Dict[str, int]  # {"e2e": 5, "api": 3, "unit": 2}
    # 风险评估
    high_risk_areas: List[str]

class RequirementStrategy(BaseModel):
    requirement_id: str
    risk_level: str          # high/medium/low
    test_depth: str          # deep/normal/shallow
    focus_areas: List[str]   # 重点测试的方面
    skip_areas: List[str]    # 可以跳过的方面
    max_cases: int           # 该需求最多生成几个用例
```

**工作流变化：**
```
analyze_requirements → plan_strategy → generate_test_cases（带策略约束）
```

#### 涉及文件

- `core/agents/strategy_planner.py` — 新建
- `core/models/strategy.py` — 新建
- `core/agents/workflow.py` — 新增节点
- `core/agents/test_case_generator.py` — 接受策略参数

---

### Enhancement 3：REST API 接口层

**价值**：让平台可以被其他系统集成，不再只能命令行运行。

#### 设计方案

使用 FastAPI 封装核心流程：

```python
# api/main.py

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse

app = FastAPI(title="AI 测试自动化平台 API")

@app.post("/analyze")
async def analyze_requirement(
    file: UploadFile,
    page_url: str,
    background_tasks: BackgroundTasks
) -> AnalyzeResponse:
    """上传需求文档，启动分析流程"""
    task_id = create_task()
    background_tasks.add_task(run_workflow_async, task_id, file, page_url)
    return {"task_id": task_id, "status": "running"}

@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str) -> TaskStatus:
    """查询任务状态"""

@app.get("/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """SSE 实时推送执行进度"""
    return StreamingResponse(
        generate_progress_events(task_id),
        media_type="text/event-stream"
    )

@app.get("/tasks/{task_id}/report")
async def get_report(task_id: str):
    """获取 Allure 报告"""

@app.get("/tasks/{task_id}/test-cases")
async def get_test_cases(task_id: str) -> List[TestCase]:
    """获取生成的测试用例"""
```

**新增依赖：**
```
fastapi>=0.115.0
uvicorn>=0.32.0
python-multipart>=0.0.12  # 文件上传
```

#### 涉及文件

- `api/main.py` — 新建
- `api/routers/` — 新建路由模块
- `api/models/` — 新建请求/响应模型
- `requirements.txt` — 新增依赖

---

## 第二批：智能化增强

---

### Enhancement 4：知识库与历史用例复用

**价值**：减少重复 LLM 调用，让生成质量随时间持续提升。

#### 问题描述

每次运行都从零开始生成，没有利用历史数据：
- 相同类型的需求（登录、搜索、表单）每次都重新生成
- 历史中质量高的用例无法复用
- 无法从历史失败中学习

#### 设计方案

引入向量数据库存储历史用例：

```python
# core/knowledge/case_library.py

class TestCaseLibrary:
    """测试用例知识库"""

    def __init__(self, db_path: str = "knowledge.db"):
        self.vector_store = ChromaDB(db_path)  # 或 FAISS

    def search_similar(
        self,
        requirement: Requirement,
        top_k: int = 5
    ) -> List[SimilarCase]:
        """
        语义搜索相似历史用例
        返回相似度 > 0.8 的历史用例
        """

    def save(self, requirement: Requirement, test_cases: List[TestCase], quality_score: float):
        """保存高质量用例到知识库"""

    def get_statistics(self) -> LibraryStats:
        """知识库统计：总用例数、覆盖的需求类型、平均质量分"""
```

**在 TestCaseGenerator 中集成：**
```python
def generate_structured(self, requirement: Requirement) -> TestCaseGenerationResult:
    # 1. 先搜索知识库
    similar_cases = self.library.search_similar(requirement)

    if similar_cases and similar_cases[0].similarity > 0.9:
        # 高度相似，直接复用并微调
        return self._adapt_cases(similar_cases, requirement)

    # 2. 没有相似用例，调用 LLM 生成
    result = self._generate_with_llm(requirement)

    # 3. 保存到知识库（评审通过后）
    if result.quality_score > 70:
        self.library.save(requirement, result.test_cases, result.quality_score)

    return result
```

**新增依赖：**
```
chromadb>=0.5.0       # 向量数据库
sentence-transformers>=3.0.0  # 文本向量化
```

#### 涉及文件

- `core/knowledge/case_library.py` — 新建
- `core/knowledge/embeddings.py` — 新建（向量化工具）
- `core/agents/test_case_generator.py` — 集成知识库

---

### Enhancement 5：多模态输入支持（截图/原型图）

**价值**：让平台能直接分析 UI 截图生成测试用例，无需文字需求文档。

#### 设计方案

扩展 `DocumentParser` 支持图片输入：

```python
# core/parsers/image_parser.py

class UIScreenshotParser:
    """UI 截图解析器"""

    def __init__(self, vision_llm):
        self.llm = vision_llm  # 需要支持视觉的模型（GPT-4V、Qwen-VL）

    def parse(self, image_path: str) -> UIAnalysisResult:
        """
        输入：UI 截图
        输出：
        - 页面功能描述
        - 识别到的 UI 元素（输入框、按钮、链接等）
        - 推断的业务流程
        - 自动生成的需求描述
        """

    def extract_interactive_elements(self, image_path: str) -> List[UIElement]:
        """提取可交互元素，直接用于生成测试步骤"""

class UIElement(BaseModel):
    element_type: str      # input/button/link/dropdown
    label: str             # "用户名"、"登录按钮"
    position: tuple        # 在截图中的位置
    suggested_selector: str  # 推荐的 CSS 选择器
```

**工作流扩展：**
```python
# main_v2.py 支持图片输入
final_state = run_workflow(
    input_type="screenshot",
    input_path="screenshots/login_page.png",
    page_url="https://example.com/login"
)
```

#### 涉及文件

- `core/parsers/image_parser.py` — 新建
- `core/parsers/document_parser.py` — 新建（统一入口）
- `main_v2.py` — 支持多种输入类型

---

### Enhancement 6：测试用例质量反馈闭环

**价值**：让平台随使用时间持续变好，而不是每次都一样。

#### 设计方案

收集三类反馈信号：

```python
# core/feedback/collector.py

class FeedbackCollector:
    """质量反馈收集器"""

    def record_human_edit(
        self,
        original_case: TestCase,
        edited_case: TestCase,
        editor: str
    ):
        """记录人工修改：哪里被改了，改成了什么"""

    def record_bug_found(
        self,
        test_case: TestCase,
        bug_description: str,
        severity: str
    ):
        """记录用例发现了真实 Bug（高价值信号）"""

    def record_false_positive(
        self,
        test_case: TestCase,
        reason: str
    ):
        """记录误报（用例失败但不是真实 Bug）"""

# core/feedback/prompt_optimizer.py

class PromptOptimizer:
    """基于反馈优化 Prompt"""

    def analyze_feedback(self, feedback_history: List[Feedback]) -> PromptSuggestions:
        """
        分析反馈模式：
        - 哪类需求的用例质量差？
        - 哪些步骤描述经常被修改？
        - 哪些断言逻辑经常出错？
        """

    def generate_improved_prompt(
        self,
        base_prompt: str,
        feedback_patterns: PromptSuggestions
    ) -> str:
        """生成改进后的 Prompt"""
```

#### 涉及文件

- `core/feedback/collector.py` — 新建
- `core/feedback/prompt_optimizer.py` — 新建
- `core/models/feedback.py` — 新建

---

### Enhancement 7：跨需求依赖分析与端到端场景生成

**价值**：生成真实业务流程的端到端测试，而不只是单功能测试。

#### 问题描述

现在每个需求独立生成用例，但真实业务有依赖：
- 购物车测试依赖登录
- 下单测试依赖购物车
- 支付测试依赖下单

这些依赖关系没有被识别，导致：
- 缺少端到端场景用例
- 用例执行顺序没有考虑依赖
- 测试数据准备不完整

#### 设计方案

```python
# core/agents/dependency_analyzer.py

class DependencyAnalyzer:
    """需求依赖分析 Agent"""

    def analyze_dependencies(
        self,
        requirements: List[Requirement]
    ) -> DependencyGraph:
        """
        分析需求间的依赖关系
        返回有向无环图（DAG）
        """

    def generate_e2e_scenarios(
        self,
        dependency_graph: DependencyGraph
    ) -> List[E2EScenario]:
        """
        基于依赖图生成端到端场景
        例如：登录 → 添加购物车 → 下单 → 支付
        """

class E2EScenario(BaseModel):
    name: str
    description: str
    requirements_chain: List[str]  # 涉及的需求 ID 链
    test_steps: List[TestStep]     # 跨需求的完整步骤
    test_data: Dict[str, Any]      # 所需测试数据
```

#### 涉及文件

- `core/agents/dependency_analyzer.py` — 新建
- `core/models/scenario.py` — 新建
- `core/agents/workflow.py` — 新增节点

---

## 第三批：工程化与生态

---

### Enhancement 8：插件化 Agent 架构

**价值**：让用户可以自定义 Agent，扩展平台能力。

#### 设计方案

```python
# core/plugins/registry.py

class AgentRegistry:
    """Agent 插件注册表"""

    _agents: Dict[str, Type[BaseAgent]] = {}

    @classmethod
    def register(cls, name: str, agent_class: Type[BaseAgent]):
        """注册自定义 Agent"""
        cls._agents[name] = agent_class

    @classmethod
    def get(cls, name: str) -> Type[BaseAgent]:
        return cls._agents[name]

# 内置 Agent 自动注册
AgentRegistry.register("requirement_analyzer", RequirementAnalyzer)
AgentRegistry.register("test_generator", TestCaseGenerator)
AgentRegistry.register("case_reviewer", CaseReviewer)

# 用户自定义 Agent
class MySecurityReviewer(BaseAgent):
    """自定义安全测试评审 Agent"""
    def review(self, test_cases):
        # 检查是否包含 SQL 注入、XSS 等安全测试
        ...

AgentRegistry.register("security_reviewer", MySecurityReviewer)
```

**配置驱动的工作流：**
```yaml
# workflow_config.yaml
workflow:
  nodes:
    - name: analyze_requirements
      agent: requirement_analyzer
    - name: generate_test_cases
      agent: test_generator
    - name: review_cases
      agent: case_reviewer
    - name: security_review        # 自定义节点
      agent: security_reviewer
      condition: "requirement.type == 'security'"
```

#### 涉及文件

- `core/plugins/registry.py` — 新建
- `core/plugins/base_agent.py` — 新建（BaseAgent 抽象类）
- `core/agents/workflow.py` — 支持动态构建

---

### Enhancement 9：增量执行（只跑变更影响的用例）

**价值**：大型项目全量执行耗时长，增量执行可以大幅提速。

#### 设计方案

```python
# core/execution/impact_analyzer.py

class ImpactAnalyzer:
    """变更影响分析器"""

    def analyze_git_diff(self, diff: str) -> List[str]:
        """
        分析 Git diff，返回受影响的功能模块
        """

    def find_affected_test_cases(
        self,
        affected_modules: List[str],
        all_test_cases: List[TestCase]
    ) -> List[TestCase]:
        """
        找出需要重新执行的测试用例
        基于：需求标签、功能模块映射
        """

    def prioritize(self, test_cases: List[TestCase]) -> List[TestCase]:
        """
        按风险优先级排序：
        1. 上次失败的用例
        2. 覆盖变更模块的用例
        3. 高优先级用例
        4. 其余用例
        """
```

**命令行支持：**
```bash
# 只跑受影响的用例
python main_v2.py --incremental --since HEAD~1

# 只跑上次失败的用例
python main_v2.py --rerun-failed
```

#### 涉及文件

- `core/execution/impact_analyzer.py` — 新建
- `main_v2.py` — 支持增量模式

---

### Enhancement 10：与 CI/CD 深度集成

**价值**：让平台成为开发流程的一部分，而不是独立工具。

#### 设计方案

**GitHub Actions 集成：**
```yaml
# .github/workflows/ai-test.yml
name: AI Test Generation

on:
  pull_request:
    paths:
      - 'docs/requirements/**'  # 需求文档变更时触发

jobs:
  generate-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Analyze requirement changes
        run: python main_v2.py --requirement ${{ env.CHANGED_FILE }}

      - name: Comment test cases on PR
        uses: actions/github-script@v7
        with:
          script: |
            const testCases = require('./output/test_cases.json')
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              body: formatTestCases(testCases)
            })
```

**Webhook 支持：**
```python
# api/webhooks.py

@app.post("/webhooks/github")
async def github_webhook(payload: GitHubWebhookPayload):
    """接收 GitHub PR 事件，自动触发测试生成"""
    if payload.event == "pull_request" and payload.action == "opened":
        changed_files = get_changed_requirement_files(payload)
        for file in changed_files:
            await trigger_analysis(file, payload.pr_url)
```

#### 涉及文件

- `.github/workflows/ai-test.yml` — 新建
- `api/webhooks.py` — 新建

---

### Enhancement 11：多项目管理与工作空间

**价值**：支持团队多项目并行使用。

#### 设计方案

```python
# core/workspace/project_manager.py

class ProjectManager:
    """多项目管理器"""

    def create_project(self, name: str, config: ProjectConfig) -> Project:
        """创建新项目"""

    def switch_project(self, project_id: str):
        """切换当前项目"""

    def list_projects(self) -> List[ProjectSummary]:
        """列出所有项目及其状态"""

class Project(BaseModel):
    id: str
    name: str
    config: ProjectConfig
    created_at: datetime
    last_run: Optional[datetime]
    statistics: ProjectStats

class ProjectStats(BaseModel):
    total_requirements: int
    total_test_cases: int
    pass_rate: float
    last_run_duration: float
```

**命令行支持：**
```bash
python main_v2.py project create --name "电商平台" --url "https://shop.example.com"
python main_v2.py project list
python main_v2.py project use "电商平台"
python main_v2.py run --requirement docs/cart.md
```

#### 涉及文件

- `core/workspace/project_manager.py` — 新建
- `core/models/project.py` — 新建
- `main_v2.py` — 支持项目命令

---

### Enhancement 12：测试报告增强（趋势分析）

**价值**：让报告不只是"这次跑了什么"，而是"质量在变好还是变差"。

#### 设计方案

在 Allure 报告基础上增加趋势数据：

```python
# core/reporting/trend_analyzer.py

class TrendAnalyzer:
    """测试趋势分析器"""

    def analyze_trend(self, history: List[ExecutionResult]) -> TrendReport:
        """
        分析多次执行的趋势：
        - 通过率变化曲线
        - 新增/修复/回归的用例
        - 执行时间趋势
        - 最不稳定的用例（flaky tests）
        """

    def detect_flaky_tests(
        self,
        history: List[ExecutionResult],
        threshold: float = 0.3
    ) -> List[FlakyTest]:
        """
        检测不稳定用例（时而通过时而失败）
        threshold: 失败率阈值
        """

    def generate_quality_score(self, trend: TrendReport) -> float:
        """
        综合质量评分（0-100）：
        - 通过率权重 40%
        - 趋势方向权重 30%
        - 稳定性权重 30%
        """
```

**报告增强内容：**
- 历史通过率折线图
- Flaky Test 列表（需要关注的不稳定用例）
- 本次新增失败 vs 历史遗留失败
- 质量评分趋势

#### 涉及文件

- `core/reporting/trend_analyzer.py` — 新建
- `core/reporting/history_store.py` — 新建（历史数据存储）
- `core/automation/allure_reporter.py` — 集成趋势数据

---

## 优先级汇总

| Enhancement | 标题 | 投入 | 产出 | 批次 |
|-------------|------|------|------|------|
| #1 | 测试失败智能分析 Agent | 中 | ⭐⭐⭐⭐⭐ | 第一批 |
| #2 | 测试策略 Agent | 中 | ⭐⭐⭐⭐ | 第一批 |
| #3 | REST API 接口层 | 中 | ⭐⭐⭐⭐ | 第一批 |
| #4 | 知识库与历史用例复用 | 中 | ⭐⭐⭐⭐ | 第二批 |
| #5 | 多模态输入（截图/原型图） | 高 | ⭐⭐⭐⭐⭐ | 第二批 |
| #6 | 质量反馈闭环 | 中 | ⭐⭐⭐⭐ | 第二批 |
| #7 | 跨需求依赖分析 | 高 | ⭐⭐⭐⭐ | 第二批 |
| #8 | 插件化 Agent 架构 | 高 | ⭐⭐⭐ | 第三批 |
| #9 | 增量执行 | 中 | ⭐⭐⭐ | 第三批 |
| #10 | CI/CD 深度集成 | 中 | ⭐⭐⭐⭐ | 第三批 |
| #11 | 多项目管理 | 中 | ⭐⭐⭐ | 第三批 |
| #12 | 报告趋势分析 | 低 | ⭐⭐⭐⭐ | 第三批 |

---

## 核心思路

修完 Bug 是让平台**能跑**，这 12 个增强是让平台**真正有价值**。

最关键的三个方向：

1. **#1 失败分析** — AI 测试平台的核心差异化，普通框架做不到
2. **#4 知识库** — 让平台越用越好，形成竞争壁垒
3. **#5 多模态输入** — 降低使用门槛，不需要写需求文档也能用

建议路径：`修 Bug → 第一批（API + 策略 + 失败分析）→ 第二批（知识库 + 多模态）→ 第三批（生态建设）`


---

## 🟢 #2: bug修复

- **状态**: open
- **标签**: 无标签
- **创建时间**: 2026-04-20
- **链接**: [https://github.com/LittleParis/AgentTestingHelper/issues/2](https://github.com/LittleParis/AgentTestingHelper/issues/2)

### 描述

# Agent 优化 Issues

> 基于当前代码分析，整理以下优化方向，按优先级排序。

---

## Issue 1：用结构化输出替换手动 JSON 解析

**标签**: `enhancement` `tech-debt` `priority-high`

### 问题描述

当前每个 Agent（`RequirementAnalyzer`、`TestCaseGenerator`、`CaseReviewer`）都有大量手动解析 LLM 输出的代码：

- `_extract_json()` — 从 markdown 代码块中提取 JSON
- `_fix_json_format()` — 修复格式问题
- `_fallback_parse()` — 降级解析方案

这些代码脆弱、重复，且难以维护。

### 优化方案

使用 LangChain 的 `with_structured_output` 直接绑定 Pydantic 模型，让框架处理解析：

```python
# 当前写法（脆弱）
content = self.llm.chat_simple(prompt)
json_data = self._extract_json(content)   # 各种修复逻辑
result = self._parse_llm_response(json_data)

# 优化后（稳定）
from langchain_core.language_models import BaseChatModel
llm_with_schema = llm.with_structured_output(RequirementAnalysisResult)
result = llm_with_schema.invoke(prompt)   # 直接返回 Pydantic 对象
```

### 预期收益

- 消除约 150 行重复的 JSON 解析代码
- 解析失败率大幅降低
- 代码可读性显著提升

### 涉及文件

- `core/agents/requirement_analyzer.py`
- `core/agents/test_case_generator.py`
- `core/agents/case_reviewer.py`
- `core/utils/llm_client.py`

---

## Issue 2：评审反馈注入生成器（有效迭代）

**标签**: `enhancement` `priority-high`

### 问题描述

当前评审不通过后的迭代是"盲目重试"——`generate_test_cases_node` 重新执行时完全不知道上一次哪里出了问题，导致迭代没有实际改进效果。

```python
# 当前：重新生成时没有带上评审意见
def generate_test_cases_node(state: AgentState) -> dict:
    generator = TestCaseGenerator()
    for req in requirements:
        test_cases = generator.generate(req)  # 不知道上次哪里不好
```

### 优化方案

将评审意见作为约束条件注入生成器的 prompt：

```python
def generate_test_cases_node(state: AgentState) -> dict:
    feedback = state.get("review_suggestions", [])
    review_comments = state.get("review_comments", [])
    iteration = state.get("iteration_count", 0)

    for req in requirements:
        # 第二次及以后迭代，带上上次的问题
        if iteration > 0 and feedback:
            test_cases = generator.generate(req, improvement_hints=feedback)
        else:
            test_cases = generator.generate(req)
```

同时在 `TestCaseGenerator._build_prompt()` 中增加 `improvement_hints` 参数：

```python
def _build_prompt(self, requirement: Requirement, improvement_hints: list = None) -> str:
    hint_section = ""
    if improvement_hints:
        hint_section = f"""
## 上次评审发现的问题（本次必须修复）
{chr(10).join(f'- {h}' for h in improvement_hints)}
"""
    return f"""...{hint_section}..."""
```

### 预期收益

- 迭代有实际意义，第二次生成质量明显高于第一次
- 减少无效迭代次数，节省 LLM 调用成本

### 涉及文件

- `core/agents/workflow.py` — `generate_test_cases_node`
- `core/agents/test_case_generator.py` — `_build_prompt`

---

## Issue 3：并行 Agent（需求级 fan-out）

**标签**: `enhancement` `performance` `priority-medium`

### 问题描述

当前多个需求的测试用例生成是串行的，需求越多耗时越长：

```python
# 当前：串行处理，N 个需求 = N 次串行 LLM 调用
for req in requirements:
    test_cases = generator.generate(req)
    all_test_cases.extend(test_cases)
```

### 优化方案

使用 LangGraph 的 `Send` API 实现需求级并行处理：

```python
from langgraph.constants import Send

def fan_out_requirements(state: AgentState):
    """将每个需求分发给独立的生成节点并行处理"""
    return [
        Send("generate_for_single_req", {
            "req": req,
            "feedback": state.get("review_suggestions", []),
            "iteration": state.get("iteration_count", 0)
        })
        for req in state["requirements"]
    ]

def generate_for_single_req(state: dict) -> dict:
    """单个需求的测试用例生成（并行执行）"""
    generator = TestCaseGenerator()
    test_cases = generator.generate(state["req"])
    return {"partial_test_cases": test_cases}

def fan_in_results(state: AgentState) -> dict:
    """汇总所有并行生成的结果"""
    all_cases = []
    for partial in state.get("partial_test_cases_list", []):
        all_cases.extend(partial)
    return {"test_cases": all_cases}
```

### 预期收益

- 多需求场景下执行时间从 O(n) 降为 O(1)（受限于 API 并发限制）
- 体现 LangGraph 的核心价值

### 涉及文件

- `core/agents/workflow.py` — 重构 `generate_test_cases_node`

---

## Issue 4：Tool Calling — Agent 主动获取页面信息

**标签**: `enhancement` `feature` `priority-medium`

### 问题描述

当前 Agent 生成测试用例时完全依赖需求文档的文字描述，无法感知真实页面结构，导致：

- 生成的选择器是猜测的（`input[name="email"]` 等）
- 无法发现需求文档中未提及的 UI 元素
- 测试脚本实际运行失败率高

### 优化方案

为 Agent 提供工具集，让其在生成测试用例前主动探测目标页面：

```python
from langchain_core.tools import tool

@tool
def screenshot_page(url: str) -> str:
    """截取页面截图并返回 base64，用于 AI 视觉分析页面结构"""
    # 使用 Playwright 截图
    ...

@tool
def get_page_dom(url: str) -> str:
    """获取页面的关键 DOM 结构，提取表单、按钮、输入框等元素"""
    # 使用 Playwright 获取 DOM
    ...

@tool
def search_similar_test_cases(requirement_title: str) -> str:
    """搜索历史测试用例库中相似的用例，避免重复生成"""
    # 搜索本地缓存或数据库
    ...

# 绑定工具到 LLM
llm_with_tools = llm.bind_tools([screenshot_page, get_page_dom, search_similar_test_cases])
```

### 预期收益

- 生成的测试脚本基于真实 DOM，选择器准确率大幅提升
- Agent 具备真正的"感知-决策-行动"能力
- 这是与普通 LLM 调用最大的差异化亮点

### 涉及文件

- `core/utils/tools.py` — 新建工具模块
- `core/agents/test_case_generator.py` — 集成工具调用
- `core/utils/llm_client.py` — 支持 `bind_tools`

---

## Issue 5：Human-in-the-loop（人工介入节点）

**标签**: `enhancement` `feature` `priority-medium`

### 问题描述

当前工作流是全自动的，没有任何人工介入点。在以下场景中，全自动执行存在风险：

- 评审多次不通过时，应该让人工决定是否继续
- 生成的测试脚本执行前，应该允许人工确认
- 需求分析结果有歧义时，应该让人工澄清

### 优化方案

使用 LangGraph 的 `interrupt` 机制在关键节点暂停等待人工输入：

```python
from langgraph.types import interrupt

def human_review_node(state: AgentState) -> dict:
    """人工审核节点 — 暂停等待人工决策"""
    review_score = state.get("review_score", 0)
    iteration = state.get("iteration_count", 0)

    # 展示当前状态给人工
    summary = {
        "iteration": iteration,
        "score": review_score,
        "test_cases_count": len(state.get("test_cases", [])),
        "issues": state.get("review_suggestions", [])
    }

    # 暂停，等待人工输入
    human_decision = interrupt({
        "message": "测试用例评审未通过，请决定下一步操作",
        "summary": summary,
        "options": ["continue", "skip_review", "abort"]
    })

    return {"human_decision": human_decision}

def route_after_human(state: AgentState) -> str:
    decision = state.get("human_decision", "continue")
    if decision == "abort":
        return END
    elif decision == "skip_review":
        return "generate_script"
    else:
        return "generate_test_cases"
```

### 预期收益

- 关键节点有人工把关，避免低质量用例进入执行阶段
- 体现"支持人工审核关键节点"的设计原则（项目规范要求）
- LangGraph 的核心特性之一，体现框架使用深度

### 涉及文件

- `core/agents/workflow.py` — 新增 `human_review_node`
- `main_v2.py` — 支持 checkpointer（持久化中间状态）

---

## Issue 6：Agent 记忆与历史用例复用

**标签**: `enhancement` `feature` `priority-low`

### 问题描述

每次运行工作流都是全新开始，没有利用历史执行数据：

- 相同需求重复生成，浪费 LLM 调用
- 历史测试用例中的好用例无法复用
- 无法从历史失败中学习

### 优化方案

引入 LangGraph 的 `MemorySaver` 或外部存储实现跨会话记忆：

```python
from langgraph.checkpoint.memory import MemorySaver

# 编译时注入 checkpointer
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# 运行时指定 thread_id，相同项目复用历史状态
config = {"configurable": {"thread_id": "project-login-feature"}}
result = app.invoke(initial_state, config=config)
```

同时建立本地测试用例缓存，避免重复生成：

```python
# 基于需求内容的哈希缓存
cache_key = hashlib.md5(requirement_text.encode()).hexdigest()
if cache.exists(cache_key):
    return cache.get(cache_key)
```

### 预期收益

- 相同需求直接复用缓存，响应速度提升 10x
- 支持断点续跑，中途失败不需要从头开始
- 为后续引入数据库（PostgreSQL）打基础

### 涉及文件

- `core/utils/cache.py` — 新建缓存模块
- `core/agents/workflow.py` — 集成 checkpointer
- `main_v2.py` — 传入 thread_id

---

---

## Issue 7：LLMClient 缺少重试机制和 Token 成本追踪

**标签**: `enhancement` `reliability` `priority-high`

### 问题描述

当前 `LLMClient.chat()` 直接调用 `self._llm.invoke()`，没有任何容错处理：

- 网络抖动或 API 限流时直接抛出异常，整个工作流中断
- 没有记录每次调用的 Token 消耗，无法统计成本
- 每次调用都创建新的 `LLMClient` 实例（各 Agent 的 `__init__` 都调用 `get_llm_client()`），浪费资源

### 优化方案

**1. 加入指数退避重试：**

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
)
def chat(self, messages, ...):
    ...
```

**2. Token 成本追踪：**

```python
class TokenTracker:
    """全局 Token 使用统计"""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0

    def record(self, usage: TokenUsage):
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens

    @property
    def estimated_cost_usd(self) -> float:
        # 按模型单价计算
        ...
```

**3. 单例 LLMClient：**

```python
_client_instance = None

def get_llm_client() -> LLMClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient()
    return _client_instance
```

### 涉及文件

- `core/utils/llm_client.py`

---

## Issue 8：MidsceneScriptGenerator 的 action 转换逻辑脆弱

**标签**: `bug` `enhancement` `priority-high`

### 问题描述

`_convert_action_to_ai_prompt()` 和 `_convert_expected_to_ai_prompt()` 用大量 `if "关键词" in action` 的字符串匹配来转换测试步骤，这是整个项目最脆弱的部分：

```python
# 当前：硬编码关键词匹配，极易失效
if "输入" in action or "填写" in action:
    if "邮箱" in action or "用户名" in action:
        return f'在邮箱或用户名输入框中输入 "{data}"'
    elif "密码" in action:
        return f'在密码输入框中输入 "{data}"'
    elif "搜索" in action or "关键词" in action:
        ...
# 遇到"请在搜索栏键入内容"这类描述就完全失效
```

而且 `_generate_decorators()` 方法生成的是 Python pytest 装饰器，但脚本是 TypeScript，这个方法根本没被调用，是死代码。

### 优化方案

**方案 A（短期）**：把 action 转换也交给 LLM 处理，而不是规则匹配：

```python
def _convert_action_to_ai_prompt(self, action: str, data: str) -> str:
    """用 LLM 将测试步骤转换为 Midscene 自然语言指令"""
    # 对于简单操作，LLM 一次调用可以批量转换所有步骤
    # 避免每个步骤单独调用
    ...
```

**方案 B（长期，配合 Issue #4）**：结合 Tool Calling，让 Agent 在生成脚本时直接感知页面 DOM，生成精确的选择器而不是自然语言描述。

同时清理死代码 `_generate_decorators()`。

### 涉及文件

- `core/automation/midscene_generator.py`

---

## Issue 9：TestExecutor 输出解析用正则匹配，不稳定

**标签**: `bug` `reliability` `priority-medium`

### 问题描述

`parse_playwright_output()` 用正则表达式解析 Playwright CLI 的文本输出来统计测试结果，这非常脆弱：

- Playwright 版本升级后输出格式变化会导致解析失败
- 文件中有两段重复的汇总解析代码（第二段是死代码，`return` 之后的代码永远不会执行）
- 中文路径、特殊字符可能导致正则匹配失败

```python
# 当前：解析文本输出，脆弱
summary_passed = re.search(r"(\d+)\s+passed", output)

# 文件中存在死代码（return 之后还有代码）
results["total"] = results["passed"] + results["failed"] + results["skipped"]
return results  # ← 这里已经 return 了

# 下面这段永远不会执行
summary_passed = re.search(r"(\d+)\s+passed", output)  # 死代码
```

### 优化方案

使用 Playwright 的 JSON reporter 替代文本解析：

```python
# 让 Playwright 输出 JSON 格式结果
cmd = ["npx", "playwright", "test", script_path,
       "--reporter=json",           # 输出 JSON
       f"--output={json_output_path}"]

# 直接解析 JSON，稳定可靠
with open(json_output_path) as f:
    report = json.load(f)
    passed = report["stats"]["expected"]
    failed = report["stats"]["unexpected"]
```

同时清理死代码。

### 涉及文件

- `core/automation/test_executor.py`

---

## Issue 10：工作流缺少可观测性（Tracing）

**标签**: `enhancement` `observability` `priority-medium`

### 问题描述

当前工作流的执行过程只有 `print()` 输出，无法：

- 追踪每个 Agent 节点的输入/输出
- 统计各节点耗时
- 在出错时快速定位是哪个节点、哪次 LLM 调用出了问题
- 对比不同迭代之间的差异

### 优化方案

**方案 A：集成 LangSmith（LangChain 官方追踪）**

```python
# 只需设置环境变量，自动追踪所有 LangChain 调用
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-key"
os.environ["LANGCHAIN_PROJECT"] = "ai-test-platform"
```

**方案 B：轻量级本地追踪（不依赖外部服务）**

```python
import time
from functools import wraps

def trace_node(node_name: str):
    """节点追踪装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(state):
            start = time.time()
            print(f"[TRACE] → {node_name} 开始")
            result = func(state)
            elapsed = time.time() - start
            print(f"[TRACE] ← {node_name} 完成 ({elapsed:.2f}s)")
            # 写入追踪日志
            _write_trace_log(node_name, state, result, elapsed)
            return result
        return wrapper
    return decorator

@trace_node("analyze_requirements")
def analyze_requirements_node(state):
    ...
```

### 涉及文件

- `core/agents/workflow.py`
- `core/utils/llm_client.py`
- `.env.example` — 新增 LangSmith 配置项

---

## Issue 11：main_v2.py 硬编码需求文件和 URL

**标签**: `enhancement` `usability` `priority-low`

### 问题描述

`main_v2.py` 中需求文件路径和目标 URL 是硬编码的：

```python
# 当前：硬编码，每次换需求都要改代码
requirement_file = "examples/requirement_baidu.md"
final_state = run_workflow(
    requirement_text=requirement_text,
    page_url="https://www.baidu.com"  # 可根据实际项目修改
)
```

### 优化方案

支持命令行参数和配置文件两种方式：

```python
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="AI 测试自动化平台")
    parser.add_argument("--requirement", "-r",
                        default="examples/requirement_baidu.md",
                        help="需求文档路径")
    parser.add_argument("--url", "-u",
                        default="https://www.baidu.com",
                        help="目标页面 URL")
    parser.add_argument("--max-iterations", "-i",
                        type=int, default=2,
                        help="最大迭代次数")
    parser.add_argument("--no-execute", action="store_true",
                        help="只生成用例，不执行测试")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)
```

使用方式：
```bash
python main_v2.py --requirement examples/requirement_login.md --url https://example.com/login
python main_v2.py -r docs/req.md -u https://app.com --no-execute
```

### 涉及文件

- `main_v2.py`

---

## Issue 12：代理设置清除代码散落各处

**标签**: `tech-debt` `priority-low`

### 问题描述

清除代理环境变量的代码在多个文件中重复出现：

```python
# 以下代码出现在：
# - main_v2.py
# - core/agents/workflow.py
# - core/automation/test_executor.py
for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(var, None)
os.environ['NO_PROXY'] = '*'
```

### 优化方案

统一到 `core/utils/env_setup.py`，在 `main_v2.py` 入口处调用一次：

```python
# core/utils/env_setup.py
def disable_proxy():
    """禁用系统代理，解决国内环境连接问题"""
    for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        os.environ.pop(var, None)
    os.environ['NO_PROXY'] = '*'

# main_v2.py — 只在入口调用一次
from core.utils.env_setup import disable_proxy
disable_proxy()
```

### 涉及文件

- `main_v2.py`
- `core/agents/workflow.py`
- `core/automation/test_executor.py`
- `core/utils/env_setup.py` — 新建

---

## 优先级汇总

| Issue | 标题 | 难度 | 亮点 | 优先级 |
|-------|------|------|------|--------|
| #1 | 结构化输出替换手动 JSON 解析 | 低 | 中 | P0 |
| #2 | 评审反馈注入生成器 | 低 | 高 | P0 |
| #7 | LLMClient 重试机制和 Token 追踪 | 低 | 中 | P0 |
| #8 | MidsceneScriptGenerator action 转换 | 中 | 高 | P0 |
| #9 | TestExecutor 输出解析改用 JSON reporter | 低 | 中 | P0 |
| #3 | 并行 Agent（fan-out） | 中 | 高 | P1 |
| #4 | Tool Calling | 高 | 非常高 | P1 |
| #5 | Human-in-the-loop | 中 | 高 | P1 |
| #10 | 工作流可观测性（Tracing） | 中 | 高 | P1 |
| #6 | Agent 记忆与历史用例复用 | 中 | 中 | P2 |
| #11 | main_v2.py 支持命令行参数 | 低 | 低 | P2 |
| #12 | 代理设置清除代码去重 | 低 | 低 | P2 |

---

## Issue 13：requirement_analyzer_v2.py 是废弃文件，导入路径已损坏

**标签**: `bug` `tech-debt` `priority-high`

### 问题描述

`core/agents/requirement_analyzer_v2.py` 是一个遗留文件，存在严重问题：

```python
# 错误的导入路径（缺少 core. 前缀，运行时直接报 ModuleNotFoundError）
from models.requirement import Requirement, RequirementAnalysisResult  # ❌
from models.config import get_settings                                  # ❌

# 正确应该是
from core.models.requirement import ...
from core.models.config import ...
```

同时它使用了已废弃的 Pydantic V1 API：
```python
print(result.json(ensure_ascii=False, indent=2))  # ❌ Pydantic V2 已移除 .json()
# 应该是
print(result.model_dump_json(indent=2))
```

而且 `requirement_analyzer.py` 已经是完整的 Pydantic 版本，这个 v2 文件完全是重复代码。

### 优化方案

直接删除 `requirement_analyzer_v2.py`，它的功能已经被 `requirement_analyzer.py` 完全覆盖。

### 涉及文件

- `core/agents/requirement_analyzer_v2.py` — 删除

---

## Issue 14：Requirement ID 格式限制过严，超过 999 个需求就崩溃

**标签**: `bug` `priority-medium`

### 问题描述

`Requirement` 和 `TestCase` 的 ID 格式用正则强制限制为 3 位数字：

```python
# core/models/requirement.py
id: str = Field(pattern=r"^REQ_\d{3}$")  # 只允许 REQ_001 ~ REQ_999

# core/models/test_case.py
id: str = Field(pattern=r"^TC_\d{3}$")   # 只允许 TC_001 ~ TC_999
```

当需求超过 999 个，或者 LLM 生成了 `REQ_0001`（4位）这样的 ID 时，Pydantic 验证直接失败，触发降级逻辑。

实际上 LLM 有时会生成 `TC_001_001`（子用例）这样的格式，也会被拒绝。

### 优化方案

放宽正则，支持更多位数：

```python
# 支持 1-6 位数字，兼容子用例格式
id: str = Field(pattern=r"^REQ_\d{1,6}$")
id: str = Field(pattern=r"^TC_[\d_]{1,10}$")  # 支持 TC_001_001 格式
```

### 涉及文件

- `core/models/requirement.py`
- `core/models/test_case.py`

---

## Issue 15：TestCase.title 禁止以数字开头，但 LLM 经常生成这样的标题

**标签**: `bug` `priority-medium`

### 问题描述

`TestCase` 的 title 验证器禁止标题以数字开头：

```python
@field_validator('title')
@classmethod
def validate_title_format(cls, v):
    if v[0].isdigit():
        raise ValueError("测试用例标题不能以数字开头")
```

但 LLM 生成的标题经常是 `"1. 验证用户登录成功"` 或 `"TC001 正常登录流程"` 这样的格式，导致验证失败触发降级，生成质量下降。

这个限制没有实际业务意义。

### 优化方案

移除这个不合理的限制，只保留真正有意义的验证（长度、特殊字符）：

```python
@field_validator('title')
@classmethod
def validate_title_format(cls, v):
    v = v.strip()
    # 只过滤真正有问题的字符（文件系统不允许的）
    invalid_chars = ['<', '>', '|', '*', '?', '"', '\n', '\r']
    for char in invalid_chars:
        if char in v:
            raise ValueError(f"标题不能包含字符: {char}")
    return v
```

### 涉及文件

- `core/models/test_case.py`

---

## Issue 16：config.yaml 与 ProjectSettings 双重配置，实际只用了一个

**标签**: `tech-debt` `priority-medium`

### 问题描述

项目有两套配置系统：

1. `config/config.yaml` — YAML 文件配置
2. `core/models/config.py` 的 `ProjectSettings` — 从 `.env` 读取

但实际代码中**只使用了 `ProjectSettings`**，`config.yaml` 从未被读取（没有任何代码 `import` 或 `open` 它）。这造成了混乱：

- 新人看到 `config.yaml` 会以为修改它有效，实际无效
- `config.yaml` 中的 `llm.temperature: 0.7` 和 `ProjectSettings` 中的 `llm_temperature: float = Field(default=0.7)` 是两份独立的默认值

### 优化方案

二选一：

**方案 A（推荐）**：删除 `config.yaml`，在 `ProjectSettings` 中补充注释说明每个配置项的含义，`.env.example` 作为唯一配置参考。

**方案 B**：让 `ProjectSettings` 支持从 `config.yaml` 读取默认值，`.env` 只覆盖敏感信息（API Key）：

```python
import yaml

class ProjectSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        yaml_file="config/config.yaml",  # pydantic-settings 支持 yaml
    )
```

### 涉及文件

- `config/config.yaml`
- `core/models/config.py`

---

## Issue 17：playwright.config.ts 有重复字段和错误的 baseURL

**标签**: `bug` `priority-medium`

### 问题描述

`config/playwright.config.ts` 有两个问题：

**1. `outputFolder` 字段重复定义：**
```typescript
reporter: [
  ['allure-playwright', { 
    outputFolder: 'allure-results',   // 第一次
    suiteTitle: false,
    detail: true,
    outputFolder: './allure-results'  // 第二次，覆盖了第一次 ❌
  }]
],
```

**2. `baseURL` 硬编码为 `localhost:3000`，但测试的是百度等外部网站：**
```typescript
use: {
  baseURL: 'http://localhost:3000',  // ❌ 测试百度时完全用不到
}
```

### 优化方案

```typescript
reporter: [
  ['allure-playwright', { 
    outputFolder: './allure-results',  // 只保留一个，用相对路径
    suiteTitle: false,
    detail: true,
  }]
],
use: {
  baseURL: process.env.TEST_BASE_URL || 'https://example.com',  // 从环境变量读取
}
```

### 涉及文件

- `config/playwright.config.ts`

---

## Issue 18：markdown_parser.py 过于简单，无法处理复杂需求文档

**标签**: `enhancement` `priority-medium`

### 问题描述

当前的 `parse_markdown()` 只是简单地 `open` + `read`，完全没有解析：

```python
def parse_markdown(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content  # 直接返回原始文本
```

`extract_sections()` 函数只处理一级标题（`# `），遇到二级标题（`## `）就会出错，而且这个函数在整个项目中从未被调用过（死代码）。

实际问题：
- 不支持 PDF、Word 格式（`config.yaml` 里提到了支持，但没实现）
- 不能提取结构化信息（表格、列表、代码块）
- 大型需求文档直接全文传给 LLM，Token 浪费严重

### 优化方案

**短期**：改进 `extract_sections()` 支持多级标题，并在 `RequirementAnalyzer` 中实际使用它做预处理：

```python
def extract_sections(content: str, max_level: int = 3) -> Dict[str, str]:
    """提取多级标题章节"""
    sections = {}
    # 支持 #, ##, ### 等多级标题
    pattern = re.compile(r'^(#{1,' + str(max_level) + r'})\s+(.+)$', re.MULTILINE)
    ...
```

**长期**：支持多格式文档：

```python
class DocumentParser:
    def parse(self, file_path: str) -> str:
        suffix = Path(file_path).suffix.lower()
        if suffix == '.md':
            return self._parse_markdown(file_path)
        elif suffix == '.pdf':
            return self._parse_pdf(file_path)      # PyMuPDF
        elif suffix in ('.docx', '.doc'):
            return self._parse_word(file_path)     # python-docx
        elif suffix == '.txt':
            return self._parse_text(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")
```

### 涉及文件

- `core/parsers/markdown_parser.py`
- `core/parsers/__init__.py`

---

## Issue 19：AgentState 使用 TypedDict，无法享受 Pydantic 验证

**标签**: `enhancement` `priority-medium`

### 问题描述

`workflow.py` 的 `AgentState` 用 `TypedDict` 定义，而项目其他地方都在用 Pydantic：

```python
class AgentState(TypedDict):
    requirement_text: str
    requirements: Optional[List[dict]]   # ← 用 dict 而不是 Requirement 模型
    test_cases: Optional[List[dict]]     # ← 同上
    review_score: Optional[float]
    ...
```

问题：
- `requirements` 和 `test_cases` 存的是 `dict`，但 Agent 内部用的是 Pydantic 模型，存取时需要反复 `model_dump()` / `model_validate()`
- `TypedDict` 没有运行时验证，字段类型错误只能在运行时发现
- `iteration_count` 没有默认值，初始化时必须手动设为 0，容易遗漏

### 优化方案

LangGraph 支持 Pydantic 模型作为 State：

```python
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    """Agent 共享状态 - Pydantic 版本"""
    requirement_text: str
    requirements: List[Requirement] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(default_factory=list)
    review_passed: bool = False
    review_score: float = 0.0
    review_comments: List[ReviewComment] = Field(default_factory=list)
    review_suggestions: List[str] = Field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 2
    ...
```

这样 Agent 节点可以直接操作 Pydantic 对象，不需要反复转换。

### 涉及文件

- `core/agents/workflow.py`

---

## Issue 20：缺少单元测试，核心逻辑无法验证

**标签**: `enhancement` `testing` `priority-high`

### 问题描述

项目 `tests/` 目录结构存在但几乎没有实际测试：

- `tests/unit/` — 目录存在，内容未知
- `tests/integration/` — 目录存在，内容未知
- 核心 Agent 逻辑（JSON 解析、Pydantic 验证、路由逻辑）完全没有测试覆盖

每次修改 Agent 代码都需要跑完整流程（调用 LLM）才能验证，成本高、速度慢。

### 优化方案

为核心逻辑添加不依赖 LLM 的单元测试：

```python
# tests/unit/test_requirement_analyzer.py
import pytest
from unittest.mock import patch, MagicMock
from core.agents.requirement_analyzer import RequirementAnalyzer

class TestRequirementAnalyzer:

    def test_extract_json_from_markdown_block(self):
        """测试从 markdown 代码块提取 JSON"""
        analyzer = RequirementAnalyzer()
        content = '```json\n{"key": "value"}\n```'
        result = analyzer._extract_json(content)
        assert result == {"key": "value"}

    def test_fix_json_format_with_prefix(self):
        """测试修复带前缀的 JSON"""
        analyzer = RequirementAnalyzer()
        content = 'json\n{"key": "value"}'
        result = analyzer._fix_json_format(content)
        assert result.startswith('{')

    @patch('core.agents.requirement_analyzer.get_llm_client')
    def test_analyze_with_mock_llm(self, mock_llm_factory):
        """用 Mock LLM 测试完整分析流程"""
        mock_llm = MagicMock()
        mock_llm.chat_simple.return_value = '''
        {"requirements": [{"id": "REQ_001", "title": "登录功能",
          "description": "用户可以登录系统", "priority": "high",
          "type": "functional", "acceptance_criteria": ["登录成功跳转首页"],
          "ui_elements": ["邮箱输入框"]}],
         "summary": "登录功能需求", "total_count": 1}
        '''
        mock_llm_factory.return_value = mock_llm

        analyzer = RequirementAnalyzer()
        result = analyzer.analyze("用户登录功能需求文档")
        assert len(result["requirements"]) == 1
```

### 涉及文件

- `tests/unit/test_requirement_analyzer.py` — 新建
- `tests/unit/test_test_case_generator.py` — 新建
- `tests/unit/test_workflow_routing.py` — 新建
- `tests/unit/test_models.py` — 新建

---

## Issue 21：缺少日志系统，全靠 print()

**标签**: `enhancement` `observability` `priority-medium`

### 问题描述

整个项目用 `print()` 输出信息，没有正式的日志系统：

- 无法按级别过滤（DEBUG/INFO/WARNING/ERROR）
- 无法写入文件持久化
- 无法在生产环境关闭调试输出
- `[DEBUG]` 标记的调试信息和正常输出混在一起

`LogConfig` 模型已经在 `config.py` 中定义好了，但从未被使用。

### 优化方案

在项目入口初始化标准 logging，替换所有 `print()`：

```python
# core/utils/logger.py
import logging
import logging.handlers
from core.models.config import get_settings

def setup_logging():
    settings = get_settings()
    log_config = settings.get_log_config()

    logging.basicConfig(
        level=getattr(logging, log_config.level),
        format=log_config.format,
        handlers=[
            logging.StreamHandler(),
            *([ logging.handlers.RotatingFileHandler(
                    log_config.file,
                    maxBytes=log_config.max_size * 1024 * 1024,
                    backupCount=log_config.backup_count
                )] if log_config.file else [])
        ]
    )

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

# 各模块使用
logger = get_logger(__name__)
logger.info("[Agent] 需求分析中...")
logger.debug(f"[DEBUG] 脚本路径: {script_path}")
logger.error(f"[ERROR] LLM 评审失败: {e}")
```

### 涉及文件

- `core/utils/logger.py` — 新建
- 所有 Agent 和 automation 模块 — 替换 `print()`

---

## Issue 22：AllureReporter.open_report() 启动 HTTP 服务后进程泄漏

**标签**: `bug` `priority-low`

### 问题描述

`open_report()` 用 `subprocess.Popen` 启动了一个 Python HTTP 服务进程，但：

- 进程 PID 虽然返回了，但没有任何机制在程序退出时关闭它
- 每次运行 `main_v2.py` 都会启动一个新的 HTTP 服务，端口随机，旧进程一直占用内存
- Windows 上 `DETACHED_PROCESS` 标志让进程完全脱离父进程，无法被 Python 的 `atexit` 清理

### 优化方案

**方案 A**：改用 `allure open` 命令（会自动管理进程生命周期）：

```python
# allure open 会自动打开浏览器并在关闭时退出
subprocess.run(["allure", "open", str(self.report_dir)])
```

**方案 B**：注册 `atexit` 清理函数：

```python
import atexit

def open_report(self):
    process = subprocess.Popen(...)
    atexit.register(process.terminate)  # 程序退出时自动终止
    return {"pid": process.pid, ...}
```

**方案 C（最简单）**：直接用 `webbrowser` 打开已生成的静态 HTML 文件，不需要 HTTP 服务：

```python
import webbrowser
index_file = self.report_dir / "index.html"
webbrowser.open(f"file:///{index_file.absolute()}")
```

### 涉及文件

- `core/automation/allure_reporter.py`

---

## Issue 23：需求文档示例太简单，无法测试复杂场景

**标签**: `enhancement` `priority-low`

### 问题描述

`examples/` 目录只有两个极简的需求文档：

- `requirement_login.md` — 登录功能，约 30 行
- `requirement_baidu.md` — 百度搜索，约 20 行

这两个文档太简单，无法暴露以下问题：
- 多需求文档（10+ 个需求）时的并行性能
- 需求之间有依赖关系时的处理
- 包含表格、图片引用、代码块的复杂 Markdown
- 非功能性需求（性能、安全）的处理

### 优化方案

补充更丰富的示例文档：

```
examples/
├── requirement_login.md          # 现有：简单登录
├── requirement_baidu.md          # 现有：简单搜索
├── requirement_ecommerce.md      # 新增：电商购物车（多需求、有依赖）
├── requirement_complex.md        # 新增：包含表格、非功能需求
└── requirement_api.md            # 新增：API 接口测试需求
```

### 涉及文件

- `examples/` — 新增示例文件

---

## 优先级汇总（完整版）

| Issue | 标题 | 类型 | 难度 | 优先级 |
|-------|------|------|------|--------|
| #1 | 结构化输出替换手动 JSON 解析 | 重构 | 低 | P0 |
| #2 | 评审反馈注入生成器 | 功能 | 低 | P0 |
| #7 | LLMClient 重试机制和 Token 追踪 | 可靠性 | 低 | P0 |
| #8 | MidsceneScriptGenerator action 转换脆弱 | Bug | 中 | P0 |
| #9 | TestExecutor 改用 JSON reporter + 清理死代码 | Bug | 低 | P0 |
| #13 | 删除损坏的 requirement_analyzer_v2.py | Bug | 低 | P0 |
| #15 | TestCase.title 不合理的数字开头限制 | Bug | 低 | P0 |
| #17 | playwright.config.ts 重复字段和错误 baseURL | Bug | 低 | P0 |
| #3 | 并行 Agent（fan-out） | 性能 | 中 | P1 |
| #4 | Tool Calling | 功能 | 高 | P1 |
| #5 | Human-in-the-loop | 功能 | 中 | P1 |
| #10 | 工作流可观测性（Tracing） | 可观测性 | 中 | P1 |
| #14 | ID 格式正则限制过严 | Bug | 低 | P1 |
| #16 | config.yaml 与 ProjectSettings 双重配置 | 重构 | 低 | P1 |
| #18 | markdown_parser 过于简单 | 功能 | 中 | P1 |
| #19 | AgentState 改用 Pydantic 模型 | 重构 | 中 | P1 |
| #20 | 缺少单元测试 | 测试 | 中 | P1 |
| #21 | 缺少日志系统 | 可观测性 | 低 | P1 |
| #6 | Agent 记忆与历史用例复用 | 功能 | 中 | P2 |
| #11 | main_v2.py 支持命令行参数 | 易用性 | 低 | P2 |
| #12 | 代理设置清除代码去重 | 重构 | 低 | P2 |
| #22 | AllureReporter HTTP 服务进程泄漏 | Bug | 低 | P2 |
| #23 | 需求文档示例太简单 | 文档 | 低 | P2 |

---

## Issue 24：requirements.txt 缺少关键依赖，且版本固定策略不一致

**标签**: `bug` `dependency` `priority-high`

### 问题描述

`requirements.txt` 存在多个问题：

**1. 缺少已使用的依赖：**
```
# 代码中已使用但未列出
langgraph          # workflow.py 中 from langgraph.graph import StateGraph
pydantic-settings  # config.py 中 from pydantic_settings import BaseSettings
tenacity           # 重试机制（计划中）
httpx              # llm_client.py 中 import httpx
```

**2. 列出了未使用的依赖：**
```
PyMuPDF==1.24.0    # 代码中从未 import，markdown_parser.py 只用了内置 open()
python-docx==1.1.0 # 同上，从未使用
markdown==3.7      # 同上，从未使用
```

**3. 版本固定过死，升级困难：**
```
openai==1.12.0     # 固定到小版本，安全补丁无法自动获取
langchain==0.3.13  # 同上
```

### 优化方案

```
# requirements.txt（修正版）

# LLM 和 Agent
openai>=1.12.0,<2.0.0
langchain>=0.3.13,<0.4.0
langchain-core>=0.3.28,<0.4.0
langchain-openai>=0.2.14,<0.3.0
langgraph>=0.2.0,<0.3.0          # 补充缺失

# 数据验证
pydantic>=2.10.3,<3.0.0
pydantic-settings>=2.0.0,<3.0.0  # 补充缺失

# HTTP 客户端
httpx>=0.27.0,<1.0.0              # 补充缺失

# 文档解析（按需安装）
PyMuPDF>=1.24.0                   # 仅在需要 PDF 解析时
python-docx>=1.1.0                # 仅在需要 Word 解析时

# UI 自动化
playwright>=1.48.0,<2.0.0
pytest-playwright>=0.5.2

# 测试框架
pytest>=8.3.4
pytest-asyncio>=0.24.0
allure-pytest>=2.13.5

# 工具
python-dotenv>=1.0.1
pyyaml>=6.0.2
```

### 涉及文件

- `requirements.txt`

---

## Issue 25：main.py（阶段1）与 main_v2.py（阶段2）并存，职责不清

**标签**: `tech-debt` `priority-medium`

### 问题描述

项目根目录有两个入口文件：

- `main.py` — 阶段1，直接调用 Agent，无 LangGraph
- `main_v2.py` — 阶段2，使用 LangGraph 工作流

两个文件有大量重复代码（`clean_history_data()`、`save_results()` 等函数几乎一模一样），而且 `main.py` 已经过时，README 也说"推荐使用 main_v2.py"。

但 `main.py` 仍然存在，新人不知道该用哪个，而且两个文件的重复代码会导致维护时只改了一处。

### 优化方案

**方案 A**：删除 `main.py`，将阶段1的功能作为 `main_v2.py` 的 `--simple` 模式：
```bash
python main_v2.py --simple   # 阶段1模式，不用 LangGraph
python main_v2.py            # 阶段2模式（默认）
```

**方案 B**：保留 `main.py` 但重命名为 `main_v1.py`，并在文件顶部加明显的废弃注释：
```python
# ⚠️ 已废弃：请使用 main_v2.py
# 此文件仅作为阶段1的历史参考
```

同时将公共函数（`clean_history_data` 等）提取到 `core/utils/runner.py`。

### 涉及文件

- `main.py`
- `main_v2.py`
- `core/utils/runner.py` — 新建（提取公共逻辑）

---

## Issue 26：generate_allure_from_results.py 硬编码了错误信息和测试名称

**标签**: `bug` `priority-medium`

### 问题描述

`scripts/generate_allure_from_results.py` 是一个降级脚本，但它有严重的硬编码问题：

```python
# 硬编码的错误信息（来自某次具体的运行）
error_message = "failed to call AI model service: 400 Access denied, please make sure your account is in good standing"

# 硬编码的默认测试名称（百度搜索相关）
if not failed_tests:
    failed_tests = [
        "TC_001: 验证使用有效关键词进行搜索并成功跳转",
        "TC_002: 验证搜索框为空时点击搜索按钮的处理",
        "TC_003: 验证搜索特殊字符关键词"
    ]

# 硬编码的执行时间
duration=2.5 + i * 0.2  # 模拟不同的执行时间
```

这意味着无论实际运行什么测试，降级报告永远显示"百度搜索"的测试名称和同一个错误信息。

### 优化方案

从 `output/test_cases*.json` 读取实际的测试用例名称，从 `output/execution*.json` 读取实际的错误信息：

```python
# 从测试用例文件读取实际名称
test_cases_files = list(output_dir.glob("test_cases*.json"))
if test_cases_files:
    with open(max(test_cases_files, key=lambda p: p.stat().st_mtime)) as f:
        data = json.load(f)
        failed_tests = [f"{tc['id']}: {tc['title']}" for tc in data.get("test_cases", [])]

# 从执行结果读取实际错误信息
error_message = execution_data.get("error") or execution_data.get("stderr", "测试执行失败")
```

### 涉及文件

- `scripts/generate_allure_from_results.py`

---

## Issue 27：conftest.py 中 OUTPUT_DIR 被重复定义，覆盖了导入的值

**标签**: `bug` `priority-medium`

### 问题描述

`tests/conftest.py` 中存在变量遮蔽（shadowing）问题：

```python
# 第1行：从 project_paths 导入
from core.utils.project_paths import OUTPUT_DIR, GENERATED_TESTS_DIR

# 第N行：又重新赋值，覆盖了导入的值！
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / OUTPUT_DIR          # ← 用绝对路径覆盖了相对路径
GENERATED_TESTS_DIR = PROJECT_ROOT / GENERATED_TESTS_DIR  # ← 同上
```

这会导致：
- `project_paths.py` 中的路径是相对路径（`Path("output")`）
- `conftest.py` 中变成了绝对路径（`/path/to/project/output`）
- 两处路径不一致，可能导致清理操作作用在错误的目录

### 优化方案

在 `project_paths.py` 中统一提供绝对路径版本：

```python
# core/utils/project_paths.py
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent  # 项目根目录

OUTPUT_DIR = PROJECT_ROOT / "output"
GENERATED_TESTS_DIR = PROJECT_ROOT / "midscene_run" / "generated"
# ...
```

然后 `conftest.py` 直接使用，不再重新赋值：
```python
from core.utils.project_paths import OUTPUT_DIR, GENERATED_TESTS_DIR
# 不需要再做 PROJECT_ROOT / OUTPUT_DIR 的操作
```

### 涉及文件

- `tests/conftest.py`
- `core/utils/project_paths.py`

---

## Issue 28：package.json 和 playwright.config.ts 放在 config/ 子目录，导致 npx 命令找不到配置

**标签**: `bug` `priority-high`

### 问题描述

`package.json` 和 `playwright.config.ts` 都放在 `config/` 子目录下，但 `TestExecutor` 在项目根目录执行 `npx playwright test`：

```python
# test_executor.py
result = subprocess.run(
    ["npx", "playwright", "test", script_path, ...],
    # 没有指定 cwd，默认在项目根目录执行
)
```

Playwright 默认在当前目录查找 `playwright.config.ts`，但配置文件在 `config/playwright.config.ts`，所以：
- 要么 Playwright 找不到配置文件，使用默认配置
- 要么需要每次都加 `--config config/playwright.config.ts` 参数

`package.json` 在 `config/` 目录也意味着 `node_modules` 会安装在 `config/node_modules/`，而不是项目根目录，导致 `npx` 找不到 `@midscene/web` 等包。

### 优化方案

将 `package.json`、`playwright.config.ts`、`tsconfig.json` 移到项目根目录（标准做法）：

```
项目根目录/
├── package.json           # 移到根目录
├── playwright.config.ts   # 移到根目录
├── tsconfig.json          # 移到根目录
├── node_modules/          # npm install 后在根目录
├── config/
│   ├── config.yaml        # 只保留 Python 配置
│   └── pytest.ini
```

同时在 `TestExecutor` 中明确指定配置文件路径：
```python
parts = ["npx", "playwright", "test", script_path,
         "--config", "playwright.config.ts", ...]
```

### 涉及文件

- `config/package.json` → 移到根目录
- `config/playwright.config.ts` → 移到根目录
- `config/tsconfig.json` → 移到根目录
- `core/automation/test_executor.py` — 更新配置文件路径

---

## Issue 29：README.md 中的环境变量说明与实际不符

**标签**: `documentation` `priority-low`

### 问题描述

`README.md` 中的配置说明有错误：

```markdown
# README.md 中写的
# ANTHROPIC_API_KEY=your_api_key_here  ← 错误！项目用的是 LLM_KEY

# 实际 .env.example 中的
LLM_KEY=your_api_key_here
```

README 还提到"支持OpenAI、阿里云百炼、智谱AI等"，但 `LLMConfig.validate_model()` 的已知模型列表里没有智谱AI的模型名称。

另外 README 的虚拟环境激活命令写的是 `venv\Scripts\activate`，但项目实际使用的是 `.venv`（所有文档和 skill 里都是 `.venv\Scripts\activate`）。

### 优化方案

统一更新 README：
- 修正环境变量名称
- 统一虚拟环境目录名（`.venv`）
- 补充智谱AI的模型名称到支持列表

### 涉及文件

- `README.md`

---

## Issue 30：tests/midscene.config.ts 放错了目录，且与 config/ 下的配置重复

**标签**: `tech-debt` `priority-low`

### 问题描述

`tests/midscene.config.ts` 放在 `tests/` 目录下，但它是 Midscene 的全局配置，不是测试文件：

```typescript
// tests/midscene.config.ts
export const midsceneConfig = {
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: process.env.OPENAI_BASE_URL,
  modelName: process.env.MIDSCENE_MODEL_NAME || 'gpt-4o',
};
```

同时 `core/models/config.py` 的 `ProjectSettings` 里也有 Midscene 相关配置：
```python
openai_api_key: Optional[str] = ...
openai_base_url: Optional[str] = ...
midscene_model_name: Optional[str] = ...
```

两套配置并存，实际生效的是哪个不清楚。

### 优化方案

删除 `tests/midscene.config.ts`，Midscene 的配置统一通过 `.env` 文件的环境变量管理（Midscene 本身支持直接读取 `OPENAI_API_KEY` 等环境变量，不需要额外的配置文件）。

### 涉及文件

- `tests/midscene.config.ts` — 删除
- `core/models/config.py` — 保留，作为唯一配置来源

---

## Issue 31：temp/ 目录和调试文件被提交到仓库

**标签**: `tech-debt` `priority-low`

### 问题描述

项目根目录有一个 `temp/` 目录，里面有调试文件：
```
temp/debug_output.txt
```

`output/playwright_debug.txt` 也是调试产物，不应该被提交。

`.gitignore` 没有忽略这些目录：
```gitignore
# 当前 .gitignore 缺少
temp/
output/
```

### 优化方案

更新 `.gitignore`：
```gitignore
# 运行时产物
temp/
output/
midscene_run/generated/
midscene_run/cache/
```

同时删除已提交的调试文件。

### 涉及文件

- `.gitignore`
- `temp/` — 删除目录
- `output/playwright_debug.txt` — 删除

---

## Issue 32：pytest.ini 的 testpaths 配置与实际测试目录不匹配

**标签**: `bug` `priority-medium`

### 问题描述

`config/pytest.ini` 中：

```ini
[pytest]
testpaths = tests   # 指向 tests/ 目录
```

但 `tests/unit/` 和 `tests/integration/` 目录是空的（没有任何测试文件），而生成的测试脚本在 `midscene_run/generated/`（TypeScript 文件，pytest 无法执行）。

同时 `pytest.ini` 放在 `config/` 子目录，但 pytest 默认在项目根目录查找 `pytest.ini`，需要每次用 `-c config/pytest.ini` 指定，否则配置不生效。

### 优化方案

将 `pytest.ini` 移到项目根目录，并更新 `testpaths`：

```ini
[pytest]
testpaths = tests/unit tests/integration
asyncio_mode = auto
```

### 涉及文件

- `config/pytest.ini` → 移到根目录

---

## Issue 33：workflow.py 中 optimize_test_cases_node 节点定义了但从未加入图

**标签**: `bug` `tech-debt` `priority-low`

### 问题描述

`workflow.py` 中定义了 `optimize_test_cases_node` 函数，但在 `build_workflow()` 中从未被添加到图中：

```python
# 定义了节点函数
def optimize_test_cases_node(state: AgentState) -> dict:
    """优化测试用例"""
    test_cases = state["test_cases"]
    optimized = []
    for tc in test_cases:
        if "priority" not in tc:
            tc["priority"] = "medium"
        optimized.append(tc)
    return {"test_cases": optimized}

# build_workflow() 中从未调用
workflow.add_node("analyze_requirements", analyze_requirements_node)
workflow.add_node("generate_test_cases", generate_test_cases_node)
workflow.add_node("review_test_cases", review_test_cases_node)
# optimize_test_cases_node 从未被 add_node ← 死代码
```

### 优化方案

二选一：
- 如果有用：在评审通过后、脚本生成前加入图中
- 如果没用：直接删除

### 涉及文件

- `core/agents/workflow.py`

---

## Issue 34：缺少 CI/CD 配置，无法自动化验证

**标签**: `enhancement` `priority-low`

### 问题描述

项目没有任何 CI/CD 配置（GitHub Actions、GitLab CI 等），导致：
- 每次提交无法自动运行单元测试
- 依赖安装是否正常无法自动验证
- 代码质量检查（lint、type check）需要手动执行

### 优化方案

添加 GitHub Actions 基础工作流：

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run unit tests
        run: python -m pytest tests/unit/ -v
      - name: Type check
        run: mypy core/ --ignore-missing-imports
      - name: Lint
        run: ruff check core/
```

### 涉及文件

- `.github/workflows/ci.yml` — 新建

---

## Issue 35：缺少类型检查配置（mypy/pyright）

**标签**: `enhancement` `code-quality` `priority-low`

### 问题描述

项目使用了大量类型注解和 Pydantic，但没有配置静态类型检查工具。现有代码中有几处类型问题：

```python
# workflow.py - Optional[List[dict]] 但实际存的是 Pydantic 模型
requirements: Optional[List[dict]]

# llm_client.py - 返回类型不精确
def chat(...) -> Union[str, ChatResponse]:  # 调用方不知道什么时候返回哪个

# case_reviewer.py - 类型注解与实现不一致
def review_all(self, requirements: List[Union[Dict, Requirement]], ...) -> Dict[str, Any]:
# 实际返回的是 ReviewAllResult.to_dict()，但注解写的是 Dict[str, Any]
```

### 优化方案

添加 `mypy.ini` 或在 `pyproject.toml` 中配置：

```ini
# mypy.ini
[mypy]
python_version = 3.11
strict = false
ignore_missing_imports = true
check_untyped_defs = true

[mypy-core.*]
disallow_untyped_defs = true
```

同时修复现有的类型不一致问题。

### 涉及文件

- `mypy.ini` — 新建
- `core/agents/workflow.py`
- `core/utils/llm_client.py`

---

## 优先级汇总（最终完整版）

| Issue | 标题 | 类型 | 难度 | 优先级 |
|-------|------|------|------|--------|
| #1 | 结构化输出替换手动 JSON 解析 | 重构 | 低 | P0 |
| #2 | 评审反馈注入生成器 | 功能 | 低 | P0 |
| #7 | LLMClient 重试机制和 Token 追踪 | 可靠性 | 低 | P0 |
| #8 | MidsceneScriptGenerator action 转换脆弱 | Bug | 中 | P0 |
| #9 | TestExecutor 改用 JSON reporter + 清理死代码 | Bug | 低 | P0 |
| #13 | 删除损坏的 requirement_analyzer_v2.py | Bug | 低 | P0 |
| #15 | TestCase.title 不合理的数字开头限制 | Bug | 低 | P0 |
| #17 | playwright.config.ts 重复字段和错误 baseURL | Bug | 低 | P0 |
| #24 | requirements.txt 缺少依赖且有未使用依赖 | Bug | 低 | P0 |
| #27 | conftest.py OUTPUT_DIR 变量遮蔽 | Bug | 低 | P0 |
| #28 | package.json 放错目录导致 npx 找不到配置 | Bug | 中 | P0 |
| #3 | 并行 Agent（fan-out） | 性能 | 中 | P1 |
| #4 | Tool Calling | 功能 | 高 | P1 |
| #5 | Human-in-the-loop | 功能 | 中 | P1 |
| #10 | 工作流可观测性（Tracing） | 可观测性 | 中 | P1 |
| #14 | ID 格式正则限制过严 | Bug | 低 | P1 |
| #16 | config.yaml 与 ProjectSettings 双重配置 | 重构 | 低 | P1 |
| #18 | markdown_parser 过于简单 | 功能 | 中 | P1 |
| #19 | AgentState 改用 Pydantic 模型 | 重构 | 中 | P1 |
| #20 | 缺少单元测试 | 测试 | 中 | P1 |
| #21 | 缺少日志系统 | 可观测性 | 低 | P1 |
| #25 | main.py 与 main_v2.py 并存职责不清 | 重构 | 低 | P1 |
| #26 | generate_allure_from_results.py 硬编码 | Bug | 低 | P1 |
| #32 | pytest.ini 放错目录且 testpaths 不匹配 | Bug | 低 | P1 |
| #6 | Agent 记忆与历史用例复用 | 功能 | 中 | P2 |
| #11 | main_v2.py 支持命令行参数 | 易用性 | 低 | P2 |
| #12 | 代理设置清除代码去重 | 重构 | 低 | P2 |
| #22 | AllureReporter HTTP 服务进程泄漏 | Bug | 低 | P2 |
| #23 | 需求文档示例太简单 | 文档 | 低 | P2 |
| #29 | README.md 环境变量说明错误 | 文档 | 低 | P2 |
| #30 | midscene.config.ts 放错目录且配置重复 | 重构 | 低 | P2 |
| #31 | temp/ 目录和调试文件被提交到仓库 | 清理 | 低 | P2 |
| #33 | optimize_test_cases_node 是死代码 | 清理 | 低 | P2 |
| #34 | 缺少 CI/CD 配置 | 工程化 | 中 | P2 |
| #35 | 缺少类型检查配置 | 代码质量 | 低 | P2 |

---

## Issue 36：.mcp.json 包含真实 GitHub Token，已泄露到 Git 仓库

**标签**: `security` `critical` `priority-critical`

### 问题描述

`.mcp.json` 文件包含了一个真实的 GitHub Personal Access Token，并且已经被提交到 Git 仓库：

```json
{
  "mcpServers": {
    "github": {
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "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"
      }
    }
  }
}
```

这是一个**严重的安全问题**：
- Token 已经暴露在公开仓库中（如果推送到 GitHub）
- 任何人都可以用这个 Token 访问你的 GitHub 账户
- Token 在 Git 历史中永久存在，即使删除文件也能找回

### 紧急处理步骤

**1. 立即撤销 Token：**
- 访问 GitHub Settings → Developer settings → Personal access tokens
- 找到这个 Token 并立即 Revoke（撤销）

**2. 从 Git 历史中彻底删除：**
```bash
# 使用 git-filter-repo 或 BFG Repo-Cleaner 清理历史
git filter-repo --path .mcp.json --invert-paths
# 或
bfg --delete-files .mcp.json
```

**3. 更新 .gitignore：**
```gitignore
# MCP 配置（包含敏感信息）
.mcp.json
```

**4. 创建模板文件：**
```json
// .mcp.json.example
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

**5. 从环境变量读取：**
```json
// .mcp.json（新版本，不提交到 Git）
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### 涉及文件

- `.mcp.json` — 立即删除并加入 .gitignore
- `.mcp.json.example` — 新建模板文件
- `.gitignore` — 添加 `.mcp.json`

---

## Issue 37：QUICKSTART.md 中的环境变量名称错误（ANTHROPIC_API_KEY）

**标签**: `documentation` `priority-high`

### 问题描述

`docs/QUICKSTART.md` 中的配置说明使用了错误的环境变量名：

```markdown
在 `.env` 文件中填入你的Claude API密钥：
ANTHROPIC_API_KEY=sk-ant-xxxxx  ← 错误！
```

但项目实际使用的是 `LLM_KEY`（在 `.env.example` 和 `config.py` 中定义）。

同时文档说"提示 'ANTHROPIC_API_KEY not found'"，但代码中从未检查这个变量名。

### 优化方案

统一更新为 `LLM_KEY`：
```markdown
在 `.env` 文件中填入你的 LLM API 密钥：
LLM_KEY=your_api_key_here
LLM_MODEL=gpt-3.5-turbo  # 或其他模型
```

### 涉及文件

- `docs/QUICKSTART.md`

---

## Issue 38：tests/ 目录有大量测试文件但从未在 CI 中运行

**标签**: `testing` `priority-medium`

### 问题描述

`tests/unit/` 和 `tests/integration/` 目录下有 15+ 个测试文件：

```
tests/unit/
├── test_analyzer_core.py
├── test_improved_analyzer.py
├── test_llm_client.py
├── test_llm_debug.py
├── test_llm.py
├── test_manual.py
├── test_pydantic_models.py
├── test_requirement_analyzer_improved.py
├── test_requirement_model_only.py
└── test_simple_pydantic.py

tests/integration/
├── test_allure_reporter.py
├── test_executor.py
├── test_main_flow.py
├── test_midscene_generator.py
└── test_workflow.py
```

但：
- 没有 CI 配置，这些测试从未自动运行
- 不知道哪些测试是通过的，哪些是失败的
- 测试文件命名混乱（`test_llm.py` vs `test_llm_debug.py` vs `test_llm_client.py`）
- 有些测试可能是临时调试文件（`test_manual.py`、`test_llm_debug.py`）

### 优化方案

**1. 清理测试文件：**
- 删除调试文件（`test_manual.py`、`test_llm_debug.py`）
- 合并重复测试（`test_llm.py` + `test_llm_client.py`）
- 重命名不清晰的文件（`test_improved_analyzer.py` → `test_requirement_analyzer_v2.py`）

**2. 运行所有测试验证状态：**
```bash
pytest tests/ -v --tb=short
```

**3. 修复失败的测试**

**4. 添加 CI 配置（见 Issue #34）**

### 涉及文件

- `tests/unit/` — 清理和重命名
- `tests/integration/` — 验证测试状态

---

## Issue 39：ProjectSettings.llm_api_key 默认值为空字符串，导致启动时不报错

**标签**: `bug` `priority-medium`

### 问题描述

`config.py` 中 `llm_api_key` 的默认值是空字符串：

```python
llm_api_key: str = Field(
    default="",  # ← 默认空字符串
    validation_alias=AliasChoices('llm_api_key', 'LLM_KEY'),
)
```

这导致：
- 用户忘记配置 `.env` 时，程序不会在启动时报错
- 直到第一次调用 LLM 时才会失败（浪费时间）
- `LLMConfig.validate_api_key()` 会检查空字符串，但 `ProjectSettings` 不会触发这个验证

### 优化方案

**方案 A**：移除默认值，强制用户配置：
```python
llm_api_key: str = Field(
    ...,  # 必填，无默认值
    validation_alias=AliasChoices('llm_api_key', 'LLM_KEY'),
)
```

**方案 B**：在 `get_settings()` 中检查：
```python
def get_settings() -> ProjectSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = ProjectSettings()
        # 启动时检查关键配置
        if not _settings_instance.llm_api_key:
            raise ValueError("LLM_KEY 未配置，请在 .env 文件中设置")
    return _settings_instance
```

### 涉及文件

- `core/models/config.py`

---

## Issue 40：LLMConfig 定义了 retry_attempts 和 retry_delay，但 LLMClient 从未使用

**标签**: `tech-debt` `priority-low`

### 问题描述

`LLMConfig` 模型中定义了重试相关字段：

```python
class LLMConfig(BaseModel):
    retry_attempts: int = Field(default=3, ...)
    retry_delay: float = Field(default=1.0, ...)
```

但 `LLMClient` 的 `__init__()` 中从未读取这两个字段：

```python
def __init__(self, api_key, model, base_url, temperature, max_tokens):
    # retry_attempts 和 retry_delay 从未被使用
    self.temperature = temperature
    self.max_tokens = max_tokens
    # 没有 self.retry_attempts = ...
```

而且 `LLMClient.chat()` 也没有实现重试逻辑（Issue #7 已提出）。

### 优化方案

在实现 Issue #7（重试机制）时，使用这两个配置字段。

### 涉及文件

- `core/models/config.py`
- `core/utils/llm_client.py`

---

## 最终优先级汇总

| Issue | 标题 | 类型 | 难度 | 优先级 |
|-------|------|------|------|--------|
| **#36** | **.mcp.json 包含真实 GitHub Token** | **安全** | **低** | **🔴 CRITICAL** |
| #1 | 结构化输出替换手动 JSON 解析 | 重构 | 低 | P0 |
| #2 | 评审反馈注入生成器 | 功能 | 低 | P0 |
| #7 | LLMClient 重试机制和 Token 追踪 | 可靠性 | 低 | P0 |
| #8 | MidsceneScriptGenerator action 转换脆弱 | Bug | 中 | P0 |
| #9 | TestExecutor 改用 JSON reporter + 清理死代码 | Bug | 低 | P0 |
| #13 | 删除损坏的 requirement_analyzer_v2.py | Bug | 低 | P0 |
| #15 | TestCase.title 不合理的数字开头限制 | Bug | 低 | P0 |
| #17 | playwright.config.ts 重复字段和错误 baseURL | Bug | 低 | P0 |
| #24 | requirements.txt 缺少依赖且有未使用依赖 | Bug | 低 | P0 |
| #27 | conftest.py OUTPUT_DIR 变量遮蔽 | Bug | 低 | P0 |
| #28 | package.json 放错目录导致 npx 找不到配置 | Bug | 中 | P0 |
| #37 | QUICKSTART.md 环境变量名称错误 | 文档 | 低 | P0 |
| #3 | 并行 Agent（fan-out） | 性能 | 中 | P1 |
| #4 | Tool Calling | 功能 | 高 | P1 |
| #5 | Human-in-the-loop | 功能 | 中 | P1 |
| #10 | 工作流可观测性（Tracing） | 可观测性 | 中 | P1 |
| #14 | ID 格式正则限制过严 | Bug | 低 | P1 |
| #16 | config.yaml 与 ProjectSettings 双重配置 | 重构 | 低 | P1 |
| #18 | markdown_parser 过于简单 | 功能 | 中 | P1 |
| #19 | AgentState 改用 Pydantic 模型 | 重构 | 中 | P1 |
| #20 | 缺少单元测试 | 测试 | 中 | P1 |
| #21 | 缺少日志系统 | 可观测性 | 低 | P1 |
| #25 | main.py 与 main_v2.py 并存职责不清 | 重构 | 低 | P1 |
| #26 | generate_allure_from_results.py 硬编码 | Bug | 低 | P1 |
| #32 | pytest.ini 放错目录且 testpaths 不匹配 | Bug | 低 | P1 |
| #38 | tests/ 有大量测试但从未在 CI 运行 | 测试 | 中 | P1 |
| #39 | llm_api_key 默认空字符串不报错 | Bug | 低 | P1 |
| #6 | Agent 记忆与历史用例复用 | 功能 | 中 | P2 |
| #11 | main_v2.py 支持命令行参数 | 易用性 | 低 | P2 |
| #12 | 代理设置清除代码去重 | 重构 | 低 | P2 |
| #22 | AllureReporter HTTP 服务进程泄漏 | Bug | 低 | P2 |
| #23 | 需求文档示例太简单 | 文档 | 低 | P2 |
| #29 | README.md 环境变量说明错误 | 文档 | 低 | P2 |
| #30 | midscene.config.ts 放错目录且配置重复 | 重构 | 低 | P2 |
| #31 | temp/ 目录和调试文件被提交到仓库 | 清理 | 低 | P2 |
| #33 | optimize_test_cases_node 是死代码 | 清理 | 低 | P2 |
| #34 | 缺少 CI/CD 配置 | 工程化 | 中 | P2 |
| #35 | 缺少类型检查配置 | 代码质量 | 低 | P2 |
| #40 | LLMConfig 定义了重试字段但未使用 | 技术债 | 低 | P2 |

---

## 总结

共发现 **40 个优化点**，分为：

- **🔴 CRITICAL（1个）**：安全问题，必须立即处理
- **P0（13个）**：严重 Bug 和缺失依赖，影响基本功能
- **P1（14个）**：重要功能增强和工程质量提升
- **P2（12个）**：易用性改进和代码清理

建议处理顺序：
1. **立即处理 #36**（撤销 GitHub Token）
2. **第一批（P0）**：修复 Bug，补全依赖，消除技术债
3. **第二批（P1）**：核心功能增强（Tool Calling、并行、可观测性）
4. **第三批（P2）**：易用性和文档完善

---

## Issue 41：test_workflow.py 的 import 路径是旧路径，运行时直接报错

**标签**: `bug` `priority-high`

### 问题描述

`tests/integration/test_workflow.py` 使用了重构前的旧导入路径：

```python
# 错误的旧路径（缺少 core. 前缀）
from agents.workflow import (       # ❌ 应该是 core.agents.workflow
    AgentState,
    analyze_requirements_node,
    ...
)
```

同时 Mock 的路径也是错的：
```python
@patch("agents.workflow.RequirementAnalyzer")   # ❌
@patch("agents.workflow.TestCaseGenerator")     # ❌
# 应该是
@patch("core.agents.workflow.RequirementAnalyzer")
@patch("core.agents.workflow.TestCaseGenerator")
```

这意味着这个集成测试文件**从来没有成功运行过**。

### 涉及文件

- `tests/integration/test_workflow.py`

---

## Issue 42：test_analyzer_core.py 不是标准 pytest 测试，无法被 pytest 自动发现

**标签**: `bug` `testing` `priority-medium`

### 问题描述

`tests/unit/test_analyzer_core.py` 的测试函数不符合 pytest 规范：

```python
# 当前：自定义测试框架，pytest 无法识别
def test_core_functionality():
    # 用 print 输出，用 return True/False 表示结果
    print("✅ 返回类型: ...")
    return True  # ← pytest 不看返回值

def test_error_handling():
    return True

# 入口是 if __name__ == "__main__"，不是 pytest 的方式
if __name__ == "__main__":
    for test_name, test_func in tests:
        if test_func():  # ← pytest 不这样调用
            passed += 1
```

pytest 运行时会发现这些函数，但因为没有 `assert` 语句，所有测试都会"通过"（即使逻辑是错的）。

### 优化方案

改写为标准 pytest 格式：

```python
import pytest
from core.models.requirement import Requirement, RequirementAnalysisResult

class TestRequirementAnalyzerCore:

    def test_analyze_structured_returns_pydantic_model(self):
        analyzer = RequirementAnalyzerCore()
        result = analyzer.analyze_structured(VALID_REQUIREMENT)
        assert isinstance(result, RequirementAnalysisResult)
        assert result.total_count == 1

    def test_analyze_raises_on_empty_input(self):
        analyzer = RequirementAnalyzerCore()
        with pytest.raises(ValueError, match="至少需要10个字符"):
            analyzer.analyze_structured("")

    def test_extract_json_from_markdown_block(self):
        analyzer = RequirementAnalyzerCore()
        content = '```json\n{"key": "value"}\n```'
        result = analyzer._extract_json(content)
        assert result == {"key": "value"}
```

### 涉及文件

- `tests/unit/test_analyzer_core.py`
- `tests/unit/` 下其他类似文件

---

## Issue 43：PHASE3_DESIGN.md 中的设计与实际实现已严重偏离

**标签**: `documentation` `priority-low`

### 问题描述

`docs/PHASE3_DESIGN.md` 是阶段3的设计文档，但实际实现与设计有多处不符：

**1. 设计中的模块结构：**
```
automation/
├── script_generator.py      # 设计中保留
├── midscene_generator.py    # 设计中新增
├── element_locator.py       # 设计中新增，实际未实现
└── test_executor.py         # 设计中新增
```
实际上 `element_locator.py` 从未被创建，`script_generator.py` 也不存在（被 `midscene_generator.py` 替代）。

**2. 设计中的 AgentState 扩展：**
```python
# 设计文档中
class AgentState(TypedDict):
    generated_scripts: List[str]   # 设计是列表
    execution_results: List[Dict]  # 设计是列表
```
实际实现：
```python
generated_script: Optional[str]   # 实际是单个字符串
execution_results: Optional[dict] # 实际是单个字典
```

**3. 设计中的 Midscene API：**
```typescript
// 设计文档中
const midscene = new Midscene(page);
await midscene.ai('...');
```
实际生成的脚本使用：
```typescript
// 实际实现
const test = base.extend<{ai: any}>(PlaywrightAiFixture());
await ai('...');
```

### 优化方案

更新设计文档使其与实际实现一致，或者在文档顶部标注"此文档为历史设计，实际实现见代码"。

### 涉及文件

- `docs/PHASE3_DESIGN.md`

---

## Issue 44：LLMConfig.validate_model() 在初始化时打印警告，污染测试输出

**标签**: `code-quality` `priority-low`

### 问题描述

`LLMConfig.validate_model()` 在验证时直接 `print()` 警告：

```python
@field_validator('model')
@classmethod
def validate_model(cls, v):
    valid_models = ["gpt-4", "qwen-plus", ...]
    if v not in valid_models:
        print(f"警告: 使用了未知的模型名称 '{v}'，请确保该模型可用")  # ← 污染输出
    return v
```

这导致：
- 每次创建 `LLMConfig` 实例都会打印到 stdout
- 运行测试时输出被污染
- 使用自定义模型名（如 `qwen-max-latest`）时每次都有警告

### 优化方案

改用 Python 标准 `warnings` 模块或 logging：

```python
import warnings

@field_validator('model')
@classmethod
def validate_model(cls, v):
    known_models = [...]
    if v not in known_models:
        warnings.warn(
            f"未知模型名称 '{v}'，请确保该模型可用",
            UserWarning,
            stacklevel=2
        )
    return v
```

### 涉及文件

- `core/models/config.py`

---

## Issue 45：缺少 pyproject.toml，项目元数据分散在多个文件

**标签**: `enhancement` `code-quality` `priority-low`

### 问题描述

现代 Python 项目应该使用 `pyproject.toml` 统一管理项目元数据，但当前项目：
- 没有 `pyproject.toml`
- 项目名称、版本在 `config/config.yaml` 里
- pytest 配置在 `config/pytest.ini` 里（放错目录）
- 没有 `setup.py` 或 `setup.cfg`
- 无法用 `pip install -e .` 安装为可编辑包

这导致 `sys.path.append(...)` 这样的 hack 出现在测试文件中：
```python
# tests/unit/test_analyzer_core.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ← 不应该这样做
```

### 优化方案

创建 `pyproject.toml`：

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "ai-test-platform"
version = "0.1.0"
description = "AI 驱动的端到端测试自动化平台"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests/unit", "tests/integration"]
asyncio_mode = "auto"
addopts = "-v --tb=short"

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true

[tool.ruff]
line-length = 100
target-version = "py311"
```

然后在项目根目录运行 `pip install -e .`，所有 `sys.path` hack 都可以删除。

### 涉及文件

- `pyproject.toml` — 新建
- `config/pytest.ini` — 内容迁移到 pyproject.toml 后删除
- `tests/unit/test_analyzer_core.py` — 删除 sys.path hack

---

## 最终完整汇总（共 45 个 Issue）

| Issue | 标题 | 类型 | 优先级 |
|-------|------|------|--------|
| **#36** | **.mcp.json 包含真实 GitHub Token** | 安全 | **🔴 CRITICAL** |
| #1 | 结构化输出替换手动 JSON 解析 | 重构 | P0 |
| #2 | 评审反馈注入生成器 | 功能 | P0 |
| #7 | LLMClient 重试机制和 Token 追踪 | 可靠性 | P0 |
| #8 | MidsceneScriptGenerator action 转换脆弱 | Bug | P0 |
| #9 | TestExecutor 改用 JSON reporter + 清理死代码 | Bug | P0 |
| #13 | 删除损坏的 requirement_analyzer_v2.py | Bug | P0 |
| #15 | TestCase.title 不合理的数字开头限制 | Bug | P0 |
| #17 | playwright.config.ts 重复字段和错误 baseURL | Bug | P0 |
| #24 | requirements.txt 缺少依赖且有未使用依赖 | Bug | P0 |
| #27 | conftest.py OUTPUT_DIR 变量遮蔽 | Bug | P0 |
| #28 | package.json 放错目录导致 npx 找不到配置 | Bug | P0 |
| #37 | QUICKSTART.md 环境变量名称错误 | 文档 | P0 |
| #41 | test_workflow.py import 路径是旧路径 | Bug | P0 |
| #3 | 并行 Agent（fan-out） | 性能 | P1 |
| #4 | Tool Calling | 功能 | P1 |
| #5 | Human-in-the-loop | 功能 | P1 |
| #10 | 工作流可观测性（Tracing） | 可观测性 | P1 |
| #14 | ID 格式正则限制过严 | Bug | P1 |
| #16 | config.yaml 与 ProjectSettings 双重配置 | 重构 | P1 |
| #18 | markdown_parser 过于简单 | 功能 | P1 |
| #19 | AgentState 改用 Pydantic 模型 | 重构 | P1 |
| #20 | 缺少单元测试 | 测试 | P1 |
| #21 | 缺少日志系统 | 可观测性 | P1 |
| #25 | main.py 与 main_v2.py 并存职责不清 | 重构 | P1 |
| #26 | generate_allure_from_results.py 硬编码 | Bug | P1 |
| #32 | pytest.ini 放错目录且 testpaths 不匹配 | Bug | P1 |
| #38 | tests/ 有大量测试但从未在 CI 运行 | 测试 | P1 |
| #39 | llm_api_key 默认空字符串不报错 | Bug | P1 |
| #42 | test_analyzer_core.py 不是标准 pytest 格式 | Bug | P1 |
| #6 | Agent 记忆与历史用例复用 | 功能 | P2 |
| #11 | main_v2.py 支持命令行参数 | 易用性 | P2 |
| #12 | 代理设置清除代码去重 | 重构 | P2 |
| #22 | AllureReporter HTTP 服务进程泄漏 | Bug | P2 |
| #23 | 需求文档示例太简单 | 文档 | P2 |
| #29 | README.md 环境变量说明错误 | 文档 | P2 |
| #30 | midscene.config.ts 放错目录且配置重复 | 重构 | P2 |
| #31 | temp/ 目录和调试文件被提交到仓库 | 清理 | P2 |
| #33 | optimize_test_cases_node 是死代码 | 清理 | P2 |
| #34 | 缺少 CI/CD 配置 | 工程化 | P2 |
| #35 | 缺少类型检查配置 | 代码质量 | P2 |
| #40 | LLMConfig 定义了重试字段但未使用 | 技术债 | P2 |
| #43 | PHASE3_DESIGN.md 与实际实现严重偏离 | 文档 | P2 |
| #44 | LLMConfig.validate_model() 污染测试输出 | 代码质量 | P2 |
| #45 | 缺少 pyproject.toml，项目元数据分散 | 工程化 | P2 |


---

## 🟢 #1: Kiro的skill缺乏description导致无法正常触发skill

- **状态**: open
- **标签**: 无标签
- **创建时间**: 2026-04-20
- **链接**: [https://github.com/LittleParis/AgentTestingHelper/issues/1](https://github.com/LittleParis/AgentTestingHelper/issues/1)

### 描述

无描述

---

