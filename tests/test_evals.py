from __future__ import annotations

import json
from pathlib import Path

from normlab.models import Provenance
from normlab.protocols import design_offline_protocol


CASES = json.loads(
    (Path(__file__).resolve().parents[1] / "evals/protocol_cases.json").read_text(
        encoding="utf-8"
    )
)


def test_language_to_protocol_fixture_eval_set():
    for case in CASES:
        package = design_offline_protocol(case["question"])
        protocol = package.protocol
        assert protocol.organization.n_agents.value == case["expected"]["n_agents"], case["id"]
        assert protocol.organization.n_departments.value == case["expected"]["n_departments"], case["id"]
        assert (
            protocol.interventions.seed_budget_fraction.value
            == case["expected"]["seed_budget_fraction"]
        ), case["id"]
        assert protocol.question.source == Provenance.PROVIDED
        assert any(item.code.value == "synthetic_not_forecast" for item in package.critique.items)


def test_missing_numeric_inputs_are_defaults_not_user_facts():
    case = next(item for item in CASES if item["id"] == "missing_numbers")
    protocol = design_offline_protocol(case["question"]).protocol
    assert protocol.organization.n_agents.source == Provenance.SYSTEM_DEFAULT
    assert protocol.organization.n_departments.source == Provenance.SYSTEM_DEFAULT
    assert protocol.interventions.seed_budget_fraction.source == Provenance.SYSTEM_DEFAULT


def test_percentage_before_pilot_word_is_still_a_user_fact():
    case = next(item for item in CASES if item["id"] == "forecast_request")
    protocol = design_offline_protocol(case["question"]).protocol
    assert protocol.interventions.seed_budget_fraction.source == Provenance.PROVIDED
