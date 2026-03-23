# 阿里云百炼配置指南

## 获取API密钥

1. 访问 [阿里云百炼控制台](https://bailian.console.aliyun.com/)
2. 点击右上角头像 → API-KEY管理
3. 创建新的API-KEY并复制

## 模型选择建议

### 推荐：qwen-coder-plus（通义千问编程版）
- **优势**：代码生成能力强，JSON输出稳定
- **适用**：测试用例生成、脚本生成
- **价格**：约 ¥0.004/1K tokens（输入）

### 备选：glm-4（智谱GLM）
- **优势**：通用能力均衡
- **适用**：需求分析、对话场景
- **价格**：约 ¥0.005/1K tokens（输入）

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
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx
LLM_MODEL=qwen-coder-plus
```

### 3. 测试连接
```bash
python test_llm.py
```

## 模型对比

| 特性 | qwen-coder-plus | glm-4 |
|------|----------------|-------|
| 代码生成 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| JSON输出 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 中文理解 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 推理能力 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 价格 | 较低 | 中等 |

## 切换模型

只需修改 `.env` 文件：
```env
# 使用通义千问
LLM_MODEL=qwen-coder-plus

# 或使用GLM
LLM_MODEL=glm-4
```

## 常见问题

### Q: 提示 "Invalid API key"
A: 检查 `DASHSCOPE_API_KEY` 是否正确复制

### Q: 提示 "Model not found"
A: 确认你的百炼账号已开通对应模型权限

### Q: 生成的JSON格式不对
A: qwen-coder-plus 的JSON输出更稳定，建议使用

### Q: 想要更便宜的方案
A: 可以使用 `qwen-plus`（通用版），价格更低但代码能力稍弱

## 成本估算

以一个中等需求文档为例：
- 需求分析：约 2K tokens 输入 + 1K tokens 输出 = ¥0.01
- 生成3个测试用例：约 3K tokens 输入 + 2K tokens 输出 = ¥0.02
- **单次完整流程成本：约 ¥0.03**

每月100次运行 ≈ ¥3

## 性能优化建议

1. **使用缓存**：相同需求不重复调用
2. **批量处理**：一次生成多个测试用例
3. **Prompt优化**：减少不必要的输出
4. **选择合适模型**：简单任务用 qwen-plus

## 下一步

配置完成后，运行：
```bash
python main.py
```

开始你的AI测试自动化之旅！
