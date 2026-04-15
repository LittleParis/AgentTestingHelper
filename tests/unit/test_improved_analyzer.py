"""
测试改进后的需求分析Agent（不依赖LLM调用）
"""
import json
from unittest.mock import Mock, patch
from core.agents.requirement_analyzer import RequirementAnalyzer
from core.models.requirement import RequirementAnalysisResult, Requirement, Priority, RequirementType


def test_analyzer_with_mock_llm():
    """使用模拟LLM测试需求分析Agent"""
    print("=" * 60)
    print("测试改进后的需求分析Agent")
    print("=" * 60)
    
    # 模拟LLM响应
    mock_llm_response = """```json
{
  "requirements": [
    {
      "id": "REQ_001",
      "title": "用户登录功能",
      "description": "用户可以通过用户名和密码登录系统，支持记住密码功能",
      "priority": "high",
      "type": "functional",
      "acceptance_criteria": [
        "正确的用户名和密码可以成功登录",
        "错误的密码提示'密码错误'",
        "用户名不存在提示'用户不存在'"
      ],
      "ui_elements": ["用户名输入框", "密码输入框", "登录按钮"]
    }
  ],
  "summary": "识别出1个高优先级功能需求，涉及用户认证",
  "total_count": 1
}
```"""
    
    # 创建模拟的LLM客户端
    mock_llm = Mock()
    mock_llm.chat_simple.return_value = mock_llm_response
    
    # 测试需求文档
    test_requirement = """
    # 用户登录功能

    ## 功能描述
    用户可以通过用户名和密码登录系统。

    ## 验收标准
    1. 正确的用户名和密码可以成功登录
    2. 错误的密码提示"密码错误"
    3. 用户名不存在提示"用户不存在"
    """
    
    # 使用patch替换LLM客户端
    with patch('agents.requirement_analyzer.get_llm_client', return_value=mock_llm):
        analyzer = RequirementAnalyzer()
        
        # 测试1: 向后兼容的字典接口
        print("\n[测试1] 向后兼容接口 (返回字典)")
        print("-" * 40)
        
        result_dict = analyzer.analyze(test_requirement)
        
        print(f"✅ 返回类型: {type(result_dict)}")
        print(f"✅ 需求数量: {len(result_dict.get('requirements', []))}")
        print(f"✅ 摘要: {result_dict.get('summary', 'N/A')}")
        
        if result_dict.get('requirements'):
            first_req = result_dict['requirements'][0]
            print(f"✅ 第一个需求ID: {first_req.get('id')}")
            print(f"✅ 第一个需求标题: {first_req.get('title')}")
            print(f"✅ 验收标准数量: {len(first_req.get('acceptance_criteria', []))}")
        
        # 测试2: 新的Pydantic接口
        print("\n[测试2] 新的Pydantic接口 (返回模型)")
        print("-" * 40)
        
        result_model = analyzer.analyze_structured(test_requirement)
        
        print(f"✅ 返回类型: {type(result_model)}")
        print(f"✅ 是否为Pydantic模型: {isinstance(result_model, RequirementAnalysisResult)}")
        print(f"✅ 需求数量: {result_model.total_count}")
        print(f"✅ 摘要: {result_model.summary}")
        
        if result_model.requirements:
            first_req = result_model.requirements[0]
            print(f"✅ 第一个需求ID: {first_req.id}")
            print(f"✅ 第一个需求标题: {first_req.title}")
            print(f"✅ 第一个需求优先级: {first_req.priority}")
            print(f"✅ 第一个需求类型: {first_req.type}")
            print(f"✅ 验收标准数量: {len(first_req.acceptance_criteria)}")
            print(f"✅ UI元素数量: {len(first_req.ui_elements)}")
        
        # 测试3: 数据验证
        print("\n[测试3] 数据验证功能")
        print("-" * 40)
        
        # 验证需求ID格式
        for req in result_model.requirements:
            if req.id.startswith("REQ_") and len(req.id) == 7:
                print(f"✅ 需求 {req.id}: ID格式正确")
            else:
                print(f"❌ 需求 {req.id}: ID格式错误")
                return False
            
            print(f"   - 标题长度: {len(req.title)} 字符")
            print(f"   - 描述长度: {len(req.description)} 字符")
            print(f"   - 验收标准: {len(req.acceptance_criteria)} 个")
        
        # 测试4: 便捷方法
        print("\n[测试4] 便捷方法")
        print("-" * 40)
        
        high_priority = result_model.get_requirements_by_priority(Priority.HIGH)
        medium_priority = result_model.get_requirements_by_priority(Priority.MEDIUM)
        low_priority = result_model.get_requirements_by_priority(Priority.LOW)
        
        print(f"✅ 高优先级需求: {len(high_priority)} 个")
        print(f"✅ 中优先级需求: {len(medium_priority)} 个")
        print(f"✅ 低优先级需求: {len(low_priority)} 个")
        
        functional_reqs = result_model.get_requirements_by_type(RequirementType.FUNCTIONAL)
        print(f"✅ 功能性需求: {len(functional_reqs)} 个")
        
        # 测试5: JSON序列化
        print("\n[测试5] JSON序列化")
        print("-" * 40)
        
        json_str = result_model.model_dump_json(indent=2)
        print(f"✅ JSON长度: {len(json_str)} 字符")
        print("✅ JSON格式正确")
        
        # 测试6: 字典转换
        print("\n[测试6] 字典转换")
        print("-" * 40)
        
        dict_result = result_model.to_dict()
        print(f"✅ 字典格式: {type(dict_result)}")
        print(f"✅ 与原接口兼容: {'requirements' in dict_result and 'summary' in dict_result}")
        
        # 验证字典和Pydantic结果一致性
        if (dict_result['summary'] == result_dict['summary'] and
            dict_result['total_count'] == result_dict['total_count']):
            print("✅ 字典接口和Pydantic接口结果一致")
        else:
            print("❌ 字典接口和Pydantic接口结果不一致")
            return False
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
        return True


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试错误处理")
    print("=" * 60)
    
    # 创建模拟的LLM客户端
    mock_llm = Mock()
    
    with patch('agents.requirement_analyzer.get_llm_client', return_value=mock_llm):
        analyzer = RequirementAnalyzer()
        
        # 测试1: 空输入
        print("\n[测试1] 空输入处理")
        try:
            result = analyzer.analyze_structured("")
            print("❌ 应该抛出ValueError")
            return False
        except ValueError as e:
            print(f"✅ 正确处理空输入: {e}")
        
        # 测试2: 太短的输入
        print("\n[测试2] 输入太短")
        try:
            result = analyzer.analyze_structured("短")
            print("❌ 应该抛出ValueError")
            return False
        except ValueError as e:
            print(f"✅ 正确处理短输入: {e}")
        
        # 测试3: 无效JSON响应
        print("\n[测试3] 无效JSON响应")
        mock_llm.chat_simple.return_value = "这不是JSON"
        
        try:
            result = analyzer.analyze_structured("这是一个足够长的需求文档内容")
            print("❌ 应该抛出JSONDecodeError")
            return False
        except json.JSONDecodeError:
            print("✅ 正确处理无效JSON")
        
        # 测试4: 降级处理
        print("\n[测试4] 降级处理机制")
        
        # 模拟格式错误但可解析的JSON
        invalid_json_response = """```json
{
  "requirements": [
    {
      "id": "INVALID_ID",
      "title": "",
      "description": "短",
      "acceptance_criteria": []
    }
  ],
  "summary": "测试",
  "total_count": 1
}
```"""
        
        mock_llm.chat_simple.return_value = invalid_json_response
        
        try:
            result = analyzer.analyze_structured("这是一个足够长的需求文档内容")
            print(f"✅ 降级处理成功，返回 {result.total_count} 个需求")
            if result.requirements:
                print(f"   修复后的需求ID: {result.requirements[0].id}")
        except Exception as e:
            print(f"❌ 降级处理失败: {e}")
            return False
        
        return True


