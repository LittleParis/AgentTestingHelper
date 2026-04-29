"""Centralized keyword definitions for test strategy planning.

All keywords are defined as tuples to ensure immutability.
Both English and Chinese keywords are included for internationalization.
"""

from typing import ClassVar, Tuple


class StrategyKeywords:
    """Centralized keyword definitions for strategy classification."""

    # Critical risk keywords - involving money, security, state changes
    CRITICAL_KEYWORDS: ClassVar[Tuple[str, ...]] = (
        "payment",
        "pay",
        "refund",
        "money",
        "fund",
        "submit",
        "commit",
        "state change",
        "status change",
        "permission",
        "security",
        "secure",
        "rollback",
        "idempotent",
        "idempotency",
        "retry",
        "approval",
        "audit",
        "risk",
        "balance",
        # Chinese
        "支付",
        "付款",
        "资金",
        "金额",
        "提交",
        "状态变更",
        "状态更新",
        "权限",
        "安全",
        "回滚",
        "幂等",
        "重试",
        "审核",
        "风控",
        "余额",
    )

    # Major risk keywords - involving errors, validation, recovery
    MAJOR_KEYWORDS: ClassVar[Tuple[str, ...]] = (
        "fail",
        "failed",
        "failure",
        "exception",
        "error",
        "invalid",
        "review",
        "verify",
        "manual",
        "recover",
        "restore",
        "negative",
        # Chinese
        "失败",
        "异常",
        "错误",
        "无效",
        "人工",
        "恢复",
        "校验",
        "拦截",
    )

    # Light risk keywords - UI, navigation, display
    LIGHT_KEYWORDS: ClassVar[Tuple[str, ...]] = (
        "load",
        "loading",
        "url",
        "visible",
        "display",
        "show",
        "hide",
        "navigate",
        "navigation",
        "tooltip",
        "hint",
        # Chinese
        "页面加载",
        "页面展示",
        "显隐",
        "展示",
        "跳转",
        "导航",
        "提示",
        "文案",
        "弱提示",
    )

    # Boundary testing keywords
    BOUNDARY_KEYWORDS: ClassVar[Tuple[str, ...]] = (
        "boundary",
        "limit",
        "min",
        "max",
        "length",
        "range",
        "edge",
        # Chinese
        "边界",
        "上限",
        "下限",
        "长度",
        "范围",
        "极限",
    )

    # Exception handling keywords
    EXCEPTION_KEYWORDS: ClassVar[Tuple[str, ...]] = (
        "exception",
        "timeout",
        "network",
        "unavailable",
        "error",
        # Chinese
        "异常",
        "超时",
        "网络",
        "不可用",
        "错误",
    )

    # Recovery behavior keywords
    RECOVERY_KEYWORDS: ClassVar[Tuple[str, ...]] = (
        "retry",
        "recover",
        "rollback",
        "resume",
        # Chinese
        "重试",
        "恢复",
        "回滚",
        "补偿",
    )

    # Permission/access control keywords
    PERMISSION_KEYWORDS: ClassVar[Tuple[str, ...]] = (
        "permission",
        "role",
        "access",
        "authorize",
        # Chinese
        "权限",
        "角色",
        "授权",
        "访问控制",
    )

    # Data validation keywords
    DATA_VALIDATION_KEYWORDS: ClassVar[Tuple[str, ...]] = (
        "validate",
        "validation",
        "format",
        "required",
        "empty",
        # Chinese
        "校验",
        "格式",
        "必填",
        "为空",
        "空值",
    )

    # Payment-related keywords (subset of CRITICAL, for specific detection)
    PAYMENT_KEYWORDS: ClassVar[Tuple[str, ...]] = (
        "payment",
        "pay",
        "refund",
        "支付",
        "付款",
        "退款",
    )

    # Order/business flow keywords
    ORDER_KEYWORDS: ClassVar[Tuple[str, ...]] = (
        "order",
        "checkout",
        "cart",
        "下单",
        "订单",
        "购物车",
    )

    # Login/authentication keywords
    LOGIN_KEYWORDS: ClassVar[Tuple[str, ...]] = (
        "login",
        "log in",
        "sign in",
        "signin",
        "登录",
        "认证",
        "鉴权",
    )
