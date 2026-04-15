"""
数据模型模块

使用 Pydantic 定义项目中的核心数据结构，提供：
- 类型安全
- 数据验证
- 自动序列化/反序列化
- JSON Schema 生成
"""

from .requirement import (
    Requirement,
    RequirementType,
    Priority,
    RequirementAnalysisResult
)

__all__ = [
    # 需求模型
    "Requirement",
    "RequirementType", 
    "Priority",
    "RequirementAnalysisResult",
]