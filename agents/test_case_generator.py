"""测试用例生成Agent - 阶段1简化版本"""
import json
import os
from typing import Dict, Any, List
from anthropic import Anthropic


class TestCaseGenerator:
    """测试用例生成Agent"""
    
    def __init__(self, api_key: str = None):
        """
        初始化测试用例生成Agent
        
        Args:
            api_key: Anthropic API密钥
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def generate(self, requirement: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        基于需求生成测试用例
        
        Args:
            requirement: 结构化需求
            
        Returns:
            测试用例列表
        """
        prompt = self._build_prompt(requirement)
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        content = response.content[0].text
        
        try:
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                json_str = content
            
            result = json.loads(json_str)
            return result.get("test_cases", [])
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"原始响应: {content}")
            raise
    
    def _build_prompt(self, requirement: Dict[str, Any]) -> str:
        """构建生成prompt"""
        req_json = json.dumps(requirement, ensure_ascii=False, indent=2)
        
        return f"""
你是一个资深测试工程师。基于以下需求，生成测试用例。

需求信息：
{req_json}

输出格式（JSON）：
```json
{{
  "test_cases": [
    {{
      "id": "TC_001",
      "requirement_id": "REQ_001",
      "title": "测试用例标题",
      "priority": "high",
      "type": "functional",
      "steps": [
        {{
          "step_number": 1,
          "action": "操作描述（用自然语言）",
          "data": "测试数据",
          "expected": "预期结果"
        }}
      ],
      "expected": "最终预期结果",
      "tags": ["smoke"]
    }}
  ]
}}
```

要求：
1. 步骤描述清晰，适合UI自动化
2. 包含正向和负向测试
3. 每个用例独立可执行
4. 至少生成2-3个测试用例
"""
