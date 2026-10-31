"""Checkpointed parser inference, draft publication, and human review."""

# LangGraph's dynamic node and state APIs have incomplete static annotations.
# pyright: reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Literal, cast

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import (  # pyright: ignore[reportMissingTypeStubs]
    END,
    START,
    MessagesState,
    StateGraph,
)
from langgraph.types import interrupt  # pyright: ignore[reportMissingTypeStubs]
from pydantic import ValidationError

from ..parser_configuration import FieldParserSet, validate_parser_set
from ..template_mining import ExtractedParameter
from ..template_representation import TemplateRepresentation, resolve_fields
from ..template_syntax import template_parameter_count
from ..transaction_extraction import extract_transaction
from . import _workflow
from ._schemas import GeneratedFieldParsers

_CORRECTION_PROMPT = (
    "Revise the current parser to address the supplied feedback and validation errors. "
    "Use the template and examples as evidence. Preserve correct mappings where possible. "
    "Return a complete seven-field parser set using only the supported rules."
)


class ReviewState(MessagesState):
    session_id: int
    template_text: str
    parameter_examples: list[list[dict[str, object]]]
    attempts: int
    round: int
    feedback: str
    candidate: dict[str, object] | None
    previous_candidate: dict[str, object] | None
    raw_output: str | None
    validation_errors: list[str]
    status: str


def initial_state(
    session_id: int,
    template_text: str,
    parameter_examples: list[list[dict[str, object]]],
    *,
    feedback: str = "",
    seed: FieldParserSet | None = None,
) -> ReviewState:
    evidence = {"template_text": template_text, "parameter_examples": parameter_examples}
    return cast(
        ReviewState,
        {
            "session_id": session_id,
            "template_text": template_text,
            "parameter_examples": parameter_examples,
            "messages": [HumanMessage(content=_workflow._PROMPT + json.dumps(evidence))],
            "attempts": 0,
            "round": 1,
            "feedback": feedback,
            "candidate": seed.model_dump(mode="json") if seed is not None else None,
            "previous_candidate": seed.model_dump(mode="json") if seed is not None else None,
            "raw_output": None,
            "validation_errors": [],
            "status": "running",
        },
    )


