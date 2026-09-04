from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import Mock

import langchain_openai
import pytest
from _pytest.capture import CaptureFixture
from langchain_core.messages import AIMessage, HumanMessage

from aggregator import parser_generation
from aggregator.parser_generation import __main__ as parser_generation_main
from aggregator.parser_generation import _workflow  # pyright: ignore[reportPrivateUsage]


def test_import_does_not_construct_chat_model(monkeypatch: pytest.MonkeyPatch) -> None:
    chat_openai = Mock(side_effect=AssertionError("ChatOpenAI was constructed during import"))

    with monkeypatch.context() as context:
        context.setattr(langchain_openai, "ChatOpenAI", chat_openai)
        importlib.reload(_workflow)
        importlib.reload(parser_generation)

        assert parser_generation.say_hello is _workflow.say_hello
        chat_openai.assert_not_called()

    importlib.reload(_workflow)
    importlib.reload(parser_generation)


def test_say_hello_loads_dotenv_and_invokes_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    load_dotenv = Mock()
    model = Mock()
    model.invoke.return_value = AIMessage(content="Hello!")
    chat_openai = Mock(return_value=model)
    monkeypatch.setattr(_workflow, "load_dotenv", load_dotenv)
    monkeypatch.setattr(_workflow, "ChatOpenAI", chat_openai)

    assert parser_generation.say_hello() == "Hello!"

    load_dotenv.assert_called_once_with(
        dotenv_path=Path(_workflow.__file__).resolve().parents[3] / ".env"
    )
    chat_openai.assert_called_once_with(model="gpt-5.4-mini")
    messages = model.invoke.call_args.args[0]
    assert len(messages) == 1
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == "Say hello."


def test_module_entry_point_prints_greeting(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(parser_generation_main, "say_hello", lambda: "Hello from LangGraph!")

    parser_generation_main.main()

    assert capsys.readouterr().out == "Hello from LangGraph!\n"
