"""Private LangGraph workflow used by the parser-generation package."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import (  # pyright: ignore[reportMissingTypeStubs]
    END,
    START,
    MessagesState,
    StateGraph,
)
from langgraph.graph.state import CompiledStateGraph  # pyright: ignore[reportMissingTypeStubs]

_MODEL = "deepseek-r1"
_PROMPT = "Say hello."
_DOTENV_PATH = Path(__file__).resolve().parents[3] / ".env"
_BASE_URL = "http://localhost:11434/v1"


def _build_graph() -> CompiledStateGraph[MessagesState, None, MessagesState, MessagesState]:
    model = ChatOpenAI(model=_MODEL, base_url=_BASE_URL)

    def chat_model(state: MessagesState) -> dict[str, list[BaseMessage]]:
        return {"messages": [model.invoke(state["messages"])]}

    builder = StateGraph(MessagesState)
    builder.add_node("chat_model", chat_model)  # pyright: ignore[reportUnknownMemberType]
    builder.add_edge(START, "chat_model")
    builder.add_edge("chat_model", END)
    return builder.compile()  # pyright: ignore[reportUnknownMemberType]


def say_hello() -> str:
    """Ask the parser-generation workflow to return a greeting."""
    load_dotenv(dotenv_path=_DOTENV_PATH)
    result = _build_graph().invoke(  # pyright: ignore[reportUnknownMemberType]
        {"messages": [HumanMessage(content=_PROMPT)]}
    )
    return result["messages"][-1].text
