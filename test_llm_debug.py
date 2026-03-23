"""调试LLM连接 - 详细版本"""
import os
from dotenv import load_dotenv
from openai import OpenAI


def test_connection_debug():
    """详细测试LLM连接"""
    load_dotenv()
    
    print("=" * 60)
    print("阿里云百炼连接调试")
    print("=" * 60)
    
    # 检查环境变量
    api_key = os.getenv("DASHSCOPE_API_KEY")
    model = os.getenv("LLM_MODEL", "qwen-plus")
    
    print(f"\n[配置信息]")
    print(f"API密钥: {api_key[:15]}...{api_key[-5:] if api_key else 'None'}")
    print(f"模型名称: {model}")
    print(f"Base URL: https://dashscope.aliyuncs.com/compatible-mode/v1")
    
    if not api_key:
        print("\n❌ 错误: 未找到 DASHSCOPE_API_KEY")
        return
    
    # 测试不同的模型
    models_to_test = [
        "qwen-plus",           # 通义千问Plus
        "qwen-coder-plus",     # 通义千问编程版
        "qwen-max",            # 通义千问Max
    ]
    
    print(f"\n[开始测试]")
    print(f"将测试以下模型（按顺序）:")
    for m in models_to_test:
        print(f"  - {m}")
    
    for test_model in models_to_test:
        print(f"\n{'='*60}")
        print(f"测试模型: {test_model}")
        print(f"{'='*60}")
        
        try:
            client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            print(f"发送测试请求...")
            response = client.chat.completions.create(
                model=test_model,
                messages=[
                    {"role": "user", "content": "你好，请回复：测试成功"}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            result = response.choices[0].message.content
            print(f"✓ 成功！")
            print(f"响应: {result}")
            print(f"\n推荐使用此模型: {test_model}")
            
            # 更新.env建议
            print(f"\n建议在.env中设置:")
            print(f"LLM_MODEL={test_model}")
            break
            
        except Exception as e:
            error_msg = str(e)
            print(f"✗ 失败")
            print(f"错误: {error_msg}")
            
            # 分析错误
            if "Invalid API-key" in error_msg or "authentication" in error_msg.lower():
                print("  → API密钥无效或已过期")
            elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                print(f"  → 模型 {test_model} 不可用（可能未开通权限）")
            elif "quota" in error_msg.lower():
                print("  → 配额不足")
            else:
                print("  → 其他错误，请检查网络或联系客服")
    
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")
    
    print("\n[下一步]")
    print("1. 如果所有模型都失败，请检查:")
    print("   - API密钥是否正确")
    print("   - 是否在百炼控制台开通了模型权限")
    print("   - 网络是否正常")
    print("\n2. 如果某个模型成功，更新.env中的LLM_MODEL")
    print("\n3. 然后运行: python test_llm.py")


if __name__ == "__main__":
    test_connection_debug()
