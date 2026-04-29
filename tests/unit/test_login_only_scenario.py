from core.automation.midscene_generator import MidsceneScriptGenerator


LOGIN_ONLY_SCENARIO = {
    "scenario_type": "login_only",
    "page_url": "https://global.lianlianpay.com/signin",
    "success_signal": {
        "type": "visual_text_or_logo",
        "value": "LianLian",
    },
    "manual_wait": True,
    "mfa_mode": "manual_wait",
    "forbidden_actions": [
        "menu_click",
        "navigation_after_login",
        "form_submit_other_than_login",
        "logout",
        "profile_edit",
    ],
    "manual_wait_timeout_ms": 180000,
}


def test_login_only_script_uses_runtime_credentials_and_stops_after_success():
    generator = MidsceneScriptGenerator(use_llm=False)

    script = generator._generate_script_content(
        [
            {
                "id": "TC_001",
                "title": "Successful login",
                "steps": [
                    {"action": "Open login page", "expected": "Login page loads"},
                    {
                        "action": "Submit credentials",
                        "data": "sample_user@example.com / sample-password-123",
                        "expected": "Logo appears",
                    },
                ],
                "expected": "LianLian logo is visible",
            }
        ],
        "https://global.lianlianpay.com/signin",
        scenario_config=LOGIN_ONLY_SCENARIO,
    )

    assert 'process.env["LOGIN_USERNAME"]' in script
    assert 'process.env["LOGIN_PASSWORD"]' in script
    assert "sample_user@example.com" not in script
    assert "sample-password-123" not in script
    assert "let maskedFields = [];" in script
    assert "maskedFields = [identifierInput, passwordInput];" in script
    assert "attachFinalScreenshot(page, testInfo, { mask: maskedFields })" in script
    assert "testInfo.attach(`final-screenshot-" in script
    assert "manual verification" in script.lower()
    assert "LianLian" in script
    assert script.count("click();") == 1
    assert "No further actions are allowed" in script
    assert "await ai(" not in script
    assert "Add identifier/password to the requirement file" in script


def test_login_only_script_collapses_multiple_cases_into_single_bounded_test():
    generator = MidsceneScriptGenerator(use_llm=False)

    script = generator._generate_script_content(
        [
            {"id": "TC_001", "title": "Login success", "steps": [], "expected": "ok"},
            {"id": "TC_002", "title": "Should not become a second login", "steps": [], "expected": "ok"},
        ],
        "https://global.lianlianpay.com/signin",
        scenario_config=LOGIN_ONLY_SCENARIO,
    )

    assert script.count("test(") == 1
    assert "TC_001" in script
    assert "TC_002" not in script
