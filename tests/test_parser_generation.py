from __future__ import annotations

import importlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from unittest.mock import Mock

import httpx
import langchain_mistralai
import langchain_openai
import pytest
from _pytest.capture import CaptureFixture
from langchain_core.exceptions import OutputParserException
from pydantic import SecretStr

from aggregator import parser_generation
from aggregator.parser_configuration import TRANSACTION_FIELD_NAMES, FieldParserSet
from aggregator.parser_generation import (
    ParameterExample,
    ParameterExamples,
    _workflow,  # pyright: ignore[reportPrivateUsage]
)
from aggregator.parser_generation import __main__ as parser_generation_main

TEMPLATE = "Paid <CURRENCY_CODE> <NUMBER> from account <NUMBER> to <*>"
EXAMPLE: list[dict[str, object]] = [
    {"index": 0, "mask_name": "CURRENCY_CODE", "value": "Rs."},
    {"index": 1, "mask_name": "NUMBER", "value": "537.77"},
    {"index": 2, "mask_name": "NUMBER", "value": "6700"},
    {"index": 3, "mask_name": "*", "value": "paytm.d63608789@pty"},
]


def test_import_does_not_construct_chat_model(monkeypatch: pytest.MonkeyPatch) -> None:
    constructor = Mock(side_effect=AssertionError("Model constructed during import"))
    with monkeypatch.context() as context:
        context.setattr(langchain_openai, "ChatOpenAI", constructor)
        context.setattr(langchain_mistralai, "ChatMistralAI", constructor)
        importlib.reload(_workflow)
        importlib.reload(parser_generation)
        assert parser_generation.generate_field_parsers is _workflow.generate_field_parsers
        constructor.assert_not_called()
    importlib.reload(_workflow)
    importlib.reload(parser_generation)


@pytest.fixture
def parser_data() -> dict[str, object]:
    return {
        "amount": {"rule": "extracted", "parameter_indices": [1]},
        "currency_code": {"rule": "extracted", "parameter_indices": [0]},
        "payee": {"rule": "extracted", "parameter_indices": [3]},
        "description": {"rule": "missing"},
        "transaction_date": {"rule": "missing"},
        "account_hint": {"rule": "extracted", "parameter_indices": [2]},
        "is_credit": {"rule": "constant", "constant_value": "false"},
    }


@dataclass
class ModelEndpoint:
    constructor: Mock
    reply: Mock
    requests: list[dict[str, object]]


@pytest.fixture
def endpoint(monkeypatch: pytest.MonkeyPatch, parser_data: dict[str, object]) -> ModelEndpoint:
    """Exercise real LangChain/Pydantic parsing with an in-memory HTTP endpoint."""
    monkeypatch.setenv("PARSER_GENERATION_PROVIDER", "ollama")
    reply = Mock(return_value=json.dumps(parser_data))
    requests: list[dict[str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": f"completion-{len(requests)}",
                "object": "chat.completion",
                "created": 0,
                "model": "deepseek-r1",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": reply()},
                    }
                ],
            },
        )

    model = langchain_openai.ChatOpenAI(
        model="deepseek-r1",
        base_url="http://localhost:11434/v1",
        api_key=SecretStr("test"),
        http_client=httpx.Client(transport=httpx.MockTransport(handle)),
        max_retries=0,
    )
    constructor = Mock(return_value=model)
    monkeypatch.setattr(_workflow, "ChatOpenAI", constructor)
    return ModelEndpoint(constructor, reply, requests)


