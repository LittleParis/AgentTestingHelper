"""
测试Pydantic模型的基本功能
"""
import json
from core.models.requirement import Requirement, RequirementAnalysisResult, Priority, RequirementType


def test_requirement_model():
    """测试需求模型"""
    print("=" * 60)
    print("测试需求模型 (Requirement)")
    print("=" * 60)
    
    # 测试1: 创建有效的需求
    print("\n[测试1] 创建有效需求")
    try:
        req = Requirement(
            id="REQ_001",
            title="用户登录功能",
            description="用户可以通过用户名和密码登录系统，支持记住密码功能",
            priority=Priority.HIGH,
            type=RequirementType.FUNCTIONAL,
            acceptance_criteria=[
                "正确的用户名和密码可以成功登录",
                "错误的密码提示'密码错误'",
                "用户名不存在提示'用户不存在'"
            ],
            ui_elements=["用户名输入框", "密码输入框", "登录按钮"]
        )
        
        print(f"✅ 需求创建成功")
        print(f"   ID: {req.id}")
        print(f"   标题: {req.title}")
        print(f"   优先级: {req.priority}")
        print(f"   类型: {req.type}")
        print(f"   验收标准数量: {len(req.acceptance_criteria)}")
        print(f"   UI元素数量: {len(req.ui_elements)}")
        
    except Exception as e:
        print(f"❌ 需求创建失败: {e}")
        return False
    
    # 测试2: 测试数据验证
    print("\n[测试2] 数据验证")
    
    # 测试无效ID格式
    try:
        invalid_req = Requirement(
            id="INVALID_ID",  # 错误格式
            title="测试",
            description="这是一个测试需求"
        )
        print("❌ 应该拒绝无效ID格式")
        return False
    except Exception as e:
        print(f"✅ 正确拒绝无效ID: {type(e).__name__}")
    
    # 测试空标题
    try:
        invalid_req = Requirement(
            id="REQ_002",
            title="",  # 空标题
            description="这是一个测试需求"
        )
        print("❌ 应该拒绝空标题")
        return False
    except Exception as e:
        print(f"✅ 正确拒绝空标题: {type(e).__name__}")
    
    # 测试描述太短
    try:
        invalid_req = Requirement(
            id="REQ_003",
            title="测试需求",
            description="短"  # 太短
        )
        print("❌ 应该拒绝太短的描述")
        return False
    except Exception as e:
        print(f"✅ 正确拒绝太短描述: {type(e).__name__}")
    
    # 测试3: JSON序列化
    print("\n[测试3] JSON序列化")
    try:
        json_str = req.json(ensure_ascii=False, indent=2)
        print(f"✅ JSON序列化成功，长度: {len(json_str)} 字符")
        
        # 验证可以反序列化
        req_from_json = Requirement.parse_raw(json_str)
        print(f"✅ JSON反序列化成功: {req_from_json.id}")
        
    except Exception as e:
        print(f"❌ JSON序列化失败: {e}")
        return False
    
    return True


def test_requirement_analysis_result():
    """测试需求分析结果模型"""
    print("\n" + "=" * 60)
    print("测试需求分析结果模型 (RequirementAnalysisResult)")
    print("=" * 60)
    
    # 创建测试需求
    requirements = [
        Requirement(
            id="REQ_001",
            title="用户登录",
            description="用户登录功能的详细描述",
            acceptance_criteria=["能够成功登录"]
        ),
        Requirement(
            id="REQ_002", 
            title="用户注册",
            description="用户注册功能的详细描述",
            acceptance_criteria=["能够成功注册"]
        )
    ]
    
    # 测试1: 创建有效的分析结果
    print("\n[测试1] 创建有效分析结果")
    try:
        result = RequirementAnalysisResult(
            requirements=requirements,
            summary="识别出2个功能需求，涉及用户认证模块",
            total_count=2
        )
        
        print(f"✅ 分析结果创建成功")
        print(f"   需求数量: {result.total_count}")
        print(f"   摘要: {result.summary}")
        print(f"   实际需求数: {len(result.requirements)}")
        
    except Exception as e:
        print(f"❌ 分析结果创建失败: {e}")
        return False
    
    # 测试2: 数量不匹配验证
    print("\n[测试2] 数量不匹配验证")
    try:
        invalid_result = RequirementAnalysisResult(
            requirements=requirements,  # 2个需求
            summary="测试",
            total_count=3  # 但说是3个
        )
        print("❌ 应该拒绝数量不匹配")
        return False
    except Exception as e:
        print(f"✅ 正确拒绝数量不匹配: {type(e).__name__}")
    
    # 测试3: ID重复验证
    print("\n[测试3] ID重复验证")
    duplicate_requirements = [
        Requirement(
            id="REQ_001",  # 重复ID
            title="需求1",
            description="第一个需求的描述",
            acceptance_criteria=["标准1"]
        ),
        Requirement(
            id="REQ_001",  # 重复ID
            title="需求2", 
            description="第二个需求的描述",
            acceptance_criteria=["标准2"]
        )
    ]
    
    try:
        invalid_result = RequirementAnalysisResult(
            requirements=duplicate_requirements,
            summary="测试",
            total_count=2
        )
        print("❌ 应该拒绝重复ID")
        return False
    except Exception as e:
        print(f"✅ 正确拒绝重复ID: {type(e).__name__}")
    
    # 测试4: 便捷方法
    print("\n[测试4] 便捷方法")
    try:
        # 按优先级筛选
        high_priority = result.get_requirements_by_priority(Priority.HIGH)
        medium_priority = result.get_requirements_by_priority(Priority.MEDIUM)
        
        print(f"✅ 按优先级筛选: 高={len(high_priority)}, 中={len(medium_priority)}")
        
        # 按类型筛选
        functional = result.get_requirements_by_type(RequirementType.FUNCTIONAL)
        print(f"✅ 按类型筛选: 功能性={len(functional)}")
        
        # 转换为字典
        dict_result = result.to_dict()
        print(f"✅ 字典转换: 包含 {len(dict_result)} 个键")
        
        # 验证字典结构
        expected_keys = {"requirements", "summary", "total_count"}
        actual_keys = set(dict_result.keys())
        if expected_keys.issubset(actual_keys):
            print("✅ 字典结构正确")
        else:
            print(f"❌ 字典结构错误，缺少: {expected_keys - actual_keys}")
            return False
            
    except Exception as e:
        print(f"❌ 便捷方法测试失败: {e}")
        return False
    
    return True


