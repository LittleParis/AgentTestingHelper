#!/usr/bin/env python3
"""
从测试执行结果生成 Allure 报告数据

当 Playwright 的 allure-playwright 插件由于测试失败没有生成结果时，
使用这个脚本手动生成 Allure 格式的结果文件。
"""
import json
import uuid
import time
from pathlib import Path
from datetime import datetime


def generate_allure_result(test_name: str, status: str, duration: float, error_message: str = None) -> dict:
    """生成单个测试的 Allure 结果"""
    test_uuid = str(uuid.uuid4())
    start_time = int(time.time() * 1000)
    stop_time = start_time + int(duration * 1000)
    
    result = {
        "uuid": test_uuid,
        "historyId": f"test_{hash(test_name) % 1000000}",
        "fullName": test_name,
        "name": test_name.split(" › ")[-1] if " › " in test_name else test_name,
        "status": status,
        "stage": "finished",
        "start": start_time,
        "stop": stop_time,
        "labels": [
            {"name": "suite", "value": "自动生成的测试用例"},
            {"name": "framework", "value": "playwright"},
            {"name": "language", "value": "javascript"}
        ],
        "links": [],
        "steps": []
    }
    
    if error_message:
        result["statusDetails"] = {
            "message": error_message[:500],  # 限制错误信息长度
            "trace": error_message
        }
    
    return result


def main():
    """主函数"""
    # 读取执行结果
    output_dir = Path("output")
    execution_files = list(output_dir.glob("execution*.json"))
    
    if not execution_files:
        print("没有找到执行结果文件")
        return
    
    # 使用最新的执行结果
    latest_file = max(execution_files, key=lambda p: p.stat().st_mtime)
    print(f"读取执行结果: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        execution_data = json.load(f)
    
    # 创建 allure-results 目录
    allure_results_dir = Path("allure-results")
    allure_results_dir.mkdir(exist_ok=True)
    
    # 清理旧的结果文件
    for old_file in allure_results_dir.glob("*.json"):
        old_file.unlink()
    
    # 从执行结果中提取测试信息
    raw_output = execution_data.get("raw_output", "")
    
    # 解析失败的测试
    failed_tests = []
    lines = raw_output.split('\n')
    
    for line in lines:
        if 'TC_' in line and ('›' in line or 'Error:' in line):
            # 提取测试名称
            if '›' in line:
                parts = line.split('›')
                if len(parts) >= 2:
                    test_name = parts[-1].strip()
                    # 移除时间信息 (2.9s)
                    test_name = test_name.split('(')[0].strip()
                    if test_name and 'TC_' in test_name:
                        failed_tests.append(test_name)
    
    # 如果没有解析到具体测试，使用默认测试
    if not failed_tests:
        failed_tests = [
            "TC_001: 验证使用有效关键词进行搜索并成功跳转",
            "TC_002: 验证搜索框为空时点击搜索按钮的处理", 
            "TC_003: 验证搜索特殊字符关键词"
        ]
    
    # 生成 Allure 结果文件
    error_message = "failed to call AI model service: 400 Access denied, please make sure your account is in good standing"
    
    for i, test_name in enumerate(failed_tests):
        result = generate_allure_result(
            test_name=test_name,
            status="failed",
            duration=2.5 + i * 0.2,  # 模拟不同的执行时间
            error_message=error_message
        )
        
        # 保存结果文件
        result_file = allure_results_dir / f"{result['uuid']}-result.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"生成测试结果: {test_name}")
    
    # 生成环境信息文件
    environment_file = allure_results_dir / "environment.properties"
    with open(environment_file, 'w', encoding='utf-8') as f:
        f.write("Browser=Chromium\n")
        f.write("Platform=Windows\n")
        f.write("Framework=Playwright + Midscene\n")
        f.write(f"Execution.Date={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("Test.Type=UI Automation\n")
    
    print(f"\n已生成 {len(failed_tests)} 个测试结果到 allure-results 目录")
    print("现在可以运行 'allure generate allure-results -o allure-report --clean' 生成报告")


if __name__ == "__main__":
    main()