def test_generation_uses_pydantic_json_schema(
    monkeypatch: pytest.MonkeyPatch, endpoint: ModelEndpoint, parser_data: dict[str, object]
) -> None:
    load_dotenv = Mock()
    monkeypatch.setattr(_workflow, "load_dotenv", load_dotenv)
    result = parser_generation.generate_field_parsers(TEMPLATE, EXAMPLE)
    assert isinstance(result, FieldParserSet)
    assert result.model_dump() == parser_data
    load_dotenv.assert_called_once_with(
        dotenv_path=Path(_workflow.__file__).resolve().parents[3] / ".env"
    )
    endpoint.constructor.assert_called_once_with(
        model="deepseek-r1", base_url="http://localhost:11434/v1"
    )
    assert len(endpoint.requests) == 1
    request = endpoint.requests[0]
    response_format = cast(dict[str, object], request["response_format"])
    assert response_format["type"] == "json_schema"
    json_schema = cast(dict[str, object], response_format["json_schema"])
    schema = cast(dict[str, object], json_schema["schema"])
    assert set(cast(list[str], schema["required"])) == set(TRANSACTION_FIELD_NAMES)
    assert schema["additionalProperties"] is False
    assert "tools" not in request
    messages = cast(list[dict[str, str]], request["messages"])
    payload = json.loads(messages[0]["content"].split("Input JSON:\n", 1)[1])
    assert payload == {"template_text": TEMPLATE, "parameter_examples": [EXAMPLE]}


def test_ollama_is_the_default_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PARSER_GENERATION_PROVIDER", raising=False)
    assert _workflow._model_provider() == "ollama"  # pyright: ignore[reportPrivateUsage]


def test_mistral_provider_uses_api_key_and_retries_with_same_model(
    monkeypatch: pytest.MonkeyPatch, parser_data: dict[str, object]
) -> None:
    structured_model = Mock()
    structured_model.invoke.side_effect = [
        OutputParserException("invalid output"),
        _workflow.GeneratedFieldParsers.model_validate(parser_data),
    ]
    model = Mock()
    model.with_structured_output.return_value = structured_model
    constructor = Mock(return_value=model)
    handler = Mock()
    langfuse = Mock()
    monkeypatch.setenv("PARSER_GENERATION_PROVIDER", "mistral")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    monkeypatch.setattr(_workflow, "load_dotenv", Mock())
    monkeypatch.setattr(_workflow, "ChatMistralAI", constructor)
    monkeypatch.setattr(_workflow, "_langfuse_tracing", Mock(return_value=(handler, langfuse)))

    result = parser_generation.generate_field_parsers(TEMPLATE, EXAMPLE)

    assert result.model_dump() == parser_data
    constructor.assert_called_once_with(model_name="codestral-2508")
    model.with_structured_output.assert_called_once_with(
        _workflow.GeneratedFieldParsers, method="json_schema"
    )
    assert structured_model.invoke.call_count == 2
    langfuse.flush.assert_called_once()


@pytest.mark.parametrize(
    ("provider", "api_key", "message"),
    [
        ("unknown", "test-key", "PARSER_GENERATION_PROVIDER"),
        ("mistral", None, "MISTRAL_API_KEY"),
        ("mistral", "   ", "MISTRAL_API_KEY"),
    ],
)
def test_invalid_provider_configuration_fails_before_model_construction(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    api_key: str | None,
    message: str,
) -> None:
    ollama_constructor = Mock()
    mistral_constructor = Mock()
    monkeypatch.setenv("PARSER_GENERATION_PROVIDER", provider)
    if api_key is None:
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    else:
        monkeypatch.setenv("MISTRAL_API_KEY", api_key)
    monkeypatch.setattr(_workflow, "load_dotenv", Mock())
    monkeypatch.setattr(_workflow, "ChatOpenAI", ollama_constructor)
    monkeypatch.setattr(_workflow, "ChatMistralAI", mistral_constructor)
    tracing = Mock()
    monkeypatch.setattr(_workflow, "_langfuse_tracing", tracing)

    with pytest.raises(ValueError, match=message):
        parser_generation.generate_field_parsers(TEMPLATE, EXAMPLE)

    ollama_constructor.assert_not_called()
    mistral_constructor.assert_not_called()
    tracing.assert_not_called()


