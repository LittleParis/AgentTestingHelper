"""
需求相关的数据模型 - Pydantic V2 兼容版本
"""
from pydantic import BaseModel, Field, field_validator, model_validator
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
        pattern=r"^REQ_\d{3}$", 
        description="需求ID，格式：REQ_001"
    )
    title: str = Field(
        min_length=1, 
        max_length=200, 
        description="需求标题"
    )
    description: str = Field(
        min_length=10, 
        description="需求详细描述"
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
        description="验收标准列表"
    )
    ui_elements: List[str] = Field(
        default_factory=list, 
        description="涉及的UI元素"
    )
    
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
    """需求分析结果"""
    requirements: List[Requirement] = Field(
        default_factory=list,
        description="分析出的需求列表"
    )
    summary: str = Field(
        min_length=10, 
        description="需求摘要"
    )
    total_count: int = Field(
        ge=0, 
        description="需求总数"
    )
    
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