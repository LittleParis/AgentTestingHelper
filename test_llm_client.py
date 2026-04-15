"""测试 LLM 客户端基本功能"""
import sys
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

from utils.llm_client import LLMClient, Message, ChatResponse, get_llm_client


def test_basic_chat():
    """测试基本聊天功能"""
    print("=" * 50)
    print("测试1: 基本聊天 (chat_simple)")
    print("=" * 50)

    client = get_llm_client()
    print(f"模型: {client.model}")
    print(f"API端点: {client.base_url}")
    print()

    try:
        response = client.chat_simple("你好，请用一句话介绍自己")
        print(f"响应: {response}")
        print("✓ 测试通过")
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

    return True


def test_message_type():
    """测试 Message 类型"""
    print("\n" + "=" * 50)
    print("测试2: 使用 Message 类型")
    print("=" * 50)

    client = get_llm_client()

    messages = [
        Message.system("你是一个测试工程师，回答要简洁"),
        Message.user("什么是单元测试？")
    ]

    try:
        response = client.chat(messages)
        print(f"响应: {response}")
        print("✓ 测试通过")
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

    return True


def test_full_response():
    """测试完整响应"""
    print("\n" + "=" * 50)
    print("测试3: 获取完整响应 (含 token 消耗)")
    print("=" * 50)

    client = get_llm_client()

    try:
        response = client.chat_simple("你好", return_response=True)

        if isinstance(response, ChatResponse):
            print(f"内容: {response.content}")
            print(f"模型: {response.model}")
            print(f"Token: {response.total_tokens}")
            print("✓ 测试通过")
        else:
            print("✗ 返回类型错误")
            return False

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

    return True


def test_template():
    """测试模板聊天"""
    print("\n" + "=" * 50)
    print("测试4: 模板聊天")
    print("=" * 50)

    client = get_llm_client()

    try:
        response = client.chat_with_template(
            template="请为 {feature} 功能生成 {count} 个测试用例标题",
            variables={"feature": "用户登录", "count": 3},
            system_prompt="你是测试用例专家，回答要简洁"
        )
        print(f"响应: {response}")
        print("✓ 测试通过")
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

    return True


def main():
    """运行所有测试"""
    print("LLM 客户端测试")
    print("=" * 50)

    results = []
    results.append(("基本聊天", test_basic_chat()))
    results.append(("Message类型", test_message_type()))
    results.append(("完整响应", test_full_response()))
    results.append(("模板聊天", test_template()))

    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)

    passed = 0
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{len(results)} 通过")

    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
