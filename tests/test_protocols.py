from __future__ import annotations

import pytest
from pydantic import ValidationError

from normlab.models import Provenance
from normlab.protocols import (
    apply_user_overrides,
    design_offline_protocol,
    ground_protocol_in_question,
    iter_sourced_values,
)


def test_offline_protocol_preserves_user_facts_and_defaults():
    question = (
        "Une entreprise de 800 personnes dans 8 départements souhaite adopter un "
        "assistant IA de production avec un budget pilotes de 5 %."
    )
    package = design_offline_protocol(question)
    protocol = package.protocol
    assert protocol.question.value == question
    assert protocol.question.source == Provenance.PROVIDED
    assert protocol.organization.n_agents.value == 800
    assert protocol.organization.n_agents.source == Provenance.PROVIDED
    assert protocol.organization.n_departments.value == 8
    assert protocol.interventions.seed_budget_fraction.value == 0.05
    assert protocol.interventions.seed_budget_fraction.source == Provenance.PROVIDED
    assert protocol.adoption.theta_mean.source == Provenance.SYSTEM_DEFAULT
    assert {item.name for item in protocol.sensitivity} == {
        "theta_mean",
        "theta_concentration",
        "silo_strength",
        "visibility",
    }
    assert package.generated_by == "offline_fixture"
    assert {item.code.value for item in package.critique.items} >= {
        "synthetic_not_forecast",
        "non_identifiable",
        "budget_non_comparable",
    }


def test_every_simulation_input_has_explicit_provenance(protocol):
    sourced = dict(iter_sourced_values(protocol))
    assert len(sourced) == 19
    assert all(value.source in Provenance for value in sourced.values())


def test_user_override_changes_id_and_provenance(protocol):
    changed = apply_user_overrides(
        protocol,
        n_agents=250,
        n_departments=5,
        silo_strength=0.7,
        theta_mean=0.28,
        theta_concentration=18.0,
        visibility=0.8,
        seed_budget_fraction=0.06,
        replicates=4,
        master_seed=456,
        strategies=["random", "champions"],
    )
    assert changed.protocol_id != protocol.protocol_id
    assert changed.organization.n_agents.source == Provenance.PROVIDED
    assert changed.adoption.visibility.source == Provenance.PROVIDED
    assert changed.interventions.ranked_strategies.source == Provenance.PROVIDED


def test_ranked_comparison_requires_at_least_two_strategies(protocol):
    with pytest.raises(ValidationError):
        apply_user_overrides(
            protocol,
            n_agents=200,
            n_departments=4,
            silo_strength=0.8,
            theta_mean=0.3,
            theta_concentration=20.0,
            visibility=1.0,
            seed_budget_fraction=0.05,
            replicates=3,
            master_seed=123,
            strategies=["random"],
        )


def test_unsupported_numeric_user_fact_is_downgraded(protocol):
    claimed = protocol.model_copy(deep=True)
    claimed.adoption.theta_mean.source = Provenance.PROVIDED
    claimed.adoption.theta_mean.value = 0.77
    grounded = ground_protocol_in_question(claimed, protocol.question.value)
    assert grounded.adoption.theta_mean.source == Provenance.INFERRED
    assert "corrected" in grounded.adoption.theta_mean.justification


def test_false_system_default_and_paraphrased_text_are_downgraded(protocol):
    claimed = protocol.model_copy(deep=True)
    claimed.adoption.theta_mean.source = Provenance.SYSTEM_DEFAULT
    claimed.adoption.theta_mean.value = 0.41
    claimed.decision_context.source = Provenance.PROVIDED
    grounded = ground_protocol_in_question(claimed, protocol.question.value)
    assert grounded.adoption.theta_mean.source == Provenance.INFERRED
    assert grounded.decision_context.source == Provenance.INFERRED
    assert grounded.question.value == protocol.question.value
    assert grounded.question.source == Provenance.PROVIDED
