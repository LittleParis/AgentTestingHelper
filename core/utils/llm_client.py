"""LLM客户端封装 - 基于LangChain"""
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
import httpx

# 临时修复：使用已安装的包
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    # 如果langchain_openai不可用，使用基础的langchain
    from langchain.chat_models import ChatOpenAI

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate


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


class LLMClient:
    """统一的LLM客户端 - 支持OpenAI兼容API"""

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        base_url: str = None,
        temperature: float = None,
        max_tokens: int = None
    ):
        """
        初始化LLM客户端

        Args:
            api_key: API密钥 (默认从配置读取)
            model: 模型名称 (默认从配置读取)
            base_url: API端点 (默认从配置读取)
            temperature: 温度参数
            max_tokens: 最大token数
        """
        # 使用统一配置
        from core.models import get_settings
        settings = get_settings()

        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.base_url = base_url or settings.llm_base_url
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

        # 初始化 LangChain ChatOpenAI
        self._llm = self._create_llm()

    def _create_llm(self) -> ChatOpenAI:
        """创建LangChain LLM实例"""
        # 创建不使用代理的 HTTP 客户端
        http_client = httpx.Client(proxy=None)

        kwargs = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "http_client": http_client,
        }

        # 设置API密钥
        if self.api_key:
            kwargs["api_key"] = self.api_key

        # 设置自定义API端点 (阿里云百炼、DeepSeek等)
        if self.base_url:
            kwargs["base_url"] = self.base_url

        return ChatOpenAI(**kwargs)

    def chat(
        self,
        messages: Union[List[Message], List[Dict[str, str]]],
        temperature: float = None,
        max_tokens: int = None,
        return_response: bool = False
    ) -> Union[str, ChatResponse]:
        """
        调用聊天接口

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

        # 调用模型
        response = self._llm.invoke(lc_messages, **invoke_kwargs)

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

    @property
    def llm(self) -> ChatOpenAI:
        """获取底层LangChain LLM实例，用于LangGraph集成"""
        return self._llm


# 便捷函数
def get_llm_client() -> LLMClient:
    """获取LLM客户端实例"""
    return LLMClient()
