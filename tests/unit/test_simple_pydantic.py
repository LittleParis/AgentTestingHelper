"""
简化的Pydantic测试，兼容V2
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from enum import Enum
import json


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
    """需求模型 - Pydantic V2 兼容版本"""
    id: str = Field(pattern=r"^REQ_\d{3}$", description="需求ID，格式：REQ_001")
    title: str = Field(min_length=1, max_length=200, description="需求标题")
    description: str = Field(min_length=10, description="需求详细描述")
    priority: Priority = Field(default=Priority.MEDIUM, description="优先级")
    type: RequirementType = Field(default=RequirementType.FUNCTIONAL, description="需求类型")
    acceptance_criteria: List[str] = Field(default_factory=list, description="验收标准列表")
    ui_elements: List[str] = Field(default_factory=list, description="涉及的UI元素")
    
    @field_validator('acceptance_criteria')
    @classmethod
    def validate_acceptance_criteria(cls, v):
        """验证验收标准"""
        if not v:
            raise ValueError("至少需要一个验收标准")
        
        for criterion in v:
            if len(criterion.strip()) < 5:
                raise ValueError(f"验收标准太短: {criterion}")
        
        return v
    
    @field_validator('ui_elements')
    @classmethod
    def validate_ui_elements(cls, v):
        """验证UI元素"""
        # 去重并过滤空字符串
        return list(set(filter(lambda x: x.strip(), v)))


class RequirementAnalysisResult(BaseModel):
    """需求分析结果 - Pydantic V2 兼容版本"""
    requirements: List[Requirement] = Field(default_factory=list, description="分析出的需求列表")
    summary: str = Field(min_length=10, description="需求摘要")
    total_count: int = Field(ge=0, description="需求总数")
    
    @model_validator(mode='after')
    def validate_total_count(self):
        """验证需求总数与实际数量一致"""
        actual_count = len(self.requirements)
        if self.total_count != actual_count:
            raise ValueError(f"total_count ({self.total_count}) 与实际需求数量 ({actual_count}) 不匹配")
        return self
    
    @field_validator('requirements')
    @classmethod
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
            "requirements": [req.model_dump() for req in self.requirements],
            "summary": self.summary,
            "total_count": self.total_count
        }


def test_basic_functionality():
    """测试基本功能"""
    print("=" * 60)
    print("测试Pydantic V2兼容的需求模型")
    print("=" * 60)
    
    # 测试1: 创建有效需求
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
    
    # 测试2: 数据验证
    print("\n[测试2] 数据验证")
    
    # 测试无效ID格式
    try:
        invalid_req = Requirement(
            id="INVALID_ID",
            title="测试",
            description="这是一个测试需求的详细描述"
        )
        print("❌ 应该拒绝无效ID格式")
        return False
    except Exception as e:
        print(f"✅ 正确拒绝无效ID: {type(e).__name__}")
    
    # 测试3: JSON序列化 (Pydantic V2方式)
    print("\n[测试3] JSON序列化")
    try:
        # 使用V2的方法
        json_str = req.model_dump_json(indent=2)
        print(f"✅ JSON序列化成功，长度: {len(json_str)} 字符")
        
        # 验证可以反序列化
        req_from_json = Requirement.model_validate_json(json_str)
        print(f"✅ JSON反序列化成功: {req_from_json.id}")
        
    except Exception as e:
        print(f"❌ JSON序列化失败: {e}")
        return False
    
    # 测试4: 需求分析结果
    print("\n[测试4] 需求分析结果")
    try:
        requirements = [req]
        result = RequirementAnalysisResult(
            requirements=requirements,
            summary="识别出1个高优先级功能需求，涉及用户认证",
            total_count=1
        )
        
        print(f"✅ 分析结果创建成功")
        print(f"   需求数量: {result.total_count}")
        print(f"   摘要: {result.summary}")
        
        # 测试便捷方法
        high_priority = result.get_requirements_by_priority(Priority.HIGH)
        print(f"✅ 高优先级需求: {len(high_priority)} 个")
        
        # 测试字典转换
        dict_result = result.to_dict()
        print(f"✅ 字典转换成功，包含 {len(dict_result)} 个键")
        
    except Exception as e:
        print(f"❌ 分析结果测试失败: {e}")
        return False
    
    # 测试5: 向后兼容性
    print("\n[测试5] 向后兼容性")
    try:
        # 模拟旧格式数据
        old_data = {
            "id": "REQ_002",
            "title": "用户注册",
            "description": "用户可以注册新账户，需要邮箱验证",
            "priority": "medium",
            "type": "functional",
            "acceptance_criteria": ["邮箱格式验证", "密码强度检查", "验证码发送"],
            "ui_elements": ["邮箱输入框", "密码输入框", "确认按钮"]
        }
        
        # 从字典创建
        req_from_dict = Requirement(**old_data)
        print(f"✅ 从字典创建需求成功: {req_from_dict.id}")
        
        # 转换回字典
        dict_back = req_from_dict.model_dump()
        print(f"✅ 转换回字典成功")
        
        # 验证关键字段存在
        required_fields = {"id", "title", "description", "priority", "type"}
        if required_fields.issubset(set(dict_back.keys())):
            print("✅ 字典结构兼容")
        else:
            print(f"❌ 字典缺少字段: {required_fields - set(dict_back.keys())}")
            return False
            
    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")
        return False
    
    return True


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试错误处理")
    print("=" * 60)
    
    # 测试1: 验收标准太短
    print("\n[测试1] 验收标准验证")
    try:
        req = Requirement(
            id="REQ_003",
            title="测试需求",
            description="这是一个测试需求的详细描述",
            acceptance_criteria=["短"]  # 太短
        )
        print("❌ 应该拒绝太短的验收标准")
        return False
    except Exception as e:
        print(f"✅ 正确拒绝太短验收标准: {type(e).__name__}")
    
    # 测试2: 数量不匹配
    print("\n[测试2] 数量不匹配验证")
    try:
        req = Requirement(
            id="REQ_004",
            title="测试需求",
            description="这是一个测试需求的详细描述",
            acceptance_criteria=["这是一个足够长的验收标准"]
        )
        
        result = RequirementAnalysisResult(
            requirements=[req],
            summary="测试摘要内容",
            total_count=2  # 错误的数量
        )
        print("❌ 应该拒绝数量不匹配")
        return False
    except Exception as e:
        print(f"✅ 正确拒绝数量不匹配: {type(e).__name__}")
    
    return True


if __name__ == "__main__":
    print("🧪 开始测试Pydantic V2兼容的需求模型...")
    
    success1 = test_basic_functionality()
    success2 = test_error_handling()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 所有测试通过！")
        print("\n📋 Pydantic集成改进总结:")
        print("1. ✅ 类型安全 - 自动验证数据类型和格式")
        print("2. ✅ 数据验证 - 运行时验证业务规则")
        print("3. ✅ 向后兼容 - 支持原有字典格式")
        print("4. ✅ 便捷方法 - 提供筛选和转换功能")
        print("5. ✅ JSON序列化 - 自动处理复杂类型")
        print("6. ✅ 详细错误 - 提供具体验证错误信息")
        print("\n🚀 可以开始集成到需求分析Agent中！")
    else:
        print("💥 测试失败，需要修复问题")
    print("=" * 60)