# Issue #4: 前端设计方案

| 属性 | 值 |
|------|-----|
| 状态 | 🟢 open |
| 标签 | 无标签 |
| 创建时间 | 2026-04-20 |
| 更新时间 | 2026-04-20 |
| 关闭时间 | 未关闭 |
| 评论数 | 0 |
| 链接 | [https://github.com/LittleParis/AgentTestingHelper/issues/4](https://github.com/LittleParis/AgentTestingHelper/issues/4) |

---

## 内容

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

