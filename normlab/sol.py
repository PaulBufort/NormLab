"""GPT-5.6 Sol adapter using the Responses API.

The adapter keeps the model outside the numerical engine. It stores no raw
reasoning and exposes only response IDs, prompt versions and the function-call ID.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Callable

from . import MODEL_ID
from .decisions import (
    assign_card_id,
    ensure_mandatory_guardrails,
    verify_decision_card,
)
from .models import (
    DecisionCard,
    ExperimentProtocol,
    ExperimentResult,
    ProtocolPackage,
    SolTrace,
)
from .prompts import (
    DECISION_INSTRUCTIONS,
    DECISION_PROMPT_VERSION,
    DESIGN_INSTRUCTIONS,
    DESIGN_PROMPT_VERSION,
    TOOL_INSTRUCTIONS,
)
from .protocols import ground_protocol_in_question, normalize_package
from .runner import compact_result_for_sol


TOOL_NAME = "run_deterministic_experiment"


def api_key_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def privacy_safe_identifier(session_identifier: str) -> str:
    return hashlib.sha256(session_identifier.encode("utf-8")).hexdigest()[:32]


def _tool_definition() -> dict[str, Any]:
    return {
        "type": "function",
        "name": TOOL_NAME,
        "description": (
            "Run the already approved NormLab protocol in the deterministic "
            "threshold-agent engine. The function cannot alter the protocol."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "protocol_id": {
                    "type": "string",
                    "description": "Exact ID of the user-approved protocol.",
                }
            },
            "required": ["protocol_id"],
            "additionalProperties": False,
        },
        "strict": True,
    }


class SolClient:
    def __init__(
        self,
        *,
        client: Any | None = None,
        api_key: str | None = None,
        session_identifier: str = "normlab-demo",
    ) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.client = client
        self.safety_identifier = privacy_safe_identifier(session_identifier)

    def design_protocol(self, question: str) -> tuple[ProtocolPackage, SolTrace]:
        response = self.client.responses.parse(
            model=MODEL_ID,
            reasoning={"effort": "medium"},
            instructions=DESIGN_INSTRUCTIONS,
            input=question,
            text_format=ProtocolPackage,
            max_output_tokens=6000,
            safety_identifier=self.safety_identifier,
            store=False,
        )
        package = getattr(response, "output_parsed", None)
        if package is None:
            raise RuntimeError("Sol did not return a parsed ProtocolPackage")
        package = package.model_copy(
            update={
                "generated_by": "gpt-5.6-sol",
                "prompt_version": DESIGN_PROMPT_VERSION,
            }
        )
        package = package.model_copy(
            update={"protocol": ground_protocol_in_question(package.protocol, question)}
        )
        package = normalize_package(package)
        trace = SolTrace(
            design_response_id=getattr(response, "id", None),
            design_prompt_version=DESIGN_PROMPT_VERSION,
            decision_prompt_version=DECISION_PROMPT_VERSION,
        )
        return package, trace

    def run_and_synthesize(
        self,
        protocol: ExperimentProtocol,
        runner: Callable[[ExperimentProtocol], ExperimentResult],
        trace: SolTrace | None = None,
    ) -> tuple[ExperimentResult, DecisionCard, SolTrace]:
        trace = trace or SolTrace(
            design_prompt_version=DESIGN_PROMPT_VERSION,
            decision_prompt_version=DECISION_PROMPT_VERSION,
        )
        protocol_json = protocol.model_dump_json(indent=2)
        tool_response = self.client.responses.create(
            model=MODEL_ID,
            reasoning={"effort": "medium"},
            instructions=TOOL_INSTRUCTIONS,
            input=(
                "Approved protocol follows. Call the deterministic tool with exactly "
                f"protocol_id={protocol.protocol_id}.\n{protocol_json}"
            ),
            tools=[_tool_definition()],
            tool_choice={"type": "function", "name": TOOL_NAME},
            parallel_tool_calls=False,
            include=["reasoning.encrypted_content"],
            max_output_tokens=1200,
            safety_identifier=self.safety_identifier,
            store=False,
        )
        calls = [
            item
            for item in getattr(tool_response, "output", [])
            if getattr(item, "type", None) == "function_call"
            and getattr(item, "name", None) == TOOL_NAME
        ]
        if len(calls) != 1:
            raise RuntimeError(f"Sol must call {TOOL_NAME} exactly once")
        call = calls[0]
        arguments = json.loads(call.arguments)
        if arguments != {"protocol_id": protocol.protocol_id}:
            raise RuntimeError("Sol attempted to alter or substitute the approved protocol")

        result = runner(protocol)
        tool_output = json.dumps(
            compact_result_for_sol(result), ensure_ascii=False, separators=(",", ":")
        )
        continuation = list(getattr(tool_response, "output", []))
        continuation.append(
            {
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": tool_output,
            }
        )
        decision_response = self.client.responses.parse(
            model=MODEL_ID,
            reasoning={"effort": "medium"},
            instructions=DECISION_INSTRUCTIONS,
            input=continuation,
            text_format=DecisionCard,
            # Structured output can be incomplete when the output cap is reached.
            # The prompt bounds the card; this reserve leaves room for Sol's
            # reasoning tokens and the complete typed response.
            max_output_tokens=8000,
            safety_identifier=self.safety_identifier,
            store=False,
        )
        card = getattr(decision_response, "output_parsed", None)
        if card is None:
            raise RuntimeError("Sol did not return a parsed DecisionCard")
        card = card.model_copy(
            update={
                "protocol_id": protocol.protocol_id,
                "generated_by": "gpt-5.6-sol",
            }
        )
        card = ensure_mandatory_guardrails(card, result)
        card = assign_card_id(card, result)
        verify_decision_card(card, result)
        updated_trace = trace.model_copy(
            update={
                "tool_response_id": getattr(tool_response, "id", None),
                "synthesis_response_id": getattr(decision_response, "id", None),
                "tool_call_id": getattr(call, "call_id", None),
            }
        )
        return result, card, updated_trace
