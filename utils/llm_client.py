"""LLM客户端封装 - 支持阿里云百炼"""
import os
from typing import Dict, Any, List
import dashscope
from dashscope import Generation


class LLMClient:
    """统一的LLM客户端，支持阿里云百炼"""
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        初始化LLM客户端
        
        Args:
            api_key: API密钥
            model: 模型名称
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", "qwen-coder-plus")
        
        # 设置 dashscope API密钥
        dashscope.api_key = self.api_key
    
    def chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """
        调用聊天接口
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            模型响应内容
        """
        try:
            response = Generation.call(
                model=self.model,
                messages=messages,
                result_format='message',
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                raise Exception(f"API调用失败: {response.code} - {response.message}")
            
        except Exception as e:
            print(f"LLM调用失败: {e}")
            raise
    
    def chat_simple(self, prompt: str, **kwargs) -> str:
        """
        简化的聊天接口
        
        Args:
            prompt: 用户提示词
            **kwargs: 其他参数
            
        Returns:
            模型响应
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, **kwargs)


# 便捷函数
def get_llm_client() -> LLMClient:
    """获取LLM客户端实例"""
    return LLMClient()
