"""
只测试需求模型，避免导入其他模块
"""
import json
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum


class RequirementType(str, Enum):
    """需求类型枚举"""
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    BUSINESS = "business"
    TECHNICAL = "technical"


class Priority(str, Enum):
    """优先级枚举"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Requirement(BaseModel):
    """需求模型"""
    id: str = Field(
        ..., 
        pattern=r"^REQ_\d{3}$", 
        description="需求ID，格式：REQ_001",
        example="REQ_001"
    )
    title: str = Field(
        ..., 
        min_length=1, 
        max_length=200, 
        description="需求标题",
        example="用户登录功能"
    )
    description: str = Field(
        ..., 
        min_length=10, 
        description="需求详细描述",
        example="用户可以通过用户名和密码登录系统"
    )
    priority: Priority = Field(
        default=Priority.MEDIUM, 
        description="优先级"
    )
    type: RequirementType = Field(
        default=RequirementType.FUNCTIONAL, 
        description="需求类型"
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list, 
        description="验收标准列表",
        example=["正确的用户名和密码可以成功登录", "错误的密码提示'密码错误'"]
    )
    ui_elements: List[str] = Field(
        default_factory=list, 
        description="涉及的UI元素",
        example=["用户名输入框", "密码输入框", "登录按钮"]
    )
    
    @validator('acceptance_criteria')
    def validate_acceptance_criteria(cls, v):
        """验证验收标准"""
        if not v:
            raise ValueError("至少需要一个验收标准")
        
        for criterion in v:
            if len(criterion.strip()) < 5:
                raise ValueError(f"验收标准太短: {criterion}")
        
        return v
    
    @validator('ui_elements')
    def validate_ui_elements(cls, v):
        """验证UI元素"""
        # 去重并过滤空字符串
        return list(set(filter(lambda x: x.strip(), v)))


class RequirementAnalysisResult(BaseModel):
    """需求分析结果"""
    requirements: List[Requirement] = Field(
        default_factory=list,
        description="分析出的需求列表"
    )
    summary: str = Field(
        ..., 
        min_length=10, 
        description="需求摘要",
        example="本次分析识别出3个功能需求，主要涉及用户认证和权限管理"
    )
    total_count: int = Field(
        ge=0, 
        description="需求总数"
    )
    
    @validator('total_count', always=True)
    def validate_total_count(cls, v, values):
        """验证需求总数与实际数量一致"""
        requirements = values.get('requirements', [])
        actual_count = len(requirements)
        if v != actual_count:
            raise ValueError(f"total_count ({v}) 与实际需求数量 ({actual_count}) 不匹配")
        return v
    
    @validator('requirements')
    def validate_requirements_unique_ids(cls, v):
        """验证需求ID唯一性"""
        ids = [req.id for req in v]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"发现重复的需求ID: {duplicates}")
        return v
    
    def get_requirements_by_priority(self, priority: Priority) -> List[Requirement]:
        """按优先级获取需求"""
        return [req for req in self.requirements if req.priority == priority]
    
    def get_requirements_by_type(self, req_type: RequirementType) -> List[Requirement]:
        """按类型获取需求"""
        return [req for req in self.requirements if req.type == req_type]
    
    def to_dict(self) -> dict:
        """转换为字典格式（向后兼容）"""
        return {
            "requirements": [req.dict() for req in self.requirements],
            "summary": self.summary,
            "total_count": self.total_count
        }


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
        return False, None
    
    # 测试2: 测试数据验证
    print("\n[测试2] 数据验证")
    
    # 测试无效ID格式
    try:
        invalid_req = Requirement(
            id="INVALID_ID",  # 错误格式
            title="测试",
            description="这是一个测试需求的详细描述"
        )
        print("❌ 应该拒绝无效ID格式")
        return False, None
    except Exception as e:
        print(f"✅ 正确拒绝无效ID: {type(e).__name__}")
    
    # 测试空标题
    try:
        invalid_req = Requirement(
            id="REQ_002",
            title="",  # 空标题
            description="这是一个测试需求的详细描述"
        )
        print("❌ 应该拒绝空标题")
        return False, None
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
        return False, None
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
        return False, None
    
    return True, req


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
            summary="测试摘要内容",
            total_count=3  # 但说是3个
        )
        print("❌ 应该拒绝数量不匹配")
        return False
    except Exception as e:
        print(f"✅ 正确拒绝数量不匹配: {type(e).__name__}")
    
    # 测试3: 便捷方法
    print("\n[测试3] 便捷方法")
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


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n" + "=" * 60)
    print("测试向后兼容性")
    print("=" * 60)
    
    # 模拟原来的字典格式数据
    old_format_data = {
        "requirements": [
            {
                "id": "REQ_001",
                "title": "用户登录",
                "description": "用户可以通过用户名和密码登录系统",
                "priority": "high",
                "type": "functional",
                "acceptance_criteria": ["正确登录", "错误提示"],
                "ui_elements": ["输入框", "按钮"]
            }
        ],
        "summary": "识别出1个登录需求"
    }
    
    print("\n[测试1] 从字典创建Pydantic模型")
    try:
        # 从字典创建需求
        req_dict = old_format_data["requirements"][0]
        req = Requirement(**req_dict)
        print(f"✅ 从字典创建需求成功: {req.id}")
        
        # 创建分析结果
        result = RequirementAnalysisResult(
            requirements=[req],
            summary=old_format_data["summary"],
            total_count=1
        )
        print(f"✅ 从字典创建分析结果成功")
        
    except Exception as e:
        print(f"❌ 从字典创建失败: {e}")
        return False
    
    print("\n[测试2] 转换回字典格式")
    try:
        # 转换回字典
        new_dict = result.to_dict()
        
        # 验证结构
        if "requirements" in new_dict and "summary" in new_dict:
            print("✅ 字典结构保持兼容")
            
            # 验证需求结构
            req_dict = new_dict["requirements"][0]
            required_fields = {"id", "title", "description", "priority", "type"}
            if required_fields.issubset(set(req_dict.keys())):
                print("✅ 需求字典结构兼容")
            else:
                print(f"❌ 需求字典缺少字段: {required_fields - set(req_dict.keys())}")
                return False
        else:
            print("❌ 字典结构不兼容")
            return False
            
    except Exception as e:
        print(f"❌ 转换字典失败: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("🧪 开始测试Pydantic需求模型...")
    
    tests = [
        ("需求模型基本功能", test_requirement_model),
        ("需求分析结果模型", test_requirement_analysis_result),
        ("向后兼容性", test_backward_compatibility)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 运行测试: {test_name}")
        try:
            if test_name == "需求模型基本功能":
                success, req = test_func()
                if success:
                    print(f"✅ {test_name} 测试通过")
                    passed += 1
                else:
                    print(f"❌ {test_name} 测试失败")
            else:
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
        print("🎉 所有测试通过！Pydantic需求模型工作正常")
        print("\n📋 改进总结:")
        print("1. ✅ 数据类型安全 - 自动验证ID格式、字段长度等")
        print("2. ✅ 运行时验证 - 防止无效数据进入系统")
        print("3. ✅ 向后兼容 - 保持原有字典接口可用")
        print("4. ✅ 便捷方法 - 提供按优先级、类型筛选功能")
        print("5. ✅ JSON序列化 - 自动处理复杂类型转换")
        print("6. ✅ 详细错误 - 提供具体的验证错误信息")
    else:
        print("💥 部分测试失败，请检查实现")
    print("=" * 60)