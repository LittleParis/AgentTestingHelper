
"""调试LLM连接 - 详细版本"""
import os
from dotenv import load_dotenv
from openai import OpenAI


def test_connection_debug():
    """详细测试LLM连接"""
    load_dotenv()

    print("=" * 60)
    print("LLM 连接调试")
    print("=" * 60)

    # 检查环境变量
    api_key = os.getenv("LLM_KEY")
    model = os.getenv("LLM_MODEL", "")
    base_url = os.getenv("LLM_BASE_URL", "")

    print(f"\n[配置信息]")
    print(f"API密钥: {api_key[:15]}...{api_key[-5:] if api_key else 'None'}")
    print(f"模型名称: {model}")
    if base_url:
        print(f"Base URL: {base_url}")

    if not api_key:
        print("\n❌ 错误: 未找到 LLM_KEY")
        return

    if not model:
        print("\n❌ 错误: 未找到 LLM_MODEL")
        print("请在 .env 中设置: LLM_MODEL=your_model_name")
        return

    print(f"\n[开始测试]")
    print(f"测试模型: {model}")

    try:
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = OpenAI(**client_kwargs)

        print(f"发送测试请求...")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "你好，请回复：测试成功"}
            ],
            temperature=0.1,
            max_tokens=50
        )

        result = response.choices[0].message.content
        print(f"✓ 成功！")
        print(f"响应: {result}")
        print(f"\n推荐使用此模型: {model}")

    except Exception as e:
        error_msg = str(e)
        print(f"✗ 失败")
        print(f"错误: {error_msg}")

        # 分析错误
        if "Invalid API-key" in error_msg or "authentication" in error_msg.lower():
            print("  → API密钥无效或已过期")
        elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            print(f"  → 模型 {model} 不可用")
        elif "quota" in error_msg.lower():
            print("  → 配额不足")
        else:
            print("  → 其他错误，请检查网络或联系客服")

    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")

    print("\n[下一步]")
    print("1. 如果测试失败，请检查:")
    print("   - API密钥是否正确")
    print("   - 模型名称是否正确")
    print("   - 网络是否正常")
    print("\n2. 如果测试成功，运行: python main.py")


if __name__ == "__main__":
    test_connection_debug()
