"""Common utility functions for test strategy planning."""

from typing import Iterable

from core.agents.strategy.keywords import StrategyKeywords


class StrategyUtils:
    """Common utility functions for strategy classification."""

    @staticmethod
    def contains_any(text: str, keywords: Iterable[str]) -> bool:
        """Check if text contains any of the given keywords.

        Args:
            text: Text to search in (should be normalized)
            keywords: Keywords to search for

        Returns:
            True if any keyword is found in text
        """
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def normalize(value: str) -> str:
        """Normalize text for keyword matching.

        Converts to lowercase and strips whitespace.

        Args:
            value: Text to normalize

        Returns:
            Normalized text
        """
        return str(value or "").strip().lower()

    @staticmethod
    def is_payment_related(normalized_text: str) -> bool:
        """Check if text is payment-related.

        Args:
            normalized_text: Pre-normalized text

        Returns:
            True if payment keywords are found
        """
        return StrategyUtils.contains_any(normalized_text, StrategyKeywords.PAYMENT_KEYWORDS)

    @staticmethod
    def is_login_related(normalized_text: str) -> bool:
        """Check if text is login-related.

        Args:
            normalized_text: Pre-normalized text

        Returns:
            True if login keywords are found
        """
        return StrategyUtils.contains_any(normalized_text, StrategyKeywords.LOGIN_KEYWORDS)

    @staticmethod
    def is_order_related(normalized_text: str) -> bool:
        """Check if text is order-related.

        Args:
            normalized_text: Pre-normalized text

        Returns:
            True if order keywords are found
        """
        return StrategyUtils.contains_any(normalized_text, StrategyKeywords.ORDER_KEYWORDS)
