"""Paired deterministic experiment runner around the legacy engine.

The wrapper is a Build Week addition. It does not alter the threshold equations.
It adds paired organizations, an explicit budget ledger, sensitivity comparisons
and machine-readable non-identifiability warnings.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

from . import ENGINE_SOURCE_COMMIT
from .legacy_engine import __version__ as LEGACY_VERSION
from .legacy_engine.dynamics import SimParams, draw_agents, run_simulation
from .legacy_engine.metrics import dept_rates
from .legacy_engine.orggen import generate_org
from .legacy_engine.seeding import make_seeding
from .models import (
    BudgetLedgerEntry,
    CurveBand,
    ExperimentProtocol,
    ExperimentResult,
    NonIdentifiabilityFlag,
    RawRun,
    SensitivityOutcome,
    StrategySummary,
)


ENGINE_VERSION = f"adoption-sim/{LEGACY_VERSION}+normlab-paired-v1"


@dataclass
class _RunRecord:
    scenario_id: str
    replicate: int
    organization_seed: int
    agent_seed: int
    seeding_seed: int
    dynamics_seed: int
    curve: np.ndarray
    final: float
    dead_departments: int
    converged: bool
    attribution: dict[str, float]
    seed_count: int


def _stable_seed(*parts: Any) -> int:
    payload = json.dumps(parts, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _parameters(protocol: ExperimentProtocol, overrides: dict[str, float]) -> SimParams:
    adoption = protocol.adoption
    return SimParams(
        theta_mean=overrides.get("theta_mean", adoption.theta_mean.value),
        theta_concentration=overrides.get(
            "theta_concentration", adoption.theta_concentration.value
        ),
        p_innovator=adoption.p_innovator.value,
        p_willing=(adoption.willingness.value,) * 3,
        able_rates=adoption.able_rate.value,
        visibility=overrides.get("visibility", adoption.visibility.value),
        relapse_prob=adoption.relapse_probability.value,
        max_steps=protocol.execution.max_steps.value,
    )


def _run_scenario(
    protocol: ExperimentProtocol,
    scenario_label: str,
    overrides: dict[str, float] | None = None,
    include_broadcast: bool = False,
) -> dict[str, list[_RunRecord]]:
    overrides = overrides or {}
    strategies = list(protocol.interventions.ranked_strategies.value)
    if include_broadcast:
        strategies.append("broadcast")
    records: dict[str, list[_RunRecord]] = defaultdict(list)
    params = _parameters(protocol, overrides)
    execution = protocol.execution

    for rep in range(execution.replicates.value):
        organization_seed = _stable_seed(execution.master_seed.value, rep, "org")
        org_rng = np.random.default_rng(organization_seed)
        org = generate_org(
            n_agents=protocol.organization.n_agents.value,
            n_departments=protocol.organization.n_departments.value,
            mean_team_size=protocol.organization.mean_team_size.value,
            silo_strength=overrides.get(
                "silo_strength", protocol.organization.silo_strength.value
            ),
            seed=org_rng,
        )
        compiled = org.compile()
        agent_seed = _stable_seed(execution.master_seed.value, rep, "agents")
        agent_rng = np.random.default_rng(agent_seed)
        agents = draw_agents(compiled, params, agent_rng)

        for strategy in strategies:
            seeding_seed = _stable_seed(execution.master_seed.value, rep, "seeding")
            dynamics_seed = _stable_seed(execution.master_seed.value, rep, "dynamics")
            seed_rng = np.random.default_rng(seeding_seed)
            dynamics_rng = np.random.default_rng(dynamics_seed)
            seeding = make_seeding(
                strategy,
                compiled,
                protocol.interventions.seed_budget_fraction.value,
                rng=seed_rng,
            )
            result = run_simulation(
                compiled, params, seeding, rng=dynamics_rng, agents=agents
            )
            rates = dept_rates(result, compiled)
            dead = sum(rate < 0.25 for rate in rates.values())
            counts = result.attribution_counts()
            denom = float(compiled.active.sum())
            records[strategy].append(
                _RunRecord(
                    scenario_id=scenario_label,
                    replicate=rep,
                    organization_seed=organization_seed,
                    agent_seed=agent_seed,
                    seeding_seed=seeding_seed,
                    dynamics_seed=dynamics_seed,
                    curve=result.curve,
                    final=result.final_rate,
                    dead_departments=dead,
                    converged=result.converged,
                    attribution={key: value / denom for key, value in counts.items()},
                    seed_count=int(seeding.initial_adopters.size),
                )
            )
    return records


def _summary(strategy: str, records: list[_RunRecord], comparable: bool) -> StrategySummary:
    curves = np.stack([record.curve for record in records])
    finals = np.array([record.final for record in records])
    attribution_keys = sorted(records[0].attribution)
    attribution = {
        key: float(np.mean([record.attribution[key] for record in records]))
        for key in attribution_keys
    }
    seed_counts = {record.seed_count for record in records}
    if len(seed_counts) != 1:
        raise RuntimeError(f"seed budget changed within strategy {strategy}")
    return StrategySummary(
        strategy=strategy,
        comparable=comparable,
        seed_count=seed_counts.pop(),
        final_adoption_mean=float(finals.mean()),
        final_adoption_p10=float(np.percentile(finals, 10)),
        final_adoption_p90=float(np.percentile(finals, 90)),
        dead_departments_mean=float(
            np.mean([record.dead_departments for record in records])
        ),
        convergence_rate=float(np.mean([record.converged for record in records])),
        attribution_share=attribution,
        curve=CurveBand(
            mean=curves.mean(axis=0).tolist(),
            p10=np.percentile(curves, 10, axis=0).tolist(),
            p90=np.percentile(curves, 90, axis=0).tolist(),
        ),
    )


def _ranking(summaries: list[StrategySummary]) -> list[str]:
    return [
        summary.strategy
        for summary in sorted(
            summaries, key=lambda item: (-item.final_adoption_mean, item.strategy)
        )
    ]


def _raw_runs(records: dict[str, list[_RunRecord]]) -> list[RawRun]:
    rows = []
    for strategy, strategy_records in records.items():
        for record in strategy_records:
            rows.append(
                RawRun(
                    scenario_id=record.scenario_id,
                    replicate=record.replicate,
                    strategy=strategy,
                    organization_seed=record.organization_seed,
                    agent_seed=record.agent_seed,
                    seeding_seed=record.seeding_seed,
                    dynamics_seed=record.dynamics_seed,
                    seed_count=record.seed_count,
                    final_adoption=record.final,
                    dead_departments=record.dead_departments,
                    converged=record.converged,
                    attribution_share=record.attribution,
                    curve=record.curve.tolist(),
                )
            )
    return rows


def run_experiment(protocol: ExperimentProtocol) -> ExperimentResult:
    """Execute the approved protocol. No model call occurs in this function."""
    base_records = _run_scenario(protocol, "base", include_broadcast=True)
    raw_runs = _raw_runs(base_records)
    ranked = [
        _summary(strategy, base_records[strategy], comparable=True)
        for strategy in protocol.interventions.ranked_strategies.value
    ]
    base_ranking = _ranking(ranked)
    broadcast = (
        _summary("broadcast", base_records["broadcast"], comparable=False)
        if protocol.interventions.broadcast_context_reference
        else None
    )
    ranked_seed_counts = {item.seed_count for item in ranked}
    if len(ranked_seed_counts) != 1:
        raise RuntimeError("ranked strategies do not share an equal seed budget")

    sensitivity: list[SensitivityOutcome] = []
    for factor in protocol.sensitivity:
        for level, value in (("low", factor.low), ("high", factor.high)):
            label = f"{factor.name}:{level}:{value}"
            variant_records = _run_scenario(
                protocol, label, overrides={factor.name: value}, include_broadcast=False
            )
            raw_runs.extend(_raw_runs(variant_records))
            summaries = [
                _summary(strategy, variant_records[strategy], comparable=True)
                for strategy in protocol.interventions.ranked_strategies.value
            ]
            ranking = _ranking(summaries)
            top = next(item for item in summaries if item.strategy == ranking[0])
            sensitivity.append(
                SensitivityOutcome(
                    factor=factor.name,
                    level=level,
                    value=value,
                    top_strategy=ranking[0],
                    top_final_adoption=top.final_adoption_mean,
                    ranking=ranking,
                    ranking_changed=ranking != base_ranking,
                )
            )

    seed_count = ranked_seed_counts.pop()
    ledger = [
        BudgetLedgerEntry(
            strategy=strategy,
            resource_unit="initial_adopters",
            amount=float(seed_count),
            comparable_in_ranking=True,
            note="Same seed count, same organizations, and paired replications.",
        )
        for strategy in protocol.interventions.ranked_strategies.value
    ]
    if broadcast is not None:
        ledger.append(
            BudgetLedgerEntry(
                strategy="broadcast",
                resource_unit="communication_exposure",
                amount=1.0,
                comparable_in_ranking=False,
                note=(
                    "Zero seeds; one round of central exposure. Displayed as a "
                    "contextual reference and never included in the main ranking."
                ),
            )
        )

    compact = {
        "protocol_id": protocol.protocol_id,
        "engine_version": ENGINE_VERSION,
        "engine_source_commit": ENGINE_SOURCE_COMMIT,
        "ranking": base_ranking,
        "means": {item.strategy: item.final_adoption_mean for item in ranked},
        "sensitivity": [item.model_dump(mode="json") for item in sensitivity],
    }
    result_id = "nlr-" + hashlib.sha256(
        json.dumps(compact, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    sensitive = any(item.ranking_changed for item in sensitivity)
    warnings = [
        "Fully synthetic, uncalibrated data: a conditional result, not a forecast.",
        "Ranked strategies share one seed budget; broadcast is outside the ranking.",
    ]
    if sensitive:
        warnings.append("The ranking changes in at least one sensitivity scenario.")

    return ExperimentResult(
        result_id=result_id,
        protocol_id=protocol.protocol_id,
        engine_version=ENGINE_VERSION,
        engine_source_commit=ENGINE_SOURCE_COMMIT,
        protocol_snapshot=protocol,
        raw_runs=raw_runs,
        ranked_summaries=ranked,
        broadcast_reference=broadcast,
        base_ranking=base_ranking,
        budget_ledger=ledger,
        sensitivity=sensitivity,
        ranking_is_sensitive=sensitive,
        non_identifiability=[
            NonIdentifiabilityFlag(
                code="theta_visibility_equivalence",
                parameters=["theta_mean", "visibility"],
                explanation=(
                    "Without broadcast, global visibility v produces the same "
                    "trajectory as visibility=1 with thresholds theta/v."
                ),
                consequence=(
                    "Low adoption cannot distinguish a high-threshold population from "
                    "resistance caused by a hard-to-observe use."
                ),
            )
        ],
        run_warnings=warnings,
    )


def compact_result_for_sol(result: ExperimentResult) -> dict[str, Any]:
    """Reduce tool output while preserving every fact allowed in the decision card."""
    summaries = []
    for item in result.ranked_summaries:
        summaries.append(
            item.model_dump(
                mode="json", exclude={"curve", "attribution_share", "convergence_rate"}
            )
        )
    return {
        "result_id": result.result_id,
        "protocol_id": result.protocol_id,
        "engine_version": result.engine_version,
        "engine_source_commit": result.engine_source_commit,
        "synthetic_data": True,
        "forecast": False,
        "ranked_summaries": summaries,
        "base_ranking": result.base_ranking,
        "broadcast_reference": (
            result.broadcast_reference.model_dump(
                mode="json", exclude={"curve", "attribution_share", "convergence_rate"}
            )
            if result.broadcast_reference
            else None
        ),
        "budget_ledger": [entry.model_dump(mode="json") for entry in result.budget_ledger],
        "sensitivity": [item.model_dump(mode="json") for item in result.sensitivity],
        "ranking_is_sensitive": result.ranking_is_sensitive,
        "non_identifiability": [
            item.model_dump(mode="json") for item in result.non_identifiability
        ],
        "run_warnings": result.run_warnings,
    }
