"""使用 dashscope 原生SDK测试连接"""
import os
from dotenv import load_dotenv
import dashscope
from dashscope import Generation


def test_dashscope_native():
    """使用 dashscope 原生SDK测试"""
    load_dotenv()
    
    print("=" * 60)
    print("阿里云百炼 Coding Plan 连接测试（原生SDK）")
    print("=" * 60)
    
    api_key = os.getenv("DASHSCOPE_API_KEY")
    
    if not api_key:
        print("❌ 错误: 未找到 DASHSCOPE_API_KEY")
        return
    
    print(f"\n✓ API密钥: {api_key[:15]}...{api_key[-5:]}")
    
    # 设置API密钥
    dashscope.api_key = api_key
    
    # Coding Plan 模型列表
    models = [
        "qwen3-coder-plus",
        "qwen3.5-plus", 
        "qwen-max",
    ]
    
    print(f"\n[测试模型]")
    
    success_models = []
    
    for model in models:
        print(f"\n{'='*60}")
        print(f"测试: {model}")
        print(f"{'='*60}")
        
        try:
            response = Generation.call(
                model=model,
                prompt="请简单回复：测试成功",
                max_tokens=50
            )
            
            if response.status_code == 200:
                result = response.output.text
                print(f"✓ 成功！")
                print(f"响应: {result}")
                success_models.append(model)
            else:
                print(f"✗ 失败")
                print(f"错误码: {response.code}")
                print(f"错误信息: {response.message}")
                
        except Exception as e:
            print(f"✗ 失败")
            print(f"错误: {e}")
    
    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    
    if success_models:
        print(f"\n✓ 可用模型 ({len(success_models)}个):")
        for model in success_models:
            print(f"  - {model}")
        
        print(f"\n推荐使用: {success_models[0]}")
        print(f"\n下一步:")
        print(f"1. 更新 .env: LLM_MODEL={success_models[0]}")
        print(f"2. 运行: python main.py")
    else:
        print("\n❌ 没有可用的模型")
        print("\n请检查:")
        print("1. API密钥是否正确")
        print("2. 是否购买了 Coding Plan")
        print("3. 网络连接是否正常")


if __name__ == "__main__":
    test_dashscope_native()
