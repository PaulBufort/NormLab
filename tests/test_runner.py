from __future__ import annotations

from normlab.runner import run_experiment


def test_runner_is_reproducible(protocol, result):
    duplicate = run_experiment(protocol)
    assert duplicate.model_dump(mode="json") == result.model_dump(mode="json")


def test_ranked_strategies_have_equal_paired_budget(result):
    summaries = result.ranked_summaries
    assert {item.seed_count for item in summaries} == {10}
    assert all(item.comparable for item in summaries)
    assert set(result.base_ranking) == {
        "random",
        "champions",
        "cluster",
        "line_manager_first",
    }
    ranked_ledger = [x for x in result.budget_ledger if x.comparable_in_ranking]
    assert {x.amount for x in ranked_ledger} == {10.0}
    assert {x.resource_unit for x in ranked_ledger} == {"initial_adopters"}


def test_broadcast_is_outside_the_ranking(result):
    assert result.broadcast_reference is not None
    assert not result.broadcast_reference.comparable
    assert "broadcast" not in result.base_ranking
    broadcast_budget = next(x for x in result.budget_ledger if x.strategy == "broadcast")
    assert not broadcast_budget.comparable_in_ranking
    assert broadcast_budget.resource_unit == "communication_exposure"


def test_sensitivity_and_non_identifiability_are_explicit(result):
    assert len(result.sensitivity) == 8
    assert {item.factor for item in result.sensitivity} == {
        "theta_mean",
        "theta_concentration",
        "silo_strength",
        "visibility",
    }
    assert result.ranking_is_sensitive == any(
        item.ranking_changed for item in result.sensitivity
    )
    flag = next(x for x in result.non_identifiability if x.code == "theta_visibility_equivalence")
    assert set(flag.parameters) == {"theta_mean", "visibility"}
    assert result.synthetic_data is True
    assert result.forecast is False


def test_raw_replications_preserve_protocol_and_every_seed(protocol, result):
    assert result.protocol_snapshot == protocol
    assert len(result.raw_runs) == 111
    base = [item for item in result.raw_runs if item.scenario_id == "base"]
    assert len(base) == 15
    per_rep = [item for item in base if item.replicate == 0]
    assert len({item.organization_seed for item in per_rep}) == 1
    assert len({item.agent_seed for item in per_rep}) == 1
    assert len({item.seeding_seed for item in per_rep}) == 1
    assert len({item.dynamics_seed for item in per_rep}) == 1
    assert all(item.seeding_seed >= 0 and item.dynamics_seed >= 0 for item in base)
