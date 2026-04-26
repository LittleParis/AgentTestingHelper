"""Workflow utility functions."""

from typing import Any, Dict, List, Optional

from core.models.workflow import AgentState


def build_executor_env_overrides(scenario_config: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Map runtime credential values onto the env var names used by the generated script."""
    if not scenario_config:
        return {}

    credentials = scenario_config.get("credentials") or {}
    if not credentials:
        return {}

    username_value = credentials.get("username_value")
    password_value = credentials.get("password_value")
    username_env = str(credentials.get("username_env") or "LOGIN_USERNAME")
    password_env = str(credentials.get("password_env") or "LOGIN_PASSWORD")

    env_overrides: Dict[str, str] = {}
    if username_value is not None:
        env_overrides[username_env] = str(username_value)
    if password_value is not None:
        env_overrides[password_env] = str(password_value)

    return env_overrides


def get_improvement_hints(state: AgentState) -> Optional[List[str]]:
    """Limit review feedback before passing it back into the generator."""
    iteration = state.get("iteration_count", 0)
    review_suggestions = state.get("review_suggestions") or []

    if iteration <= 0 or not review_suggestions:
        return None

    max_hints = 5
    return review_suggestions[:max_hints]