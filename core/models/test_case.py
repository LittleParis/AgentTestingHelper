"""
测试用例相关的数据模型 - Pydantic V2 兼容版本
"""
from pydantic import BaseModel, Field, field_validator, model_validator
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
        description="步骤序号，从1开始"
    )
    action: str = Field(
        min_length=5,
        description="操作描述，使用自然语言"
    )
    data: Optional[str] = Field(
        None,
        description="测试数据"
    )
    expected: str = Field(
        min_length=3,
        description="该步骤的预期结果"
    )


class TestCase(BaseModel):
    """测试用例模型"""
    id: str = Field(
        pattern=r"^TC_[\d_]+$",
        description="测试用例ID，格式：TC_001（支持子用例格式如 TC_001_001）"
    )
    requirement_id: str = Field(
        pattern=r"^REQ_\d{1,6}$",
        description="关联的需求ID，格式：REQ_001（支持1-6位数字）"
    )
    title: str = Field(
        min_length=5,
        max_length=200,
        description="测试用例标题"
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
        min_length=1,
        description="测试步骤列表"
    )
    expected: str = Field(
        min_length=5,
        description="最终预期结果"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="测试标签"
    )
    preconditions: Optional[str] = Field(
        default=None,
        description="前置条件"
    )
    postconditions: Optional[str] = Field(
        default=None,
        description="后置条件"
    )
    estimated_time: Optional[int] = Field(
        default=None,
        ge=1,
        description="预估执行时间(秒)"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="创建时间"
    )

    @field_validator('steps')
    @classmethod
    def validate_steps_sequence(cls, v):
        """验证步骤序号连续性"""
        if not v:
            raise ValueError("至少需要一个测试步骤")

        expected_numbers = list(range(1, len(v) + 1))
        actual_numbers = [step.step_number for step in v]

        if actual_numbers != expected_numbers:
            raise ValueError(f"步骤序号不连续: 期望 {expected_numbers}, 实际 {actual_numbers}")

        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """验证和清理标签"""
        # 去重、去空、转小写
        cleaned_tags = []
        for tag in v:
            tag = tag.strip().lower()
            if tag and tag not in cleaned_tags:
                cleaned_tags.append(tag)
        return cleaned_tags

    @field_validator('title')
    @classmethod
    def validate_title_format(cls, v):
        """验证标题格式"""
        v = v.strip()
        # 只过滤文件系统不允许的字符（用于生成测试文件名）
        invalid_chars = ['<', '>', '|', '*', '?', '"', '\n', '\r']
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


class TestCaseGenerationResult(BaseModel):
    """测试用例生成结果"""
    test_cases: List[TestCase] = Field(
        default_factory=list,
        description="生成的测试用例列表"
    )
    requirement_id: str = Field(
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
        default=None,
        description="生成策略说明"
    )

    @model_validator(mode='after')
    def validate_counts(self):
        """验证数量一致性"""
        actual_count = len(self.test_cases)
        if self.total_count != actual_count:
            # 自动修正
            self.total_count = actual_count
        return self

    @field_validator('test_cases')
    @classmethod
    def validate_test_cases_requirement_id(cls, v):
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