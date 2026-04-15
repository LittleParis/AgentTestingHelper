"""
测试用例相关的数据模型
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum
from datetime import datetime
from .requirement import Priority


class TestCaseType(str, Enum):
    """测试用例类型"""
    FUNCTIONAL = "functional"
    UI = "ui"
    API = "api"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"


class TestStep(BaseModel):
    """测试步骤"""
    step_number: int = Field(
        ge=1, 
        description="步骤序号，从1开始",
        example=1
    )
    action: str = Field(
        ..., 
        min_length=5, 
        description="操作描述，使用自然语言",
        example="在用户名输入框中输入 'admin'"
    )
    data: Optional[str] = Field(
        None, 
        description="测试数据",
        example="admin"
    )
    expected: str = Field(
        ..., 
        min_length=3, 
        description="该步骤的预期结果",
        example="用户名输入框显示 'admin'"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "step_number": 1,
                "action": "在用户名输入框中输入 'admin'",
                "data": "admin",
                "expected": "用户名输入框显示 'admin'"
            }
        }


class TestCase(BaseModel):
    """测试用例模型"""
    id: str = Field(
        ..., 
        pattern=r"^TC_\d{3}$", 
        description="测试用例ID，格式：TC_001",
        example="TC_001"
    )
    requirement_id: str = Field(
        ..., 
        pattern=r"^REQ_\d{3}$", 
        description="关联的需求ID",
        example="REQ_001"
    )
    title: str = Field(
        ..., 
        min_length=5, 
        max_length=200, 
        description="测试用例标题",
        example="正确用户名和密码登录成功"
    )
    priority: Priority = Field(
        default=Priority.MEDIUM, 
        description="测试优先级"
    )
    type: TestCaseType = Field(
        default=TestCaseType.FUNCTIONAL, 
        description="测试用例类型"
    )
    steps: List[TestStep] = Field(
        ..., 
        min_items=1, 
        description="测试步骤列表"
    )
    expected: str = Field(
        ..., 
        min_length=5, 
        description="最终预期结果",
        example="用户成功登录，跳转到首页"
    )
    tags: List[str] = Field(
        default_factory=list, 
        description="测试标签",
        example=["smoke", "login", "positive"]
    )
    preconditions: Optional[str] = Field(
        None,
        description="前置条件",
        example="用户已注册且账户未被锁定"
    )
    postconditions: Optional[str] = Field(
        None,
        description="后置条件",
        example="用户处于登录状态"
    )
    estimated_time: Optional[int] = Field(
        None,
        ge=1,
        description="预估执行时间(秒)",
        example=30
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="创建时间"
    )
    
    @validator('steps')
    def validate_steps_sequence(cls, v):
        """验证步骤序号连续性"""
        if not v:
            raise ValueError("至少需要一个测试步骤")
        
        expected_numbers = list(range(1, len(v) + 1))
        actual_numbers = [step.step_number for step in v]
        
        if actual_numbers != expected_numbers:
            raise ValueError(f"步骤序号不连续: 期望 {expected_numbers}, 实际 {actual_numbers}")
        
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        """验证和清理标签"""
        # 去重、去空、转小写
        cleaned_tags = []
        for tag in v:
            tag = tag.strip().lower()
            if tag and tag not in cleaned_tags:
                cleaned_tags.append(tag)
        return cleaned_tags
    
    @validator('title')
    def validate_title_format(cls, v):
        """验证标题格式"""
        # 确保标题不以数字开头，不包含特殊字符
        if v[0].isdigit():
            raise ValueError("测试用例标题不能以数字开头")
        
        invalid_chars = ['<', '>', '|', ':', '*', '?', '"']
        for char in invalid_chars:
            if char in v:
                raise ValueError(f"测试用例标题不能包含字符: {char}")
        
        return v
    
    def get_step_count(self) -> int:
        """获取步骤数量"""
        return len(self.steps)
    
    def has_tag(self, tag: str) -> bool:
        """检查是否包含指定标签"""
        return tag.lower() in self.tags
    
    class Config:
        json_encoders = {
            Priority: lambda v: v.value,
            TestCaseType: lambda v: v.value,
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "id": "TC_001",
                "requirement_id": "REQ_001",
                "title": "正确用户名和密码登录成功",
                "priority": "high",
                "type": "functional",
                "steps": [
                    {
                        "step_number": 1,
                        "action": "打开登录页面",
                        "data": "https://example.com/login",
                        "expected": "显示登录表单"
                    },
                    {
                        "step_number": 2,
                        "action": "输入用户名",
                        "data": "admin",
                        "expected": "用户名输入框显示 'admin'"
                    },
                    {
                        "step_number": 3,
                        "action": "输入密码",
                        "data": "password123",
                        "expected": "密码输入框显示密码掩码"
                    },
                    {
                        "step_number": 4,
                        "action": "点击登录按钮",
                        "data": None,
                        "expected": "提交登录请求"
                    }
                ],
                "expected": "用户成功登录，跳转到首页",
                "tags": ["smoke", "login", "positive"],
                "preconditions": "用户已注册且账户未被锁定",
                "postconditions": "用户处于登录状态",
                "estimated_time": 30
            }
        }


class TestCaseGenerationResult(BaseModel):
    """测试用例生成结果"""
    test_cases: List[TestCase] = Field(
        default_factory=list,
        description="生成的测试用例列表"
    )
    requirement_id: str = Field(
        ..., 
        description="关联的需求ID"
    )
    generation_time: datetime = Field(
        default_factory=datetime.now,
        description="生成时间"
    )
    total_count: int = Field(
        ge=0, 
        description="生成的测试用例数量"
    )
    generation_strategy: Optional[str] = Field(
        None,
        description="生成策略说明",
        example="基于验收标准生成正向和负向测试用例"
    )
    
    @validator('total_count', always=True)
    def validate_total_count(cls, v, values):
        """验证测试用例总数"""
        test_cases = values.get('test_cases', [])
        actual_count = len(test_cases)
        if v != actual_count:
            raise ValueError(f"total_count ({v}) 与实际测试用例数量 ({actual_count}) 不匹配")
        return v
    
    @validator('test_cases')
    def validate_test_cases_requirement_id(cls, v, values):
        """验证所有测试用例的需求ID一致"""
        requirement_id = values.get('requirement_id')
        if requirement_id:
            for tc in v:
                if tc.requirement_id != requirement_id:
                    raise ValueError(f"测试用例 {tc.id} 的需求ID ({tc.requirement_id}) 与期望的需求ID ({requirement_id}) 不匹配")
        return v
    
    @validator('test_cases')
    def validate_test_cases_unique_ids(cls, v):
        """验证测试用例ID唯一性"""
        ids = [tc.id for tc in v]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"发现重复的测试用例ID: {duplicates}")
        return v
    
    def get_test_cases_by_priority(self, priority: Priority) -> List[TestCase]:
        """按优先级获取测试用例"""
        return [tc for tc in self.test_cases if tc.priority == priority]
    
    def get_test_cases_by_type(self, test_type: TestCaseType) -> List[TestCase]:
        """按类型获取测试用例"""
        return [tc for tc in self.test_cases if tc.type == test_type]
    
    def get_test_cases_by_tag(self, tag: str) -> List[TestCase]:
        """按标签获取测试用例"""
        return [tc for tc in self.test_cases if tc.has_tag(tag)]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }