import pytest
from unittest.mock import MagicMock

from core.utils.llm_client import LLMClient, StructuredOutputError


class DummySchema:
    __name__ = "DummySchema"


def make_client() -> LLMClient:
    client = object.__new__(LLMClient)
    client.temperature = 0.7
    client.model = "test-model"
    client.base_url = "https://example.com/v1"
    client._llm = MagicMock()
    client._create_llm = MagicMock()
    client._invoke_raw_prompt = MagicMock()
    client._write_structured_diagnostics = MagicMock()
    client._safe_preview = MagicMock(return_value="preview")
    return client


def test_invoke_structured_uses_override_temperature_when_provided():
    client = make_client()
    structured_runner = MagicMock()
    structured_runner.invoke.return_value = {"ok": True}
    override_llm = MagicMock()
    override_llm.with_structured_output.return_value = structured_runner
    client._create_llm.return_value = override_llm

    result = client.invoke_structured(
        DummySchema,
        "prompt",
        operation="requirement_analysis",
        temperature=0.1,
    )

    assert result == {"ok": True}
    client._create_llm.assert_called_once_with(temperature=0.1)
    override_llm.with_structured_output.assert_called_once_with(DummySchema)
    client._llm.with_structured_output.assert_not_called()


def test_invoke_structured_uses_default_llm_when_no_override_is_provided():
    client = make_client()
    structured_runner = MagicMock()
    structured_runner.invoke.return_value = {"ok": True}
    client._llm.with_structured_output.return_value = structured_runner

    result = client.invoke_structured(
        DummySchema,
        "prompt",
        operation="requirement_analysis",
    )

    assert result == {"ok": True}
    client._create_llm.assert_not_called()
    client._llm.with_structured_output.assert_called_once_with(DummySchema)


def test_invoke_structured_failure_does_not_request_raw_response_capture():
    client = make_client()
    structured_runner = MagicMock()
    structured_runner.invoke.side_effect = ValueError("boom")
    client._llm.with_structured_output.return_value = structured_runner
    client._write_structured_diagnostics.return_value = "diag.json"

    with pytest.raises(StructuredOutputError) as exc_info:
        client.invoke_structured(
            DummySchema,
            "prompt",
            operation="requirement_analysis",
        )

    client._invoke_raw_prompt.assert_not_called()
    client._write_structured_diagnostics.assert_called_once()
    _, kwargs = client._write_structured_diagnostics.call_args
    assert kwargs["schema_name"] == "DummySchema"
    assert kwargs["operation"] == "requirement_analysis"
    assert kwargs["prompt"] == "prompt"
    assert "raw_response" not in kwargs
    assert "raw_capture_error" not in kwargs
    assert exc_info.value.diagnostics_path == "diag.json"
    assert exc_info.value.raw_response_preview is None


def test_invoke_structured_failure_still_writes_lightweight_diagnostics():
    client = make_client()
    structured_runner = MagicMock()
    structured_runner.invoke.side_effect = RuntimeError("structured failed")
    client._llm.with_structured_output.return_value = structured_runner
    client._write_structured_diagnostics.return_value = "diag.json"

    with pytest.raises(StructuredOutputError):
        client.invoke_structured(DummySchema, "prompt")

    _, kwargs = client._write_structured_diagnostics.call_args
    assert kwargs["schema_name"] == "DummySchema"
    assert kwargs["operation"] == "DummySchema"
    assert kwargs["prompt"] == "prompt"
    assert isinstance(kwargs["exception"], RuntimeError)
