from main_v2 import (
    _hydrate_runtime_credentials,
    _inject_requirement_credentials,
    _maybe_enable_login_only_scenario,
)


REQUIREMENT_TEXT = """
## Credentials
- identifier_env: LOGIN_USERNAME
- password_env: LOGIN_PASSWORD
- identifier: sample_user@example.com
- password: sample-password-123
"""


def test_inject_requirement_credentials_merges_into_login_only_scenario():
    scenario_config = {
        "scenario_type": "login_only",
        "credentials": {
            "username_env": "LOGIN_USERNAME",
            "password_env": "LOGIN_PASSWORD",
        },
    }

    updated_config, extracted_credentials = _inject_requirement_credentials(
        scenario_config,
        REQUIREMENT_TEXT,
    )

    assert extracted_credentials == {
        "identifier": "sample_user@example.com",
        "password": "sample-password-123",
    }
    assert updated_config["scenario_type"] == "login_only"
    assert updated_config["credentials"]["username_env"] == "LOGIN_USERNAME"
    assert updated_config["credentials"]["password_env"] == "LOGIN_PASSWORD"
    assert updated_config["credentials"]["username_value"] == "sample_user@example.com"
    assert updated_config["credentials"]["password_value"] == "sample-password-123"


def test_inject_requirement_credentials_builds_runtime_config_when_missing():
    updated_config, extracted_credentials = _inject_requirement_credentials(
        None,
        REQUIREMENT_TEXT,
    )

    assert extracted_credentials["identifier"] == "sample_user@example.com"
    assert extracted_credentials["password"] == "sample-password-123"
    assert updated_config["credentials"]["username_env"] == "LOGIN_USERNAME"
    assert updated_config["credentials"]["password_env"] == "LOGIN_PASSWORD"
    assert updated_config["credentials"]["username_value"] == "sample_user@example.com"
    assert updated_config["credentials"]["password_value"] == "sample-password-123"


def test_inject_requirement_credentials_uses_env_names_from_requirement_document():
    updated_config, _ = _inject_requirement_credentials(
        None,
        """
        ## Credentials
        - identifier_env: ACCOUNT_RUNTIME_USER
        - password_env: ACCOUNT_RUNTIME_SECRET
        """,
    )

    assert updated_config["credentials"]["username_env"] == "ACCOUNT_RUNTIME_USER"
    assert updated_config["credentials"]["password_env"] == "ACCOUNT_RUNTIME_SECRET"
    assert "username_value" not in updated_config["credentials"]
    assert "password_value" not in updated_config["credentials"]


def test_inject_requirement_credentials_falls_back_to_dotenv_values(monkeypatch):
    monkeypatch.setenv("LOGIN_USERNAME", "dotenv-user@example.com")
    monkeypatch.setenv("LOGIN_PASSWORD", "dotenv-password-123")

    updated_config, extracted_credentials = _inject_requirement_credentials(
        None,
        """
        ## Credentials
        - identifier_env: LOGIN_USERNAME
        - password_env: LOGIN_PASSWORD
        """,
    )

    assert extracted_credentials == {"identifier": None, "password": None}
    assert updated_config["credentials"]["username_value"] == "dotenv-user@example.com"
    assert updated_config["credentials"]["password_value"] == "dotenv-password-123"


def test_inject_requirement_credentials_prefers_plaintext_over_dotenv(monkeypatch):
    monkeypatch.setenv("LOGIN_USERNAME", "dotenv-user@example.com")
    monkeypatch.setenv("LOGIN_PASSWORD", "dotenv-password-123")

    updated_config, extracted_credentials = _inject_requirement_credentials(None, REQUIREMENT_TEXT)

    assert extracted_credentials["identifier"] == "sample_user@example.com"
    assert extracted_credentials["password"] == "sample-password-123"
    assert updated_config["credentials"]["username_value"] == "sample_user@example.com"
    assert updated_config["credentials"]["password_value"] == "sample-password-123"


def test_hydrate_runtime_credentials_backfills_values_from_env(monkeypatch):
    monkeypatch.setenv("LOGIN_USERNAME", "dotenv-user@example.com")
    monkeypatch.setenv("LOGIN_PASSWORD", "dotenv-password-123")

    updated_config = _hydrate_runtime_credentials(
        {
            "scenario_type": "login_only",
            "credentials": {
                "username_env": "LOGIN_USERNAME",
                "password_env": "LOGIN_PASSWORD",
            },
        }
    )

    assert updated_config["credentials"]["username_value"] == "dotenv-user@example.com"
    assert updated_config["credentials"]["password_value"] == "dotenv-password-123"


def test_inject_requirement_credentials_augments_generic_scenario():
    scenario_config = {
        "scenario_type": "generic",
        "page_url": "https://example.com/login",
    }

    updated_config, extracted_credentials = _inject_requirement_credentials(
        scenario_config,
        REQUIREMENT_TEXT,
    )

    assert extracted_credentials["identifier"] == "sample_user@example.com"
    assert extracted_credentials["password"] == "sample-password-123"
    assert updated_config["scenario_type"] == "generic"
    assert updated_config["page_url"] == "https://example.com/login"
    assert updated_config["credentials"]["username_value"] == "sample_user@example.com"
    assert updated_config["credentials"]["password_value"] == "sample-password-123"


def test_maybe_enable_login_only_scenario_infers_from_explicit_requirement_file():
    scenario_config, extracted_credentials = _inject_requirement_credentials(
        None,
        REQUIREMENT_TEXT,
    )

    updated_config = _maybe_enable_login_only_scenario(
        scenario_config,
        "examples/requirement_login_only.md",
        REQUIREMENT_TEXT,
        "https://global.lianlianpay.com/signin",
        extracted_credentials,
    )

    assert updated_config["scenario_type"] == "login_only"
    assert updated_config["page_url"] == "https://global.lianlianpay.com/signin"
    assert updated_config["credentials"]["username_value"] == "sample_user@example.com"
    assert updated_config["credentials"]["password_value"] == "sample-password-123"


def test_maybe_enable_login_only_scenario_preserves_generic_scenario_when_signals_absent():
    scenario_config = {
        "credentials": {
            "username_env": "LOGIN_USERNAME",
            "password_env": "LOGIN_PASSWORD",
            "username_value": "sample_user@example.com",
            "password_value": "sample-password-123",
        }
    }

    updated_config = _maybe_enable_login_only_scenario(
        scenario_config,
        "examples/requirement_checkout.md",
        "# Checkout Journey",
        "https://example.com/checkout",
        {
            "identifier": "sample_user@example.com",
            "password": "sample-password-123",
        },
    )

    assert "scenario_type" not in updated_config
    assert updated_config["credentials"]["username_value"] == "sample_user@example.com"