def build_review_graph(
    checkpointer: Any,
    publish: Callable[[int, int, FieldParserSet], None],
    approve: Callable[[int, int, FieldParserSet], None],
) -> Any:
    """Construct the graph after environment and checkpointer setup."""
    model: Any = None

    def infer(state: ReviewState, *, correction: bool) -> dict[str, object]:
        nonlocal model
        if model is None:
            model = _workflow._structured_model(_workflow._model_provider())
        messages = list(state["messages"])
        updates: list[Any] = []
        if correction:
            prompt = (
                f"{_CORRECTION_PROMPT}\n"
                f"Current parser: {state['candidate'] or state['previous_candidate']!r}\n"
                f"User feedback: {state['feedback']}\n"
                f"Validation errors: {state['validation_errors']!r}\n"
                f"Raw output: {state['raw_output']!r}"
            )
            request = HumanMessage(content=prompt)
            messages.append(request)
            updates.append(request)
        try:
            response = model.invoke(messages)
        except (ValidationError, OutputParserException) as error:
            raw = getattr(error, "llm_output", None)
            if raw is not None:
                updates.append(AIMessage(content=str(raw)))
            return {
                "candidate": None,
                "previous_candidate": state["candidate"] or state["previous_candidate"],
                "raw_output": str(raw) if raw is not None else None,
                "validation_errors": [str(error)],
                "messages": updates,
                "attempts": state["attempts"] + 1,
            }
        try:
            candidate = response.model_dump(mode="json")
            raw_output = response.model_dump_json()
        except (AttributeError, TypeError, ValueError) as error:
            raw_output = str(response)
            updates.append(AIMessage(content=raw_output))
            return {
                "candidate": None,
                "previous_candidate": state["candidate"] or state["previous_candidate"],
                "raw_output": raw_output,
                "validation_errors": [str(error)],
                "messages": updates,
                "attempts": state["attempts"] + 1,
            }
        updates.append(AIMessage(content=raw_output))
        return {
            "candidate": candidate,
            "previous_candidate": candidate,
            "raw_output": None,
            "validation_errors": [],
            "messages": updates,
            "attempts": state["attempts"] + 1,
        }

    def generate_parser(state: ReviewState) -> dict[str, object]:
        return infer(state, correction=False)

    def correct_parser_with_feedback(state: ReviewState) -> dict[str, object]:
        return infer(state, correction=True)

    def validate_parser(state: ReviewState) -> dict[str, object]:
        candidate = state["candidate"]
        if candidate is None:
            return {}
        try:
            complete = GeneratedFieldParsers.model_validate(candidate)
            parsers = FieldParserSet.model_validate(complete.model_dump())
            validate_parser_set(parsers, template_parameter_count(state["template_text"]))
            for number, example in enumerate(state["parameter_examples"], start=1):
                parameters = tuple(
                    ExtractedParameter(str(item["value"]), str(item["mask_name"]))
                    for item in sorted(example, key=lambda item: int(cast(int, item["index"])))
                )
                resolved: dict[str, str | None] | None = None
                try:
                    resolved = resolve_fields(parameters, parsers)
                    extract_transaction(
                        TemplateRepresentation(state["template_text"], parameters, resolved)
                    )
                except (ValueError, IndexError) as error:
                    raise ValueError(
                        f"Transaction verification failed for example {number}. "
                        f"Resolved fields: {resolved!r}. Validation error: {error}"
                    ) from error
        except (ValidationError, ValueError, IndexError) as error:
            return {"validation_errors": [str(error)]}
        return {"validation_errors": [], "candidate": parsers.model_dump(mode="json")}

    def route_validation(state: ReviewState) -> Literal["publish", "correct", "fail"]:
        if not state["validation_errors"] and state["candidate"] is not None:
            return "publish"
        return "correct" if state["attempts"] < 3 else "fail"

    def publish_draft(state: ReviewState) -> dict[str, object]:
        publish(
            state["session_id"],
            state["round"],
            FieldParserSet.model_validate(state["candidate"]),
        )
        return {"status": "awaiting_review"}

    def human_review(state: ReviewState) -> dict[str, object]:
        decision = interrupt({"session_id": state["session_id"], "round": state["round"]})
        if not isinstance(decision, dict):
            raise ValueError("Invalid review decision")
        decision = cast(dict[str, object], decision)
        if decision.get("action") == "approve":
            return {"status": "approving"}
        feedback = decision.get("feedback")
        if not isinstance(feedback, str) or not feedback.strip():
            raise ValueError("Review feedback must be nonblank")
        return {
            "feedback": feedback,
            "round": state["round"] + 1,
            "attempts": 0,
            "validation_errors": [],
            "status": "running",
        }

    def route_review(state: ReviewState) -> Literal["approve", "correct"]:
        return "approve" if state["status"] == "approving" else "correct"

    def approve_draft(state: ReviewState) -> dict[str, object]:
        approve(
            state["session_id"],
            state["round"],
            FieldParserSet.model_validate(state["candidate"]),
        )
        return {"status": "approved"}

    def fail_round(state: ReviewState) -> dict[str, object]:
        return {"status": "failed"}

    builder = StateGraph(ReviewState)
    builder.add_node("generate_parser", generate_parser)
    builder.add_node("correct_parser_with_feedback", correct_parser_with_feedback)
    builder.add_node("validate_parser", validate_parser)
    builder.add_node("publish_draft", publish_draft)
    builder.add_node("human_review", human_review)
    builder.add_node("approve_draft", approve_draft)
    builder.add_node("fail_round", fail_round)
    builder.add_conditional_edges(
        START,
        lambda state: "correct" if state["feedback"] else "generate",
        {"correct": "correct_parser_with_feedback", "generate": "generate_parser"},
    )
    builder.add_edge("generate_parser", "validate_parser")
    builder.add_edge("correct_parser_with_feedback", "validate_parser")
    builder.add_conditional_edges(
        "validate_parser",
        route_validation,
        {
            "publish": "publish_draft",
            "correct": "correct_parser_with_feedback",
            "fail": "fail_round",
        },
    )
    builder.add_edge("publish_draft", "human_review")
    builder.add_conditional_edges(
        "human_review",
        route_review,
        {"approve": "approve_draft", "correct": "correct_parser_with_feedback"},
    )
    builder.add_edge("approve_draft", END)
    builder.add_edge("fail_round", END)
    return builder.compile(checkpointer=checkpointer)
