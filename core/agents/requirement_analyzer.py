"""需求分析Agent - 改进版本（集成Pydantic）"""
import json
import os
from typing import Dict, Any, Optional
from pydantic import ValidationError

from core.utils.llm_client import get_llm_client
from core.models.requirement import Requirement, RequirementAnalysisResult, RequirementType, Priority


class RequirementAnalyzer:
    """需求分析Agent - 改进版本"""
    
    def __init__(self):
        """初始化需求分析Agent"""
        self.llm = get_llm_client()
    
    def analyze(self, requirement_text: str) -> Dict[str, Any]:
        """
        分析需求文档（向后兼容接口）
        
        Args:
            requirement_text: 需求文档内容
            
        Returns:
            结构化的需求JSON（字典格式）
        """
        # 调用新的Pydantic版本
        result = self.analyze_structured(requirement_text)
        
        # 转换为字典格式保持兼容性
        return result.to_dict()
    
    def analyze_structured(self, requirement_text: str) -> RequirementAnalysisResult:
        """
        分析需求文档（新版本，返回Pydantic模型）
        
        Args:
            requirement_text: 需求文档内容
            
        Returns:
            RequirementAnalysisResult: 结构化的需求分析结果
            
        Raises:
            ValueError: 当输入参数无效时
            ValidationError: 当LLM输出不符合预期格式时
        """
        if not requirement_text or len(requirement_text.strip()) < 10:
            raise ValueError("需求文档内容太短，至少需要10个字符")
        
        prompt = self._build_prompt(requirement_text)
        
        try:
            # 调用LLM
            content = self.llm.chat_simple(prompt, temperature=0.7, max_tokens=4096)
            
            # 解析JSON响应
            json_data = self._extract_json(content)
            
            # 使用Pydantic验证和解析
            result = self._parse_llm_response(json_data)
            
            return result
            
        except ValidationError as e:
            print(f"[RequirementAnalyzer] 数据验证失败: {e}")
            # 降级到简单解析
            return self._fallback_parse(json_data)
        except json.JSONDecodeError as e:
            print(f"[RequirementAnalyzer] JSON解析失败: {e}")
            print(f"原始响应: {content}")
            raise
        except Exception as e:
            print(f"[RequirementAnalyzer] 分析失败: {e}")
            raise
    
    def _build_prompt(self, requirement_text: str) -> str:
        """构建分析prompt"""
        return f"""你是一个专业的需求分析专家。请分析以下需求文档，提取关键信息。

需求文档内容：
{requirement_text}

请按以下JSON格式输出，严格遵循数据结构：

```json
{{
  "requirements": [
    {{
      "id": "REQ_001",
      "title": "需求标题",
      "description": "详细描述",
      "priority": "high|medium|low",
      "type": "functional|non_functional|business|technical",
      "acceptance_criteria": ["验收标准1", "验收标准2"],
      "ui_elements": ["涉及的UI元素"]
    }}
  ],
  "summary": "需求概述",
  "total_count": 1
}}
```

分析要点：
1. **需求ID**: 必须使用 REQ_001, REQ_002 格式
2. **优先级**: 只能是 high, medium, low 之一
3. **类型**: 只能是 functional, non_functional, business, technical 之一
4. **验收标准**: 每个标准至少5个字符，用于生成测试用例
5. **UI元素**: 识别页面交互元素，用于UI自动化
6. **总数**: total_count 必须等于 requirements 数组长度

输出要求：
- 严格按照JSON格式输出
- 确保所有必填字段都有值
- 验收标准至少包含1个，每个至少5个字符
- 需求描述至少10个字符
- 需求标题1-200个字符

请直接输出JSON，不要有其他内容。"""

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """从LLM响应中提取JSON"""
        content = content.strip()
        
        # 尝试从markdown代码块中提取
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()
        
        # 解析JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试修复常见的JSON格式问题
            content = self._fix_json_format(content)
            return json.loads(content)
    
    def _fix_json_format(self, content: str) -> str:
        """修复常见的JSON格式问题"""
        # 移除可能的前后缀
        content = content.strip()
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        
        # 移除可能的语言标识
        if content.startswith('json'):
            content = content[4:]
        
        # 确保以 { 开头，} 结尾
        content = content.strip()
        if not content.startswith('{'):
            # 查找第一个 {
            start = content.find('{')
            if start != -1:
                content = content[start:]
        
        if not content.endswith('}'):
            # 查找最后一个 }
            end = content.rfind('}')
            if end != -1:
                content = content[:end+1]
        
        return content
    
    def _parse_llm_response(self, json_data: Dict[str, Any]) -> RequirementAnalysisResult:
        """使用Pydantic解析LLM响应"""
        try:
            # 首先解析需求列表
            requirements = []
            raw_requirements = json_data.get("requirements", [])
            
            for i, req_data in enumerate(raw_requirements):
                try:
                    # 确保ID格式正确
                    if "id" not in req_data:
                        req_data["id"] = f"REQ_{i+1:03d}"
                    
                    # 验证和创建需求对象
                    requirement = Requirement(**req_data)
                    requirements.append(requirement)
                    
                except ValidationError as e:
                    print(f"[RequirementAnalyzer] 需求 {i+1} 验证失败: {e}")
                    # 尝试修复常见问题
                    fixed_req = self._fix_requirement_data(req_data, i+1)
                    if fixed_req:
                        requirements.append(fixed_req)
            
            # 创建分析结果
            result_data = {
                "requirements": requirements,
                "summary": json_data.get("summary", "需求分析完成"),
                "total_count": len(requirements)
            }
            
            return RequirementAnalysisResult(**result_data)
            
        except ValidationError as e:
            print(f"[RequirementAnalyzer] 结果验证失败: {e}")
            raise
    
    def _fix_requirement_data(self, req_data: dict, index: int) -> Optional[Requirement]:
        """尝试修复需求数据"""
        try:
            # 修复常见问题
            fixed_data = req_data.copy()
            
            # 确保ID格式
            if "id" not in fixed_data or not fixed_data["id"]:
                fixed_data["id"] = f"REQ_{index:03d}"
            
            # 确保标题存在
            if "title" not in fixed_data or not fixed_data["title"]:
                fixed_data["title"] = f"需求 {index}"
            
            # 确保描述存在且足够长
            if "description" not in fixed_data or len(fixed_data["description"]) < 10:
                fixed_data["description"] = f"这是第 {index} 个需求的详细描述"
            
            # 确保验收标准存在
            if "acceptance_criteria" not in fixed_data or not fixed_data["acceptance_criteria"]:
                fixed_data["acceptance_criteria"] = ["基本功能正常工作"]
            
            # 验证优先级
            if "priority" not in fixed_data or fixed_data["priority"] not in ["high", "medium", "low"]:
                fixed_data["priority"] = "medium"
            
            # 验证类型
            if "type" not in fixed_data or fixed_data["type"] not in ["functional", "non_functional", "business", "technical"]:
                fixed_data["type"] = "functional"
            
            return Requirement(**fixed_data)
            
        except Exception as e:
            print(f"[RequirementAnalyzer] 无法修复需求数据: {e}")
            return None
    
    def _fallback_parse(self, json_data: Dict[str, Any]) -> RequirementAnalysisResult:
        """降级解析方案（当Pydantic验证失败时）"""
        print("[RequirementAnalyzer] 使用降级解析方案")
        
        try:
            # 简单的数据清理和默认值设置
            requirements = []
            raw_requirements = json_data.get("requirements", [])
            
            for i, req_data in enumerate(raw_requirements):
                # 创建最基本的需求对象
                requirement = Requirement(
                    id=req_data.get("id", f"REQ_{i+1:03d}"),
                    title=req_data.get("title", f"需求 {i+1}"),
                    description=req_data.get("description", "需求描述"),
                    priority=Priority.MEDIUM,
                    type=RequirementType.FUNCTIONAL,
                    acceptance_criteria=req_data.get("acceptance_criteria", ["基本功能正常"]),
                    ui_elements=req_data.get("ui_elements", [])
                )
                requirements.append(requirement)
            
            return RequirementAnalysisResult(
                requirements=requirements,
                summary=json_data.get("summary", "需求分析完成（降级模式）"),
                total_count=len(requirements)
            )
            
        except Exception as e:
            print(f"[RequirementAnalyzer] 降级解析也失败: {e}")
            # 返回空结果
            return RequirementAnalysisResult(
                requirements=[],
                summary="需求分析失败",
                total_count=0
            )
    
    
    def _build_prompt(self, requirement_text: str) -> str:
        """构建分析prompt"""
        return f"""你是一个专业的需求分析专家。请分析以下需求文档，提取关键信息。

需求文档内容：
{requirement_text}

请按以下JSON格式输出，严格遵循数据结构：

```json
{{
  "requirements": [
    {{
      "id": "REQ_001",
      "title": "需求标题",
      "description": "详细描述",
      "priority": "high|medium|low",
      "type": "functional|non_functional|business|technical",
      "acceptance_criteria": ["验收标准1", "验收标准2"],
      "ui_elements": ["涉及的UI元素"]
    }}
  ],
  "summary": "需求概述",
  "total_count": 1
}}
```

分析要点：
1. **需求ID**: 必须使用 REQ_001, REQ_002 格式
2. **优先级**: 只能是 high, medium, low 之一
3. **类型**: 只能是 functional, non_functional, business, technical 之一
4. **验收标准**: 每个标准至少5个字符，用于生成测试用例
5. **UI元素**: 识别页面交互元素，用于UI自动化
6. **总数**: total_count 必须等于 requirements 数组长度

输出要求：
- 严格按照JSON格式输出
- 确保所有必填字段都有值
- 验收标准至少包含1个，每个至少5个字符
- 需求描述至少10个字符
- 需求标题1-200个字符

请直接输出JSON，不要有其他内容。"""

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """从LLM响应中提取JSON"""
        content = content.strip()
        
        # 尝试从markdown代码块中提取
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()
        
        # 解析JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试修复常见的JSON格式问题
            content = self._fix_json_format(content)
            return json.loads(content)
    
    def _fix_json_format(self, content: str) -> str:
        """修复常见的JSON格式问题"""
        # 移除可能的前后缀
        content = content.strip()
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        
        # 移除可能的语言标识
        if content.startswith('json'):
            content = content[4:]
        
        # 确保以 { 开头，} 结尾
        content = content.strip()
        if not content.startswith('{'):
            # 查找第一个 {
            start = content.find('{')
            if start != -1:
                content = content[start:]
        
        if not content.endswith('}'):
            # 查找最后一个 }
            end = content.rfind('}')
            if end != -1:
                content = content[:end+1]
        
        return content
    
    def _parse_llm_response(self, json_data: Dict[str, Any]) -> RequirementAnalysisResult:
        """使用Pydantic解析LLM响应"""
        try:
            # 首先解析需求列表
            requirements = []
            raw_requirements = json_data.get("requirements", [])
            
            for i, req_data in enumerate(raw_requirements):
                try:
                    # 确保ID格式正确
                    if "id" not in req_data:
                        req_data["id"] = f"REQ_{i+1:03d}"
                    
                    # 验证和创建需求对象
                    requirement = Requirement(**req_data)
                    requirements.append(requirement)
                    
                except ValidationError as e:
                    print(f"[RequirementAnalyzer] 需求 {i+1} 验证失败: {e}")
                    # 尝试修复常见问题
                    fixed_req = self._fix_requirement_data(req_data, i+1)
                    if fixed_req:
                        requirements.append(fixed_req)
            
            # 创建分析结果
            result_data = {
                "requirements": requirements,
                "summary": json_data.get("summary", "需求分析完成"),
                "total_count": len(requirements)
            }
            
            return RequirementAnalysisResult(**result_data)
            
        except ValidationError as e:
            print(f"[RequirementAnalyzer] 结果验证失败: {e}")
            raise
    
    def _fix_requirement_data(self, req_data: dict, index: int) -> Optional[Requirement]:
        """尝试修复需求数据"""
        try:
            # 修复常见问题
            fixed_data = req_data.copy()
            
            # 确保ID格式
            if "id" not in fixed_data or not fixed_data["id"]:
                fixed_data["id"] = f"REQ_{index:03d}"
            
            # 确保标题存在
            if "title" not in fixed_data or not fixed_data["title"]:
                fixed_data["title"] = f"需求 {index}"
            
            # 确保描述存在且足够长
            if "description" not in fixed_data or len(fixed_data["description"]) < 10:
                fixed_data["description"] = f"这是第 {index} 个需求的详细描述"
            
            # 确保验收标准存在
            if "acceptance_criteria" not in fixed_data or not fixed_data["acceptance_criteria"]:
                fixed_data["acceptance_criteria"] = ["基本功能正常工作"]
            
            # 验证优先级
            if "priority" not in fixed_data or fixed_data["priority"] not in ["high", "medium", "low"]:
                fixed_data["priority"] = "medium"
            
            # 验证类型
            if "type" not in fixed_data or fixed_data["type"] not in ["functional", "non_functional", "business", "technical"]:
                fixed_data["type"] = "functional"
            
            return Requirement(**fixed_data)
            
        except Exception as e:
            print(f"[RequirementAnalyzer] 无法修复需求数据: {e}")
            return None
    
    def _fallback_parse(self, json_data: Dict[str, Any]) -> RequirementAnalysisResult:
        """降级解析方案（当Pydantic验证失败时）"""
        print("[RequirementAnalyzer] 使用降级解析方案")
        
        try:
            # 简单的数据清理和默认值设置
            requirements = []
            raw_requirements = json_data.get("requirements", [])
            
            for i, req_data in enumerate(raw_requirements):
                # 创建最基本的需求对象
                requirement = Requirement(
                    id=req_data.get("id", f"REQ_{i+1:03d}"),
                    title=req_data.get("title", f"需求 {i+1}"),
                    description=req_data.get("description", "需求描述"),
                    priority=Priority.MEDIUM,
                    type=RequirementType.FUNCTIONAL,
                    acceptance_criteria=req_data.get("acceptance_criteria", ["基本功能正常"]),
                    ui_elements=req_data.get("ui_elements", [])
                )
                requirements.append(requirement)
            
            return RequirementAnalysisResult(
                requirements=requirements,
                summary=json_data.get("summary", "需求分析完成（降级模式）"),
                total_count=len(requirements)
            )
            
        except Exception as e:
            print(f"[RequirementAnalyzer] 降级解析也失败: {e}")
            # 返回空结果
            return RequirementAnalysisResult(
                requirements=[],
                summary="需求分析失败",
                total_count=0
            )
