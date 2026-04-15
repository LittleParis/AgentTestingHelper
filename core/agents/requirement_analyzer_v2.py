"""
需求分析Agent - Pydantic版本

相比原版的改进：
1. 使用 Pydantic 模型确保数据类型安全
2. 自动验证输出格式
3. 更好的错误处理
4. 支持配置管理
"""
import json
import os
from typing import Dict, Any, List
from pydantic import ValidationError

from core.utils.llm_client import get_llm_client
from models.requirement import Requirement, RequirementAnalysisResult, RequirementType, Priority
from models.config import get_settings


class RequirementAnalyzerV2:
    """需求分析Agent - Pydantic版本"""
    
    def __init__(self):
        """初始化需求分析Agent"""
        self.settings = get_settings()
        self.llm = get_llm_client()
    
    def analyze(self, requirement_text: str) -> RequirementAnalysisResult:
        """
        分析需求文档
        
        Args:
            requirement_text: 需求文档内容
            
        Returns:
            RequirementAnalysisResult: 结构化的需求分析结果
            
        Raises:
            ValidationError: 当LLM输出不符合预期格式时
            ValueError: 当输入参数无效时
        """
        if not requirement_text or len(requirement_text.strip()) < 10:
            raise ValueError("需求文档内容太短，至少需要10个字符")
        
        prompt = self._build_prompt(requirement_text)
        
        try:
            # 调用LLM
            content = self.llm.chat_simple(
                prompt, 
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens
            )
            
            # 解析JSON响应
            json_data = self._extract_json(content)
            
            # 使用Pydantic验证和解析
            result = self._parse_llm_response(json_data)
            
            return result
            
        except ValidationError as e:
            print(f"[RequirementAnalyzer] 数据验证失败: {e}")
            # 可以选择降级到简单解析或重试
            raise
        except json.JSONDecodeError as e:
            print(f"[RequirementAnalyzer] JSON解析失败: {e}")
            print(f"原始响应: {content}")
            raise
        except Exception as e:
            print(f"[RequirementAnalyzer] 分析失败: {e}")
            raise
    
    def _build_prompt(self, requirement_text: str) -> str:
        """构建分析prompt"""
        # 使用Pydantic模型的schema生成更准确的示例
        requirement_schema = Requirement.schema()
        result_schema = RequirementAnalysisResult.schema()
        
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
                    # 可以选择跳过或使用默认值
                    continue
            
            # 创建分析结果
            result_data = {
                "requirements": requirements,
                "summary": json_data.get("summary", "需求分析完成"),
                "total_count": len(requirements)
            }
            
            return RequirementAnalysisResult(**result_data)
            
        except ValidationError as e:
            print(f"[RequirementAnalyzer] 结果验证失败: {e}")
            # 提供更详细的错误信息
            self._log_validation_error(e, json_data)
            raise
    
    def _log_validation_error(self, error: ValidationError, data: Dict[str, Any]):
        """记录详细的验证错误信息"""
        print("=" * 50)
        print("数据验证错误详情:")
        print("=" * 50)
        
        for err in error.errors():
            field = " -> ".join(str(x) for x in err["loc"])
            message = err["msg"]
            value = err.get("input", "N/A")
            
            print(f"字段: {field}")
            print(f"错误: {message}")
            print(f"输入值: {value}")
            print("-" * 30)
        
        print(f"原始数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        print("=" * 50)
    
    def validate_requirements(self, requirements: List[Requirement]) -> Dict[str, Any]:
        """验证需求列表的完整性"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {}
        }
        
        # 检查ID唯一性
        ids = [req.id for req in requirements]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            validation_result["errors"].append(f"发现重复的需求ID: {duplicates}")
            validation_result["valid"] = False
        
        # 统计信息
        priorities = [req.priority for req in requirements]
        types = [req.type for req in requirements]
        
        validation_result["statistics"] = {
            "total_count": len(requirements),
            "priority_distribution": {
                "high": priorities.count(Priority.HIGH),
                "medium": priorities.count(Priority.MEDIUM),
                "low": priorities.count(Priority.LOW)
            },
            "type_distribution": {
                "functional": types.count(RequirementType.FUNCTIONAL),
                "non_functional": types.count(RequirementType.NON_FUNCTIONAL),
                "business": types.count(RequirementType.BUSINESS),
                "technical": types.count(RequirementType.TECHNICAL)
            }
        }
        
        # 检查验收标准覆盖率
        no_criteria_count = sum(1 for req in requirements if not req.acceptance_criteria)
        if no_criteria_count > 0:
            validation_result["warnings"].append(f"{no_criteria_count} 个需求缺少验收标准")
        
        return validation_result


# 便捷函数
def analyze_requirements(requirement_text: str) -> RequirementAnalysisResult:
    """便捷的需求分析函数"""
    analyzer = RequirementAnalyzerV2()
    return analyzer.analyze(requirement_text)


# ============ 测试 ============

if __name__ == "__main__":
    # 测试需求分析
    test_requirement = """
    # 用户登录功能

    ## 功能描述
    用户可以通过用户名和密码登录系统，支持记住密码功能。

    ## 详细需求
    1. 用户输入用户名和密码
    2. 系统验证用户凭据
    3. 登录成功后跳转到首页
    4. 支持"记住密码"选项

    ## 验收标准
    1. 正确的用户名和密码可以成功登录
    2. 错误的密码提示"密码错误"
    3. 用户名不存在提示"用户不存在"
    4. 密码输入3次错误后锁定账户
    5. 勾选"记住密码"后下次访问自动填充
    """

    try:
        analyzer = RequirementAnalyzerV2()
        result = analyzer.analyze(test_requirement)
        
        print("需求分析结果:")
        print("=" * 50)
        print(f"需求总数: {result.total_count}")
        print(f"摘要: {result.summary}")
        print()
        
        for req in result.requirements:
            print(f"需求ID: {req.id}")
            print(f"标题: {req.title}")
            print(f"优先级: {req.priority}")
            print(f"类型: {req.type}")
            print(f"验收标准数量: {len(req.acceptance_criteria)}")
            print(f"UI元素数量: {len(req.ui_elements)}")
            print("-" * 30)
        
        # 验证需求
        validation = analyzer.validate_requirements(result.requirements)
        print(f"验证结果: {'通过' if validation['valid'] else '失败'}")
        if validation['errors']:
            print(f"错误: {validation['errors']}")
        if validation['warnings']:
            print(f"警告: {validation['warnings']}")
        
        # 输出JSON格式（用于调试）
        print("\nJSON输出:")
        print(result.json(ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()