def test_generation_attaches_and_flushes_opt_in_langfuse_tracing(
    monkeypatch: pytest.MonkeyPatch, parser_data: dict[str, object]
) -> None:
    handler = Mock()
    langfuse = Mock()
    graph = Mock()
    graph.invoke.return_value = {"parsers": FieldParserSet.model_validate(parser_data)}
    monkeypatch.setattr(_workflow, "load_dotenv", Mock())
    monkeypatch.setattr(_workflow, "_build_graph", Mock(return_value=graph))
    monkeypatch.setattr(
        _workflow,
        "_langfuse_tracing",
        Mock(return_value=(handler, langfuse)),
    )

    result = parser_generation.generate_field_parsers(TEMPLATE, EXAMPLE)

    assert result.model_dump() == parser_data
    graph.invoke.assert_called_once()
    _, kwargs = graph.invoke.call_args
    assert kwargs["config"] == {
        "callbacks": [handler],
        "run_name": "generate-field-parsers",
    }
    langfuse.flush.assert_called_once()


def test_multiple_examples_and_explicit_indices(endpoint: ModelEndpoint) -> None:
    second = [dict(parameter) for parameter in EXAMPLE]
    second[1]["value"] = "100.00"
    examples = [list(reversed(EXAMPLE)), second]
    result = parser_generation.generate_field_parsers(TEMPLATE, examples)
    assert result.amount is not None
    messages = cast(list[dict[str, str]], endpoint.requests[0]["messages"])
    payload = json.loads(messages[0]["content"].split("Input JSON:\n", 1)[1])
    assert payload["parameter_examples"] == examples


def test_accepts_parameter_models(endpoint: ModelEndpoint) -> None:
    parameters = [ParameterExample.model_validate(parameter) for parameter in EXAMPLE]
    parser_generation.generate_field_parsers(TEMPLATE, parameters)
    assert len(endpoint.requests) == 1


INVALID_INPUTS: list[tuple[object, object]] = [
    (" \n", EXAMPLE),
    (None, EXAMPLE),
    (TEMPLATE, []),
    (TEMPLATE, [[]]),
    (TEMPLATE, EXAMPLE[:-1]),
    (TEMPLATE, [*EXAMPLE, EXAMPLE[0]]),
    (TEMPLATE, [["Rs.", "537.77", "6700", "paytm.d63608789@pty"]]),
    (TEMPLATE, "invalid"),
    (TEMPLATE, [EXAMPLE, []]),
]


@pytest.mark.parametrize(("template", "examples"), INVALID_INPUTS)
def test_invalid_input_fails_before_inference(
    endpoint: ModelEndpoint, template: object, examples: object
) -> None:
    with pytest.raises(ValueError):
        parser_generation.generate_field_parsers(
            cast(str, template), cast(ParameterExamples, examples)
        )
    endpoint.constructor.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("index", -1),
        ("index", 4),
        ("index", 1),
        ("index", True),
        ("index", "0"),
        ("mask_name", "NUMBER"),
        ("value", None),
        ("value", 10),
        ("extra", "unexpected"),
    ],
)
def test_invalid_parameter_objects_fail_before_inference(
    endpoint: ModelEndpoint, field: str, value: object
) -> None:
    invalid = [dict(parameter) for parameter in EXAMPLE]
    invalid[0][field] = value
    with pytest.raises(ValueError):
        parser_generation.generate_field_parsers(TEMPLATE, invalid)
    endpoint.constructor.assert_not_called()


@pytest.mark.parametrize(
    "invalid_configuration",
    [
        None,
        {"rule": "unknown"},
        {"rule": "extracted", "parameter_indices": [4]},
        {"rule": "extracted", "parameter_indices": [-1]},
        {"rule": "extracted", "parameter_indices": [True]},
        {"rule": "extracted", "parameter_indices": [1, 1]},
        {"rule": "extracted", "parameter_indices": []},
        {"rule": "constant", "constant_value": False},
        {"rule": "missing", "constant_value": "10"},
    ],
)
def test_invalid_configuration_is_corrected_with_same_model(
    endpoint: ModelEndpoint, parser_data: dict[str, object], invalid_configuration: object
) -> None:
    endpoint.reply.side_effect = [
        json.dumps(dict(parser_data, amount=invalid_configuration)),
        json.dumps(parser_data),
    ]
    assert parser_generation.generate_field_parsers(TEMPLATE, EXAMPLE).model_dump() == parser_data
    assert len(endpoint.requests) == 2
    assert all(request["model"] == "deepseek-r1" for request in endpoint.requests)
    assert endpoint.requests[0]["response_format"] == endpoint.requests[1]["response_format"]
    messages = cast(list[dict[str, str]], endpoint.requests[-1]["messages"])
    assert "failed validation" in messages[-1]["content"]
    endpoint.constructor.assert_called_once()