def test_enum_values():
    """测试枚举值"""
    print("\n" + "=" * 60)
    print("测试枚举值")
    print("=" * 60)
    
    # 测试Priority枚举
    print("\n[测试1] Priority枚举")
    priorities = [Priority.HIGH, Priority.MEDIUM, Priority.LOW]
    for p in priorities:
        print(f"✅ {p.name} = {p.value}")
    
    # 测试RequirementType枚举
    print("\n[测试2] RequirementType枚举")
    types = [RequirementType.FUNCTIONAL, RequirementType.NON_FUNCTIONAL, 
             RequirementType.BUSINESS, RequirementType.TECHNICAL]
    for t in types:
        print(f"✅ {t.name} = {t.value}")
    
    return True


def test_json_compatibility():
    """测试JSON兼容性"""
    print("\n" + "=" * 60)
    print("测试JSON兼容性")
    print("=" * 60)
    
    # 创建测试数据
    req = Requirement(
        id="REQ_001",
        title="测试需求",
        description="这是一个测试需求的详细描述",
        priority=Priority.HIGH,
        type=RequirementType.FUNCTIONAL,
        acceptance_criteria=["标准1", "标准2"],
        ui_elements=["元素1", "元素2"]
    )
    
    result = RequirementAnalysisResult(
        requirements=[req],
        summary="测试摘要",
        total_count=1
    )
    
    # 测试1: Pydantic JSON
    print("\n[测试1] Pydantic JSON序列化")
    try:
        pydantic_json = result.json(ensure_ascii=False, indent=2)
        print(f"✅ Pydantic JSON长度: {len(pydantic_json)}")
        
        # 验证可以解析
        parsed = json.loads(pydantic_json)
        print(f"✅ JSON解析成功，包含 {len(parsed)} 个键")
        
    except Exception as e:
        print(f"❌ Pydantic JSON失败: {e}")
        return False
    
    # 测试2: 字典转换后的JSON
    print("\n[测试2] 字典JSON序列化")
    try:
        dict_data = result.to_dict()
        dict_json = json.dumps(dict_data, ensure_ascii=False, indent=2)
        print(f"✅ 字典JSON长度: {len(dict_json)}")
        
        # 验证结构一致性
        dict_parsed = json.loads(dict_json)
        pydantic_parsed = json.loads(pydantic_json)
        
        # 比较关键字段
        if (dict_parsed["summary"] == pydantic_parsed["summary"] and
            dict_parsed["total_count"] == pydantic_parsed["total_count"]):
            print("✅ JSON结构一致")
        else:
            print("❌ JSON结构不一致")
            return False
            
    except Exception as e:
        print(f"❌ 字典JSON失败: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("🧪 开始测试Pydantic模型...")
    
    tests = [
        ("需求模型", test_requirement_model),
        ("需求分析结果模型", test_requirement_analysis_result),
        ("枚举值", test_enum_values),
        ("JSON兼容性", test_json_compatibility)
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
        print("🎉 所有测试通过！Pydantic模型工作正常")
    else:
        print("💥 部分测试失败，请检查实现")
    print("=" * 60)