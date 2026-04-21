"""
单元测试：验证 LLMClient 重试机制和 Token 追踪

测试目标：
1. 验证重试机制正确触发
2. 验证 Token 追踪器正确记录
3. 验证单例模式正确工作
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from core.utils.llm_client import (
    LLMClient,
    TokenTracker,
    get_llm_client,
    get_token_tracker,
    reset_llm_client,
    TokenUsage,
    ChatResponse,
    RETRYABLE_EXCEPTIONS
)


class TestTokenTracker:
    """Token 追踪器测试"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        tracker1 = get_token_tracker()
        tracker2 = get_token_tracker()
        assert tracker1 is tracker2, "TokenTracker 应该是单例"

    def test_record_token_usage(self):
        """测试记录 Token 使用"""
        tracker = TokenTracker()
        tracker.reset()  # 清空之前的数据

        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        tracker.record(usage)

        assert tracker.total_prompt_tokens == 100
        assert tracker.total_completion_tokens == 50
        assert tracker.total_tokens == 150
        assert tracker.call_count == 1

    def test_multiple_records(self):
        """测试多次记录"""
        tracker = TokenTracker()
        tracker.reset()

        tracker.record(TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150))
        tracker.record(TokenUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300))

        assert tracker.total_prompt_tokens == 300
        assert tracker.total_completion_tokens == 150
        assert tracker.call_count == 2

    def test_get_summary(self):
        """测试获取摘要"""
        tracker = TokenTracker()
        tracker.reset()

        tracker.record(TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150))

        summary = tracker.get_summary()
        assert summary["call_count"] == 1
        assert summary["total_prompt_tokens"] == 100
        assert summary["total_completion_tokens"] == 50
        assert summary["total_tokens"] == 150

    def test_reset(self):
        """测试重置"""
        tracker = TokenTracker()
        tracker.record(TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150))
        tracker.reset()

        assert tracker.total_prompt_tokens == 0
        assert tracker.total_completion_tokens == 0
        assert tracker.call_count == 0


class TestLLMClientSingleton:
    """LLMClient 单例测试"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        reset_llm_client()  # 重置单例

        client1 = get_llm_client()
        client2 = get_llm_client()

        assert client1 is client2, "LLMClient 应该是单例"

    def test_reset_singleton(self):
        """测试重置单例"""
        client1 = get_llm_client()
        reset_llm_client()
        client2 = get_llm_client()

        assert client1 is not client2, "重置后应该是新实例"


class TestRetryMechanism:
    """重试机制测试"""

    def test_retry_on_timeout(self):
        """测试超时时触发重试"""
        with patch('core.utils.llm_client.LLMClient._create_llm') as mock_create_llm:
            # 创建 Mock LLM
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm

            # 第一次调用超时，第二次成功
            mock_llm.invoke.side_effect = [
                httpx.TimeoutException("Connection timeout"),
                MagicMock(content="Success response")
            ]

            # Mock 配置
            with patch('core.models.get_settings') as mock_settings:
                mock_settings.return_value = MagicMock(
                    llm_api_key="test_key",
                    llm_model="gpt-3.5-turbo",
                    llm_base_url=None,
                    llm_temperature=0.7,
                    llm_max_tokens=4096,
                    llm_retry_attempts=3,
                    llm_retry_delay=0.1
                )

                client = LLMClient()
                result = client.chat([{"role": "user", "content": "test"}])

                assert result == "Success response"
                assert mock_llm.invoke.call_count == 2, "应该重试一次"

    def test_retry_on_connect_error(self):
        """测试连接错误时触发重试"""
        with patch('core.utils.llm_client.LLMClient._create_llm') as mock_create_llm:
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm

            # 第一次连接错误，第二次成功
            mock_llm.invoke.side_effect = [
                httpx.ConnectError("Connection failed"),
                MagicMock(content="Success response")
            ]

            with patch('core.models.get_settings') as mock_settings:
                mock_settings.return_value = MagicMock(
                    llm_api_key="test_key",
                    llm_model="gpt-3.5-turbo",
                    llm_base_url=None,
                    llm_temperature=0.7,
                    llm_max_tokens=4096,
                    llm_retry_attempts=3,
                    llm_retry_delay=0.1
                )

                client = LLMClient()
                result = client.chat([{"role": "user", "content": "test"}])

                assert result == "Success response"
                assert mock_llm.invoke.call_count == 2

    def test_max_retries_exceeded(self):
        """测试超过最大重试次数后抛出异常"""
        with patch('core.utils.llm_client.LLMClient._create_llm') as mock_create_llm:
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm

            # 所有调用都超时
            mock_llm.invoke.side_effect = httpx.TimeoutException("Connection timeout")

            with patch('core.models.get_settings') as mock_settings:
                mock_settings.return_value = MagicMock(
                    llm_api_key="test_key",
                    llm_model="gpt-3.5-turbo",
                    llm_base_url=None,
                    llm_temperature=0.7,
                    llm_max_tokens=4096,
                    llm_retry_attempts=2,  # 最多重试2次
                    llm_retry_delay=0.1
                )

                client = LLMClient()

                with pytest.raises(httpx.TimeoutException):
                    client.chat([{"role": "user", "content": "test"}])

                # stop_after_attempt(2) 表示最多尝试 2 次
                assert mock_llm.invoke.call_count == 2


class TestTokenTracking:
    """Token 追踪集成测试"""

    def test_token_tracking_on_chat_response(self):
        """测试 chat 方法返回 ChatResponse 时记录 Token"""
        tracker = get_token_tracker()
        tracker.reset()

        with patch('core.utils.llm_client.LLMClient._create_llm') as mock_create_llm:
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm

            # 模拟带有 token 使用信息的响应
            mock_response = MagicMock()
            mock_response.content = "Test response"
            mock_response.response_metadata = {
                "token_usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 30,
                    "total_tokens": 80
                }
            }
            mock_llm.invoke.return_value = mock_response

            with patch('core.models.get_settings') as mock_settings:
                mock_settings.return_value = MagicMock(
                    llm_api_key="test_key",
                    llm_model="gpt-3.5-turbo",
                    llm_base_url=None,
                    llm_temperature=0.7,
                    llm_max_tokens=4096,
                    llm_retry_attempts=3,
                    llm_retry_delay=0.1
                )

                client = LLMClient()
                response = client.chat([{"role": "user", "content": "test"}], return_response=True)

                assert isinstance(response, ChatResponse)
                assert response.usage.prompt_tokens == 50
                assert tracker.total_prompt_tokens == 50
                assert tracker.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
