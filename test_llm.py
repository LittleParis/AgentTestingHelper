"""测试LLM连接"""
import os
from dotenv import load_dotenv
from utils.llm_client import get_llm_client


def test_connection():
    """测试LLM连接"""
    load_dotenv()
    
    print("=" * 60)
    print("测试阿里云百炼连接")
    print("=" * 60)
    
    # 检查环境变量
    api_key = os.getenv("DASHSCOPE_API_KEY")
    model = os.getenv("LLM_MODEL", "qwen3-coder-plus")
    
    if not api_key:
        print("❌ 错误: 未找到 DASHSCOPE_API_KEY")
        print("请在 .env 文件中配置你的API密钥")
        return
    
    print(f"✓ API密钥: {api_key[:10]}...")
    print(f"✓ 模型: {model}")
    
    # 测试调用
    print("\n正在测试LLM调用...")
    
    try:
        llm = get_llm_client()
        
        response = llm.chat_simple(
            "请用JSON格式输出：{\"status\": \"success\", \"message\": \"连接成功\"}",
            temperature=0.1,
            max_tokens=100
        )
        
        print("\n✓ LLM响应:")
        print(response)
        print("\n" + "=" * 60)
        print("✓ 连接测试成功！")
        print("=" * 60)
        print("\n你现在可以运行: python main.py")
        
    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        print("\n请检查:")
        print("1. API密钥是否正确")
        print("2. 网络连接是否正常")
        print("3. 模型权限是否开通")


if __name__ == "__main__":
    test_connection()
