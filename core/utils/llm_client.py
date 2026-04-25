"""LLM客户端封装 - 基于LangChain"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
import httpx
import threading

# 临时修复：使用已安装的包
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    # 如果langchain_openai不可用，使用基础的langchain
    from langchain.chat_models import ChatOpenAI

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate

# 重试机制
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import logging

from core.utils.project_paths import LLM_DIAGNOSTICS_DIR, ensure_runtime_directories

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class FinishReason(str, Enum):
    """完成原因枚举"""
    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    FUNCTION_CALL = "function_call"
    TOOL_CALLS = "tool_calls"


class Message(BaseModel):
    """
    消息类型定义 - Pydantic 版本
    """
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")

    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式"""
        return {"role": self.role.value, "content": self.content}

    def to_langchain_message(self) -> BaseMessage:
        """转换为LangChain消息类型"""
        if self.role == MessageRole.SYSTEM:
            return SystemMessage(content=self.content)
        elif self.role == MessageRole.ASSISTANT:
            return AIMessage(content=self.content)
        else:
            return HumanMessage(content=self.content)

    @classmethod
    def system(cls, content: str) -> "Message":
        """创建系统消息"""
        return cls(role=MessageRole.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> "Message":
        """创建用户消息"""
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(cls, content: str) -> "Message":
        """创建助手消息"""
        return cls(role=MessageRole.ASSISTANT, content=content)


class TokenUsage(BaseModel):
    """Token使用统计"""
    prompt_tokens: int = Field(default=0, ge=0, description="输入token数")
    completion_tokens: int = Field(default=0, ge=0, description="输出token数")
    total_tokens: int = Field(default=0, ge=0, description="总token数")


class ChatResponse(BaseModel):
    """
    聊天响应类型定义 - Pydantic 版本
    """
    content: str = Field(..., description="响应内容")
    model: str = Field(default="", description="使用的模型名称")
    usage: Optional[TokenUsage] = Field(default=None, description="Token使用情况")
    finish_reason: FinishReason = Field(default=FinishReason.STOP, description="完成原因")
    response_time: float = Field(default=0.0, ge=0, description="响应时间(秒)")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    @property
    def total_tokens(self) -> int:
        """兼容旧接口：获取总token数"""
        return self.usage.total_tokens if self.usage else 0


class StructuredOutputError(Exception):
    """结构化输出失败时的统一异常。"""

    def __init__(
        self,
        message: str,
        *,
        diagnostics_path: Optional[str] = None,
        raw_response_preview: Optional[str] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.diagnostics_path = diagnostics_path
        self.raw_response_preview = raw_response_preview
        self.original_exception = original_exception

    def __str__(self) -> str:
        base = super().__str__()
        if self.diagnostics_path:
            base += f" | diagnostics={self.diagnostics_path}"
        return base


class TokenTracker:
    """
    全局 Token 使用追踪器

    线程安全的单例，用于统计整个会话的 Token 消耗。
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._call_count = 0
        self._lock = threading.Lock()

    def record(self, usage: TokenUsage) -> None:
        """记录一次调用的 Token 使用"""
        with self._lock:
            self._total_prompt_tokens += usage.prompt_tokens
            self._total_completion_tokens += usage.completion_tokens
            self._call_count += 1

    @property
    def total_prompt_tokens(self) -> int:
        """总输入 token 数"""
        with self._lock:
            return self._total_prompt_tokens

    @property
    def total_completion_tokens(self) -> int:
        """总输出 token 数"""
        with self._lock:
            return self._total_completion_tokens

    @property
    def total_tokens(self) -> int:
        """总 token 数"""
        return self.total_prompt_tokens + self.total_completion_tokens

    @property
    def call_count(self) -> int:
        """调用次数"""
        with self._lock:
            return self._call_count

    def get_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        return {
            "call_count": self.call_count,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
        }

    def reset(self) -> None:
        """重置统计"""
        with self._lock:
            self._total_prompt_tokens = 0
            self._total_completion_tokens = 0
            self._call_count = 0


# 全局 Token 追踪器实例
_token_tracker = None
_token_tracker_lock = threading.Lock()


def get_token_tracker() -> TokenTracker:
    """获取全局 Token 追踪器实例"""
    global _token_tracker
    if _token_tracker is None:
        with _token_tracker_lock:
            if _token_tracker is None:
                _token_tracker = TokenTracker()
    return _token_tracker


# 可重试的异常类型
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    ConnectionError,
)


class LLMClient:
    """统一的LLM客户端 - 支持OpenAI兼容API"""

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        base_url: str = None,
        temperature: float = None,
        max_tokens: int = None,
        retry_attempts: int = None,
        retry_delay: float = None
    ):
        """
        初始化LLM客户端

        Args:
            api_key: API密钥 (默认从配置读取)
            model: 模型名称 (默认从配置读取)
            base_url: API端点 (默认从配置读取)
            temperature: 温度参数
            max_tokens: 最大token数
            retry_attempts: 重试次数 (默认从配置读取)
            retry_delay: 重试延迟秒数 (默认从配置读取)
        """
        # 使用统一配置
        from core.models import get_settings
        settings = get_settings()

        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.base_url = base_url or settings.llm_base_url
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens
        self.retry_attempts = retry_attempts if retry_attempts is not None else settings.llm_retry_attempts
        self.retry_delay = retry_delay if retry_delay is not None else settings.llm_retry_delay
        self.use_env_proxy = self._parse_bool_env(
            os.getenv("LLM_USE_ENV_PROXY"),
            default=getattr(settings, "llm_use_env_proxy", False),
        )
        self.proxy_url = os.getenv("LLM_PROXY_URL") or getattr(settings, "llm_proxy_url", None)

        # 初始化 LangChain ChatOpenAI
        self._llm = self._create_llm()

        # Token 追踪器
        self._token_tracker = get_token_tracker()

    def _create_llm(self) -> ChatOpenAI:
        """创建LangChain LLM实例"""
        # 继承环境变量中的代理配置，便于在受限网络环境中访问模型服务。
        http_client = httpx.Client()

        kwargs = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "http_client": self._build_http_client(),
        }

        # 设置API密钥
        if self.api_key:
            kwargs["api_key"] = self.api_key

        # 设置自定义API端点 (阿里云百炼、DeepSeek等)
        if self.base_url:
            kwargs["base_url"] = self.base_url

        return ChatOpenAI(**kwargs)

    def _create_retry_decorator(self):
        """创建重试装饰器"""
        return retry(
            stop=stop_after_attempt(self.retry_attempts),
            wait=wait_exponential(multiplier=1, min=self.retry_delay, max=10),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )

    def _safe_preview(self, value: Any, max_length: int = 500) -> str:
        """生成适合日志展示的短预览。"""
        text = "" if value is None else str(value)
        text = text.replace("\r", " ").replace("\n", "\\n")
        if len(text) > max_length:
            return text[:max_length] + "...(truncated)"
        return text

    def _build_http_client(self) -> httpx.Client:
        """Build an HTTP client for text-model traffic with isolated proxy rules."""
        client_kwargs: Dict[str, Any] = {}
        if self.proxy_url:
            client_kwargs["proxy"] = self.proxy_url
        else:
            client_kwargs["trust_env"] = self.use_env_proxy
        return httpx.Client(**client_kwargs)

    def _parse_bool_env(self, value: Optional[str], default: bool) -> bool:
        """Parse a boolean environment variable with a safe default."""
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def _invoke_raw_prompt(self, prompt: str) -> str:
        """直接调用底层模型，获取原始文本响应用于诊断。"""
        response = self._llm.invoke([HumanMessage(content=prompt)])
        content = getattr(response, "content", "")
        if isinstance(content, list):
            return json.dumps(content, ensure_ascii=False)
        return str(content)

    def _write_structured_diagnostics(
        self,
        *,
        schema_name: str,
        operation: str,
        prompt: str,
        exception: Exception,
        raw_response: Optional[str] = None,
        raw_capture_error: Optional[str] = None,
    ) -> str:
        """将结构化输出失败的现场落盘，便于后续排查。"""
        ensure_runtime_directories()
        LLM_DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)

        safe_operation = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (operation or schema_name))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        diagnostics_path = LLM_DIAGNOSTICS_DIR / f"{timestamp}_{safe_operation}.json"

        payload = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "schema": schema_name,
            "model": self.model,
            "base_url": self.base_url,
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "prompt_length": len(prompt or ""),
            "prompt_preview": self._safe_preview(prompt, max_length=1200),
            "prompt": prompt,
            "raw_response_preview": self._safe_preview(raw_response, max_length=1200) if raw_response is not None else None,
            "raw_response": raw_response,
            "raw_capture_error": raw_capture_error,
        }

        with open(diagnostics_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

        return str(diagnostics_path)

    def invoke_structured(self, schema, prompt: str, operation: Optional[str] = None):
        """
        统一的结构化输出调用入口。

        失败时会自动记录诊断文件，并抛出带路径的 StructuredOutputError。
        """
        schema_name = getattr(schema, "__name__", str(schema))
        operation_name = operation or schema_name
        structured_llm = self._llm.with_structured_output(schema)

        try:
            result = structured_llm.invoke(prompt)
            if result is None:
                raise ValueError("Structured output returned None")
            logger.debug(
                "Structured output succeeded: operation=%s schema=%s model=%s",
                operation_name,
                schema_name,
                self.model,
            )
            return result
        except Exception as exc:
            logger.warning(
                "Structured output failed: operation=%s schema=%s model=%s error=%s",
                operation_name,
                schema_name,
                self.model,
                exc,
            )

            raw_response = None
            raw_capture_error = None
            try:
                raw_response = self._invoke_raw_prompt(prompt)
            except Exception as raw_exc:
                raw_capture_error = f"{type(raw_exc).__name__}: {raw_exc}"
                logger.warning(
                    "Structured output raw capture failed: operation=%s schema=%s error=%s",
                    operation_name,
                    schema_name,
                    raw_capture_error,
                )

            diagnostics_path = self._write_structured_diagnostics(
                schema_name=schema_name,
                operation=operation_name,
                prompt=prompt,
                exception=exc,
                raw_response=raw_response,
                raw_capture_error=raw_capture_error,
            )
            logger.warning(
                "Structured output diagnostics saved: operation=%s path=%s",
                operation_name,
                diagnostics_path,
            )

            raise StructuredOutputError(
                f"Structured output failed for {operation_name}: {exc}",
                diagnostics_path=diagnostics_path,
                raw_response_preview=self._safe_preview(raw_response),
                original_exception=exc,
            ) from exc

    def chat(
        self,
        messages: Union[List[Message], List[Dict[str, str]]],
        temperature: float = None,
        max_tokens: int = None,
        return_response: bool = False
    ) -> Union[str, ChatResponse]:
        """
        调用聊天接口（带重试机制）

        Args:
            messages: 消息列表，支持 Message 对象或字典格式
            temperature: 温度参数 (可选，覆盖默认值)
            max_tokens: 最大token数 (可选，覆盖默认值)
            return_response: 是否返回完整响应对象

        Returns:
            模型响应内容 或 ChatResponse 对象
        """
        # 转换消息格式
        lc_messages = []
        for msg in messages:
            if isinstance(msg, Message):
                lc_messages.append(msg.to_langchain_message())
            else:
                # 兼容字典格式
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                else:
                    lc_messages.append(HumanMessage(content=content))

        # 配置参数
        invoke_kwargs = {}
        if temperature is not None:
            invoke_kwargs["temperature"] = temperature
        if max_tokens is not None:
            invoke_kwargs["max_tokens"] = max_tokens

        # 带重试的调用
        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        def _invoke_with_retry():
            return self._llm.invoke(lc_messages, **invoke_kwargs)

        response = _invoke_with_retry()

        if return_response:
            # 构建完整响应
            usage = None
            if hasattr(response, "response_metadata"):
                token_usage = response.response_metadata.get("token_usage", {})
                if token_usage:
                    usage = TokenUsage(
                        prompt_tokens=token_usage.get("prompt_tokens", 0),
                        completion_tokens=token_usage.get("completion_tokens", 0),
                        total_tokens=token_usage.get("total_tokens", 0)
                    )
                    # 记录到追踪器
                    self._token_tracker.record(usage)

            return ChatResponse(
                content=response.content,
                model=self.model,
                usage=usage,
                finish_reason=FinishReason.STOP
            )

        return response.content

    def chat_simple(
        self,
        prompt: str,
        system_prompt: str = None,
        return_response: bool = False,
        **kwargs
    ) -> Union[str, ChatResponse]:
        """
        简化的聊天接口

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词 (可选)
            return_response: 是否返回完整响应对象
            **kwargs: 其他参数 (temperature, max_tokens等)

        Returns:
            模型响应内容 或 ChatResponse 对象
        """
        messages = []
        if system_prompt:
            messages.append(Message.system(system_prompt))
        messages.append(Message.user(prompt))

        return self.chat(messages, return_response=return_response, **kwargs)

    def chat_with_template(
        self,
        template: str,
        variables: Dict[str, Any],
        system_prompt: str = None
    ) -> str:
        """
        使用模板聊天

        Args:
            template: 提示词模板，使用 {variable} 占位符
            variables: 模板变量
            system_prompt: 系统提示词 (可选)

        Returns:
            模型响应
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt or "你是一个有帮助的AI助手。"),
            ("human", template)
        ])

        chain = prompt | self._llm
        response = chain.invoke(variables)
        return response.content

    def with_structured_output(self, schema):
        """
        绑定 Pydantic 模型，让 LLM 直接返回结构化输出

        Args:
            schema: Pydantic 模型类

        Returns:
            绑定了 schema 的 LLM 链

        Example:
            llm = get_llm_client()
            structured_llm = llm.with_structured_output(RequirementAnalysisResult)
            result = structured_llm.invoke(prompt)  # 直接返回 Pydantic 对象
        """
        return self._llm.with_structured_output(schema)

    @property
    def llm(self) -> ChatOpenAI:
        """获取底层LangChain LLM实例，用于LangGraph集成"""
        return self._llm

    @property
    def token_tracker(self) -> TokenTracker:
        """获取 Token 追踪器"""
        return self._token_tracker


# 单例 LLMClient
_client_instance = None
_client_lock = threading.Lock()


def get_llm_client() -> LLMClient:
    """
    获取LLM客户端实例（单例模式）

    线程安全的单例实现，确保整个应用共享同一个客户端实例。
    """
    global _client_instance
    if _client_instance is None:
        with _client_lock:
            if _client_instance is None:
                _client_instance = LLMClient()
    return _client_instance


def reset_llm_client() -> None:
    """
    重置 LLM 客户端单例

    用于测试或需要重新初始化客户端的场景。
    """
    global _client_instance
    with _client_lock:
        _client_instance = None
