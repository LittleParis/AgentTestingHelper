"""测试阿里云百炼 Coding Plan 连接"""
import os
from dotenv import load_dotenv
from openai import OpenAI


def test_coding_plan():
    """测试 Coding Plan 可用模型"""
    load_dotenv()
    
    print("=" * 60)
    print("阿里云百炼 Coding Plan 连接测试")
    print("=" * 60)
    
    api_key = os.getenv("DASHSCOPE_API_KEY")
    
    if not api_key:
        print("❌ 错误: 未找到 DASHSCOPE_API_KEY")
        return
    
    print(f"\n✓ API密钥: {api_key[:15]}...{api_key[-5:]}")
    print(f"✓ Base URL: https://dashscope.aliyuncs.com/compatible-mode/v1")
    
    # Coding Plan 包含的模型
    coding_plan_models = [
        ("qwen3-coder-plus", "通义千问编程版（推荐用于代码生成）"),
        ("qwen3.5-plus", "通义千问3.5 Plus（通用能力强）"),
        ("qwen3-max", "通义千问Max（最强）"),
        ("glm-5", "智谱GLM-5"),
    ]
    
    print(f"\n[测试 Coding Plan 模型]")
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    success_models = []
    
    for model_name, description in coding_plan_models:
        print(f"\n{'='*60}")
        print(f"测试: {model_name}")
        print(f"说明: {description}")
        print(f"{'='*60}")
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": "请简单回复：测试成功"}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            result = response.choices[0].message.content
            print(f"✓ 成功！")
            print(f"响应: {result}")
            success_models.append(model_name)
            
        except Exception as e:
            error_msg = str(e)
            print(f"✗ 失败")
            print(f"错误: {error_msg}")
            
            if "Invalid API-key" in error_msg:
                print("  → API密钥无效")
                break
            elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                print(f"  → 模型未开通（可能需要在百炼控制台开通）")
            elif "quota" in error_msg.lower() or "insufficient" in error_msg.lower():
                print("  → 配额不足")
    
    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    
    if success_models:
        print(f"\n✓ 可用模型 ({len(success_models)}个):")
        for model in success_models:
            print(f"  - {model}")
        
        print(f"\n推荐配置 (.env):")
        print(f"LLM_MODEL={success_models[0]}")
        
        print(f"\n下一步:")
        print(f"1. 更新 .env 文件中的 LLM_MODEL")
        print(f"2. 运行: python main.py")
    else:
        print("\n❌ 没有可用的模型")
        print("\n请检查:")
        print("1. 是否已购买 Coding Plan 套餐")
        print("2. API密钥是否正确")
        print("3. 是否在百炼控制台开通了模型权限")
        print("\n访问: https://bailian.console.aliyun.com/")


if __name__ == "__main__":
    test_coding_plan()