def test_two_corrections_can_succeed(
    endpoint: ModelEndpoint, parser_data: dict[str, object]
) -> None:
    endpoint.reply.side_effect = ["not JSON", "{}", json.dumps(parser_data)]
    assert parser_generation.generate_field_parsers(TEMPLATE, EXAMPLE).model_dump() == parser_data
    assert len(endpoint.requests) == 3


@pytest.mark.parametrize("response", ["not JSON", "{}", "[]", "<think>unfinished"])
def test_invalid_output_exhausts_retries(endpoint: ModelEndpoint, response: str) -> None:
    endpoint.reply.return_value = response
    with pytest.raises(parser_generation.ParserGenerationError, match="after 3 attempts"):
        parser_generation.generate_field_parsers(TEMPLATE, EXAMPLE)
    assert len(endpoint.requests) == 3


def test_extra_output_fields_are_rejected(
    endpoint: ModelEndpoint, parser_data: dict[str, object]
) -> None:
    endpoint.reply.return_value = json.dumps(dict(parser_data, invented={"rule": "missing"}))
    with pytest.raises(parser_generation.ParserGenerationError, match="invented"):
        parser_generation.generate_field_parsers(TEMPLATE, EXAMPLE)


def test_provider_failure_propagates_without_correction(monkeypatch: pytest.MonkeyPatch) -> None:
    constructor = Mock()
    failure = ConnectionError("Ollama unavailable")
    invoke = constructor.return_value.with_structured_output.return_value.invoke
    invoke.side_effect = failure
    monkeypatch.setenv("PARSER_GENERATION_PROVIDER", "ollama")
    monkeypatch.setattr(_workflow, "ChatOpenAI", constructor)
    with pytest.raises(ConnectionError) as caught:
        parser_generation.generate_field_parsers(TEMPLATE, EXAMPLE)
    assert caught.value is failure
    invoke.assert_called_once()


def test_template_without_placeholders(endpoint: ModelEndpoint) -> None:
    expected = {name: {"rule": "missing"} for name in TRANSACTION_FIELD_NAMES}
    endpoint.reply.return_value = json.dumps(expected)
    assert parser_generation.generate_field_parsers("Account notice", []).model_dump() == expected


def test_shared_parser_set_still_allows_unconfigured_fields() -> None:
    assert FieldParserSet.model_validate({"amount": None}).configured() == {}


def test_module_entry_point_prints_parsers(
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
    endpoint: ModelEndpoint,
    parser_data: dict[str, object],
) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"template_text": TEMPLATE, "parameter_examples": EXAMPLE})),
    )
    parser_generation_main.main()
    captured = capsys.readouterr()
    assert json.loads(captured.out) == parser_data
    assert captured.err == ""
    assert len(endpoint.requests) == 1


@pytest.mark.parametrize(
    "request_json",
    ["", "not JSON", "{}", '{"template_text":"Paid <NUMBER>","parameter_examples":[[]]}'],
)
def test_cli_rejects_invalid_input(
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
    endpoint: ModelEndpoint,
    request_json: str,
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(request_json))
    with pytest.raises(SystemExit) as caught:
        parser_generation_main.main()
    assert caught.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Parser generation failed:" in captured.err
    endpoint.constructor.assert_not_called()


def test_cli_reports_generation_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        parser_generation_main,
        "generate_field_parsers",
        Mock(side_effect=ConnectionError("unavailable")),
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"template_text": TEMPLATE, "parameter_examples": EXAMPLE})),
    )
    with pytest.raises(SystemExit) as caught:
        parser_generation_main.main()
    assert caught.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unavailable" in captured.err
