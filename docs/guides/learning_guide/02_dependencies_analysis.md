# 依赖分析 - 理解每个库的作用

## Python依赖 (requirements.txt)

### AI和LLM相关
```python
# LangChain - LLM应用开发框架
langchain==0.3.13           # 核心框架
langchain-community==0.3.13 # 社区扩展
langchain-core==0.3.28      # 核心组件
langchain-openai==0.2.14    # OpenAI集成

# OpenAI - LLM API客户端
openai==1.12.0              # 官方Python SDK
```

### 测试自动化相关
```python
# Playwright - 浏览器自动化
playwright==1.48.0          # 核心库
pytest-playwright==0.5.2    # Pytest集成

# Pytest - 测试框架
pytest==8.3.4               # 核心测试框架
pytest-asyncio==0.24.0      # 异步测试支持

# Allure - 测试报告
allure-pytest==2.13.5       # Pytest插件
```

### 文档处理相关
```python
# 文档解析
PyMuPDF==1.24.0            # PDF解析
python-docx==1.1.0         # Word文档解析
markdown==3.7               # Markdown解析
```

### 工具库
```python
# 数据处理和配置
pydantic==2.10.3           # 数据验证
python-dotenv==1.0.1       # 环境变量管理
pyyaml==6.0.2              # YAML配置文件
```

## Node.js依赖 (package.json)

### 测试执行相关
```json
{
  "@playwright/test": "^1.48.0",    // Playwright测试框架
  "playwright": "^1.48.0",          // Playwright核心
  "@midscene/web": "^0.15.0"        // AI视觉定位库
}
```

### 开发工具
```json
{
  "typescript": "^5.6.0",           // TypeScript编译器
  "@types/node": "^22.0.0",         // Node.js类型定义
  "allure-playwright": "^3.7.1",    // Allure报告插件
  "dotenv": "^17.4.1"               // 环境变量支持
}
```

## 学习重点

1. **LangChain**: 理解如何用它调用LLM
2. **Playwright**: 理解浏览器自动化原理
3. **Midscene**: 理解AI视觉定位概念
4. **Allure**: 理解测试报告生成