"""需求分析Agent - 阶段1简化版本"""
import json
import os
from typing import Dict, Any
from utils.llm_client import get_llm_client


class RequirementAnalyzer:
    """需求分析Agent"""
    
    def __init__(self):
        """初始化需求分析Agent"""
        self.llm = get_llm_client()
    
    def analyze(self, requirement_text: str) -> Dict[str, Any]:
        """
        分析需求文档
        
        Args:
            requirement_text: 需求文档内容
            
        Returns:
            结构化的需求JSON
        """
        prompt = self._build_prompt(requirement_text)
        
        # 调用LLM
        content = self.llm.chat_simple(prompt, temperature=0.7, max_tokens=4096)
        
        # 尝试解析JSON
        try:
            # 查找JSON代码块
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                json_str = content
            
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"原始响应: {content}")
            raise
    
    def _build_prompt(self, requirement_text: str) -> str:
        """构建分析prompt"""
        return f"""
你是一个专业的需求分析专家。请分析以下需求文档，提取关键信息。

需求文档内容：
{requirement_text}

请按以下JSON格式输出：
```json
{{
  "requirements": [
    {{
      "id": "REQ_001",
      "title": "需求标题",
      "description": "详细描述",
      "priority": "high",
      "type": "functional",
      "acceptance_criteria": ["验收标准1", "验收标准2"],
      "ui_elements": ["涉及的UI元素"]
    }}
  ],
  "summary": "需求概述"
}}
```

分析要点：
1. 识别所有功能点
2. 提取验收标准（用于生成测试用例）
3. 标注优先级
4. 识别UI交互元素
"""
