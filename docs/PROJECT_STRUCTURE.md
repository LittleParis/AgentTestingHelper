# 项目结构整理计划

## 当前问题

1. **测试文件散乱** - 根目录有很多 `test_*.py` 文件
2. **重复目录** - 有多个 venv 目录 (`venv/`, `.venv/`)
3. **临时文件** - 调试文件和临时输出文件
4. **文档分散** - 文档分布在多个目录中

## 目标结构

```
AI测试自动化平台/
├── 📁 core/                    # 核心模块
│   ├── agents/                 # Agent模块
│   ├── models/                 # 数据模型
│   ├── parsers/               # 文档解析
│   ├── automation/            # 自动化执行
│   └── utils/                 # 工具模块
├── 📁 tests/                   # 测试目录
│   ├── unit/                  # 单元测试
│   ├── integration/           # 集成测试
│   ├── fixtures/              # 测试数据
│   └── generated/             # 生成的测试脚本
├── 📁 docs/                    # 文档目录
│   ├── guides/                # 学习指南
│   ├── improvements/          # 改进建议
│   └── api/                   # API文档
├── 📁 examples/               # 示例文件
├── 📁 output/                 # 输出目录
├── 📁 config/                 # 配置文件
├── 📁 scripts/                # 脚本工具
└── 📁 temp/                   # 临时文件
```

## 整理步骤

1. 创建新的目录结构
2. 移动核心模块到 `core/`
3. 整理测试文件到 `tests/`
4. 合并文档到 `docs/`
5. 清理临时文件
6. 更新导入路径