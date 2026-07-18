from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from normlab import MODEL_ID
from normlab.decisions import build_offline_decision_card
from normlab.prompts import DESIGN_PROMPT_VERSION
from normlab.protocols import design_offline_protocol
from normlab.sol import SolClient, TOOL_NAME, privacy_safe_identifier


class FakeResponses:
    def __init__(self, parsed_outputs):
        self.parsed_outputs = list(parsed_outputs)
        self.parse_calls = []
        self.create_calls = []

    def parse(self, **kwargs):
        self.parse_calls.append(kwargs)
        return SimpleNamespace(
            id=f"resp-parse-{len(self.parse_calls)}",
            output_parsed=self.parsed_outputs.pop(0),
        )

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        protocol_id = kwargs["input"].split("protocol_id=", 1)[1].split(".\n", 1)[0]
        call = SimpleNamespace(
            type="function_call",
            name=TOOL_NAME,
            arguments=json.dumps({"protocol_id": protocol_id}),
            call_id="call-123",
        )
        return SimpleNamespace(id="resp-tool", output=[call])


def test_design_uses_explicit_sol_model_and_private_responses_contract():
    question = (
        "Une organisation de 200 personnes dans 4 départements veut adopter "
        "un copilote IA de production avec un budget pilotes de 5 %."
    )
    parsed = design_offline_protocol(question)
    responses = FakeResponses([parsed])
    client = SolClient(client=SimpleNamespace(responses=responses), session_identifier="abc")
    package, trace = client.design_protocol(question)
    call = responses.parse_calls[0]
    assert call["model"] == MODEL_ID == "gpt-5.6-sol"
    assert call["reasoning"] == {"effort": "medium"}
    assert call["store"] is False
    assert call["text_format"].__name__ == "ProtocolPackage"
    assert call["safety_identifier"] == privacy_safe_identifier("abc")
    assert package.generated_by == "gpt-5.6-sol"
    assert package.prompt_version == DESIGN_PROMPT_VERSION
    assert trace.design_response_id == "resp-parse-1"


def test_sol_can_only_call_approved_protocol_then_receives_engine_result(protocol, result):
    card = build_offline_decision_card(protocol, result).model_copy(
        update={"generated_by": "gpt-5.6-sol"}
    )
    responses = FakeResponses([card])
    client = SolClient(client=SimpleNamespace(responses=responses), session_identifier="abc")
    actual_result, actual_card, trace = client.run_and_synthesize(
        protocol, lambda approved: result
    )
    tool_call = responses.create_calls[0]
    assert tool_call["model"] == "gpt-5.6-sol"
    assert tool_call["store"] is False
    assert tool_call["parallel_tool_calls"] is False
    assert tool_call["tools"][0]["strict"] is True
    assert tool_call["tool_choice"] == {"type": "function", "name": TOOL_NAME}
    continuation = responses.parse_calls[0]["input"]
    assert responses.parse_calls[0]["max_output_tokens"] == 8000
    output = next(x for x in continuation if isinstance(x, dict))
    compact = json.loads(output["output"])
    assert compact["result_id"] == result.result_id
    assert actual_result == result
    assert actual_card.generated_by == "gpt-5.6-sol"
    assert trace.tool_call_id == "call-123"


def test_sol_rejects_protocol_substitution(protocol):
    responses = FakeResponses([])

    def malicious_create(**kwargs):
        call = SimpleNamespace(
            type="function_call",
            name=TOOL_NAME,
            arguments=json.dumps({"protocol_id": "nlp-substituted"}),
            call_id="call-bad",
        )
        return SimpleNamespace(id="resp-tool", output=[call])

    responses.create = malicious_create
    client = SolClient(client=SimpleNamespace(responses=responses))
    with pytest.raises(RuntimeError, match="alter or substitute"):
        client.run_and_synthesize(protocol, lambda approved: None)
