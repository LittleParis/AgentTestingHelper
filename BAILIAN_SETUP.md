# LLM 配置指南

## 获取 API 密钥

根据你使用的 LLM 服务商获取 API 密钥：

- **OpenAI**: https://platform.openai.com/api-keys
- **阿里云百炼**: https://bailian.console.aliyun.com/
- **智谱 AI**: https://open.bigmodel.cn/
- **其他**: 参考对应服务商文档

## 配置步骤

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
# 复制模板
copy .env.example .env

# 编辑.env文件
notepad .env
```

在 `.env` 中填入：
```env
LLM_KEY=your_api_key_here
LLM_MODEL=your_model_name
LLM_BASE_URL=https://api.example.com/v1  # 可选，自定义 API 端点
```

### 3. 测试连接
```bash
python test_llm.py
```

## 常见 LLM 服务商配置示例

### OpenAI
```env
LLM_KEY=sk-xxxxxxxx
LLM_MODEL=gpt-4
# LLM_BASE_URL 不需要设置
```

### 阿里云百炼
```env
LLM_KEY=sk-xxxxxxxx
LLM_MODEL=qwen-coder-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 智谱 AI
```env
LLM_KEY=xxxxxxxx
LLM_MODEL=glm-4
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
```

## 常见问题

### Q: 提示 "Invalid API key"
A: 检查 `LLM_KEY` 是否正确复制

### Q: 提示 "Model not found"
A: 确认模型名称是否正确，不同服务商的模型命名不同

### Q: 连接超时
A: 检查网络连接，部分服务商可能需要代理

## 下一步

配置完成后，运行：
```bash
python main.py
```

开始你的 AI 测试自动化之旅！
