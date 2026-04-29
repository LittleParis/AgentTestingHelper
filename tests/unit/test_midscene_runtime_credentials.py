from core.automation.midscene_generator import MidsceneScriptGenerator


def test_generic_login_steps_use_runtime_credentials_in_script():
    generator = MidsceneScriptGenerator(use_llm=False)

    script = generator._generate_script_content(
        [
            {
                "id": "TC_001_001",
                "title": "登录主路径",
                "priority": "high",
                "steps": [
                    {
                        "action": "在用户名输入框中输入有效的用户标识符",
                        "data": "",
                        "expected": "用户名输入框显示已输入内容",
                    },
                    {
                        "action": "在密码输入框中输入有效的密码",
                        "data": "",
                        "expected": "密码输入框显示已输入内容",
                    },
                    {
                        "action": "点击登录按钮提交登录请求",
                        "data": "",
                        "expected": "登录请求提交成功",
                    },
                ],
                "expected": "登录成功",
                "tags": ["smoke"],
            }
        ],
        "https://example.com/login",
        scenario_config={
            "credentials": {
                "username_env": "LOGIN_USERNAME",
                "password_env": "LOGIN_PASSWORD",
            }
        },
    )

    assert 'const runtimeUsername = process.env["LOGIN_USERNAME"] ?? \'\';' in script
    assert 'const runtimePassword = process.env["LOGIN_PASSWORD"] ?? \'\';' in script
    assert "await identifierInput.fill(runtimeUsername ||" in script
    assert "await passwordInput.fill(runtimePassword ||" in script
    assert "await submitButton.click();" in script
    assert 'await identifierInput.fill("test")' not in script
