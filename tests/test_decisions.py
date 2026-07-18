from __future__ import annotations

import pytest

from normlab.decisions import build_offline_decision_card, verify_decision_card


def test_offline_card_is_grounded_and_separated(protocol, result):
    card = build_offline_decision_card(protocol, result)
    verify_decision_card(card, result)
    assert card.results and card.assumptions and card.limitations and card.next_data
    assert card.generated_by == "offline_fixture"
    assert "synth" in card.synthetic_disclaimer.lower()
    assert "prévision" in card.synthetic_disclaimer.lower()


def test_invented_evidence_is_rejected(protocol, result):
    card = build_offline_decision_card(protocol, result)
    evidence = card.results[0].evidence[0]
    bad_evidence = evidence.model_copy(update={"value": evidence.value + 0.01})
    bad_result = card.results[0].model_copy(update={"evidence": [bad_evidence]})
    bad_card = card.model_copy(update={"results": [bad_result]})
    with pytest.raises(ValueError, match="invented or stale evidence"):
        verify_decision_card(bad_card, result)


def test_wrong_evidence_unit_is_rejected(protocol, result):
    card = build_offline_decision_card(protocol, result)
    evidence = card.results[0].evidence[0]
    bad_evidence = evidence.model_copy(update={"unit": "departments"})
    bad_result = card.results[0].model_copy(update={"evidence": [bad_evidence]})
    bad_card = card.model_copy(update={"results": [bad_result]})
    with pytest.raises(ValueError, match="wrong evidence unit"):
        verify_decision_card(bad_card, result)
