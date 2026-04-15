# 环境搭建指南

## 1. Python环境
```bash
# 检查Python版本 (需要3.10+)
python --version

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 安装Python依赖
pip install -r requirements.txt
```

## 2. Node.js环境
```bash
# 检查Node.js版本
node --version
npm --version

# 安装Node.js依赖
npm install

# 安装Playwright浏览器
npx playwright install chromium
```

## 3. 配置文件
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入API密钥
# 如果没有API密钥，可以先跳过，学习代码结构
```

## 4. 验证安装
```bash
# 检查关键依赖
pip list | grep -E "langchain|playwright|pytest"
npm list --depth=0
```