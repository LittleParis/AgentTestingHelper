"""
评审相关的数据模型
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from enum import Enum


class CommentSeverity(str, Enum):
    """评论严重程度"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CommentType(str, Enum):
    """评论类型"""
    ERROR = "error"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    NO_COVERAGE = "no_coverage"
    PARSE_ERROR = "parse_error"


class ReviewComment(BaseModel):
    """评审评论"""
    type: CommentType = Field(
        description="评论类型"
    )
    severity: CommentSeverity = Field(
        default=CommentSeverity.MEDIUM,
        description="严重程度"
    )
    message: str = Field(
        min_length=5,
        description="评论内容"
    )
    field: Optional[str] = Field(
        default=None,
        description="指向的字段名"
    )

    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        """验证消息内容"""
        return v.strip()


class ReviewDimensions(BaseModel):
    """评审维度得分"""
    completeness: int = Field(
        ge=0, le=20,
        description="完整性得分 (0-20)"
    )
    coverage: int = Field(
        ge=0, le=20,
        description="覆盖率得分 (0-20)"
    )
    reasonability: int = Field(
        ge=0, le=20,
        description="合理性得分 (0-20)"
    )
    independence: int = Field(
        ge=0, le=20,
        description="独立性得分 (0-20)"
    )
    clarity: int = Field(
        ge=0, le=20,
        description="清晰度得分 (0-20)"
    )

    def total(self) -> int:
        """计算总分"""
        return self.completeness + self.coverage + self.reasonability + self.independence + self.clarity

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "completeness": self.completeness,
            "coverage": self.coverage,
            "reasonability": self.reasonability,
            "independence": self.independence,
            "clarity": self.clarity
        }


class ReviewResult(BaseModel):
    """单个需求的评审结果"""
    passed: bool = Field(
        description="是否通过评审"
    )
    score: int = Field(
        ge=0, le=100,
        description="评审得分 (0-100)"
    )
    dimensions: Optional[ReviewDimensions] = Field(
        default=None,
        description="各维度得分"
    )
    comments: List[ReviewComment] = Field(
        default_factory=list,
        description="评审评论"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="改进建议"
    )

    @model_validator(mode='after')
    def validate_score_consistency(self):
        """验证分数与维度一致性"""
        if self.dimensions:
            expected_score = self.dimensions.total()
            if self.score != expected_score:
                # 以维度计算为准
                self.score = expected_score
        return self

    @field_validator('suggestions')
    @classmethod
    def validate_suggestions(cls, v):
        """验证建议列表"""
        # 去重并过滤空字符串
        return list(dict.fromkeys(filter(lambda x: x and x.strip(), v)))

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "passed": self.passed,
            "score": self.score,
            "dimensions": self.dimensions.to_dict() if self.dimensions else None,
            "comments": [c.model_dump() for c in self.comments],
            "suggestions": self.suggestions
        }


class RequirementReviewDetail(BaseModel):
    """单个需求的评审详情"""
    requirement_id: str = Field(
        description="需求ID"
    )
    requirement_title: str = Field(
        description="需求标题"
    )
    passed: bool = Field(
        description="是否通过评审"
    )
    score: float = Field(
        ge=0, le=100,
        description="评审得分"
    )
    dimensions: Optional[ReviewDimensions] = Field(
        default=None,
        description="各维度得分"
    )
    comments: List[ReviewComment] = Field(
        default_factory=list,
        description="评审评论"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="改进建议"
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "requirement_id": self.requirement_id,
            "requirement_title": self.requirement_title,
            "passed": self.passed,
            "score": self.score,
            "dimensions": self.dimensions.to_dict() if self.dimensions else None,
            "comments": [c.model_dump() for c in self.comments],
            "suggestions": self.suggestions
        }


class ReviewAllResult(BaseModel):
    """整体评审结果"""
    passed: bool = Field(
        description="整体是否通过"
    )
    total_score: float = Field(
        ge=0, le=100,
        description="平均得分"
    )
    details: List[RequirementReviewDetail] = Field(
        default_factory=list,
        description="各需求评审详情"
    )
    summary: str = Field(
        min_length=5,
        description="评审摘要"
    )

    @model_validator(mode='after')
    def validate_passed_consistency(self):
        """验证通过状态一致性"""
        if self.details:
            # 所有需求都通过且平均分>=60才算通过
            all_passed = all(d.passed for d in self.details)
            score_passed = self.total_score >= 60
            expected_passed = all_passed and score_passed
            if self.passed != expected_passed:
                self.passed = expected_passed
        return self

    @field_validator('total_score')
    @classmethod
    def validate_total_score(cls, v):
        """验证总分范围"""
        return round(v, 1)

    def get_passed_count(self) -> int:
        """获取通过的需求数量"""
        return sum(1 for d in self.details if d.passed)

    def get_failed_details(self) -> List[RequirementReviewDetail]:
        """获取未通过的评审详情"""
        return [d for d in self.details if not d.passed]

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "passed": self.passed,
            "total_score": self.total_score,
            "details": [d.to_dict() for d in self.details],
            "summary": self.summary
        }