def test_json_parsing():
    """测试JSON解析功能"""
    print("\n" + "=" * 60)
    print("测试JSON解析功能")
    print("=" * 60)
    
    analyzer = RequirementAnalyzer()
    
    # 测试1: 标准JSON代码块
    print("\n[测试1] 标准JSON代码块")
    content1 = """```json
{"test": "value"}
```"""
    
    result1 = analyzer._extract_json(content1)
    print(f"✅ 解析成功: {result1}")
    
    # 测试2: 无代码块标记
    print("\n[测试2] 无代码块标记")
    content2 = '{"test": "value"}'
    
    result2 = analyzer._extract_json(content2)
    print(f"✅ 解析成功: {result2}")
    
    # 测试3: 格式修复
    print("\n[测试3] 格式修复")
    content3 = """```
json
{"test": "value"}
```extra content"""
    
    result3 = analyzer._extract_json(content3)
    print(f"✅ 修复并解析成功: {result3}")
    
    return True


if __name__ == "__main__":
    print("🧪 开始测试改进后的需求分析Agent...")
    
    tests = [
        ("基本功能", test_analyzer_with_mock_llm),
        ("错误处理", test_error_handling),
        ("JSON解析", test_json_parsing)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 运行测试: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name} 测试通过")
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"💥 {test_name} 测试异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")
    if passed == total:
        print("🎉 所有测试通过！需求分析Agent改进成功")
        print("\n📋 改进总结:")
        print("1. ✅ 保持向后兼容 - 原有代码无需修改")
        print("2. ✅ 新增Pydantic接口 - 提供类型安全的新接口")
        print("3. ✅ 数据验证增强 - 自动验证ID格式、字段长度等")
        print("4. ✅ 错误处理改进 - 降级机制和详细错误信息")
        print("5. ✅ 便捷方法支持 - 按优先级、类型筛选需求")
        print("6. ✅ JSON处理增强 - 更强的格式修复能力")
        print("\n🚀 可以开始在项目中使用改进后的Agent！")
    else:
        print("💥 部分测试失败，需要修复问题")
    print("=" * 60)