"""Strict, inspectable contracts for NormLab.

All product-layer models are Build Week additions. The schemas deliberately keep
user-provided facts, Sol inferences and versioned defaults separate.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Provenance(str, Enum):
    PROVIDED = "provided"
    INFERRED = "inferred"
    SYSTEM_DEFAULT = "system_default"


class IntValue(StrictModel):
    value: int
    source: Provenance
    justification: str = Field(min_length=3, max_length=400)


class FloatValue(StrictModel):
    value: float
    source: Provenance
    justification: str = Field(min_length=3, max_length=400)


class TextValue(StrictModel):
    value: str = Field(min_length=1, max_length=2000)
    source: Provenance
    justification: str = Field(min_length=3, max_length=400)


StrategyName = Literal["random", "champions", "cluster", "line_manager_first"]
SensitivityName = Literal[
    "theta_mean", "theta_concentration", "silo_strength", "visibility"
]


class StrategySet(StrictModel):
    value: list[StrategyName] = Field(min_length=2, max_length=4)
    source: Provenance
    justification: str = Field(min_length=3, max_length=400)

    @model_validator(mode="after")
    def unique_strategies(self) -> "StrategySet":
        if len(self.value) != len(set(self.value)):
            raise ValueError("strategies must be unique")
        return self


class OrganizationSpec(StrictModel):
    n_agents: IntValue
    n_departments: IntValue
    mean_team_size: IntValue
    silo_strength: FloatValue


class AdoptionSpec(StrictModel):
    behavior_definition: TextValue
    theta_mean: FloatValue
    theta_concentration: FloatValue
    p_innovator: FloatValue
    willingness: FloatValue
    able_rate: FloatValue
    visibility: FloatValue
    relapse_probability: FloatValue


class InterventionSpec(StrictModel):
    ranked_strategies: StrategySet
    seed_budget_fraction: FloatValue
    broadcast_context_reference: bool = True


class ExecutionSpec(StrictModel):
    replicates: IntValue
    master_seed: IntValue
    max_steps: IntValue
    paired_common_organizations: bool = True


class SensitivityFactor(StrictModel):
    name: SensitivityName
    low: float
    high: float
    rationale: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def ordered(self) -> "SensitivityFactor":
        if self.low >= self.high:
            raise ValueError("sensitivity low must be lower than high")
        return self


class Assumption(StrictModel):
    statement: str = Field(min_length=3, max_length=800)
    source: Provenance
    impact: str = Field(min_length=3, max_length=800)


class ExperimentProtocol(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    protocol_id: str = Field(min_length=3, max_length=80)
    question: TextValue
    decision_context: TextValue
    organization: OrganizationSpec
    adoption: AdoptionSpec
    interventions: InterventionSpec
    execution: ExecutionSpec
    sensitivity: list[SensitivityFactor] = Field(min_length=4, max_length=4)
    assumptions: list[Assumption] = Field(min_length=1, max_length=12)
    missing_data: list[str] = Field(min_length=1, max_length=12)
    exclusions: list[str] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_domain(self) -> "ExperimentProtocol":
        org, adoption = self.organization, self.adoption
        interventions, execution = self.interventions, self.execution
        if not 200 <= org.n_agents.value <= 3000:
            raise ValueError("n_agents must be in [200, 3000] for the interactive MVP")
        if not 2 <= org.n_departments.value <= 20:
            raise ValueError("n_departments must be in [2, 20]")
        if not 3 <= org.mean_team_size.value <= 30:
            raise ValueError("mean_team_size must be in [3, 30]")
        bounded = {
            "silo_strength": org.silo_strength.value,
            "theta_mean": adoption.theta_mean.value,
            "p_innovator": adoption.p_innovator.value,
            "willingness": adoption.willingness.value,
            "able_rate": adoption.able_rate.value,
            "visibility": adoption.visibility.value,
            "relapse_probability": adoption.relapse_probability.value,
        }
        for name, value in bounded.items():
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        if not 0.01 <= adoption.theta_mean.value <= 0.8:
            raise ValueError("theta_mean must be in [0.01, 0.8]")
        if not 1 <= adoption.theta_concentration.value <= 100:
            raise ValueError("theta_concentration must be in [1, 100]")
        if not 0.01 <= interventions.seed_budget_fraction.value <= 0.15:
            raise ValueError("seed budget must be in [0.01, 0.15]")
        if not 3 <= execution.replicates.value <= 20:
            raise ValueError("replicates must be in [3, 20]")
        if not 20 <= execution.max_steps.value <= 100:
            raise ValueError("max_steps must be in [20, 100]")
        if not execution.paired_common_organizations:
            raise ValueError("ranked comparisons must use paired organizations")
        required = {
            "theta_mean", "theta_concentration", "silo_strength", "visibility"
        }
        names = [factor.name for factor in self.sensitivity]
        if set(names) != required or len(names) != len(set(names)):
            raise ValueError("sensitivity must contain each required factor exactly once")
        return self


class CritiqueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class CritiqueCode(str, Enum):
    STRONG_ASSUMPTION = "strong_assumption"
    MISSING_USER_DATA = "missing_user_data"
    BUDGET_NON_COMPARABLE = "budget_non_comparable"
    SENSITIVE_RANKING = "sensitive_ranking"
    NON_IDENTIFIABLE = "non_identifiable"
    OUTSIDE_ENGINE_SCOPE = "outside_engine_scope"
    SYNTHETIC_NOT_FORECAST = "synthetic_not_forecast"


class CritiqueItem(StrictModel):
    code: CritiqueCode
    severity: CritiqueSeverity
    message: str = Field(min_length=3, max_length=800)
    field_paths: list[str] = Field(default_factory=list, max_length=8)


class ExperimentCritique(StrictModel):
    summary: str = Field(min_length=3, max_length=1200)
    items: list[CritiqueItem] = Field(min_length=1, max_length=16)

    @property
    def has_blocker(self) -> bool:
        return any(item.severity == CritiqueSeverity.BLOCKING for item in self.items)


class ProtocolPackage(StrictModel):
    protocol: ExperimentProtocol
    critique: ExperimentCritique
    generated_by: Literal["gpt-5.6-sol", "offline_fixture"]
    prompt_version: str


class CurveBand(StrictModel):
    mean: list[float]
    p10: list[float]
    p90: list[float]


class StrategySummary(StrictModel):
    strategy: str
    comparable: bool
    seed_count: int
    final_adoption_mean: float
    final_adoption_p10: float
    final_adoption_p90: float
    dead_departments_mean: float
    convergence_rate: float
    attribution_share: dict[str, float]
    curve: CurveBand


class BudgetLedgerEntry(StrictModel):
    strategy: str
    resource_unit: str
    amount: float
    comparable_in_ranking: bool
    note: str


class SensitivityOutcome(StrictModel):
    factor: SensitivityName
    level: Literal["low", "high"]
    value: float
    top_strategy: str
    top_final_adoption: float
    ranking: list[str]
    ranking_changed: bool


class NonIdentifiabilityFlag(StrictModel):
    code: str
    parameters: list[str]
    explanation: str
    consequence: str


class RawRun(StrictModel):
    scenario_id: str
    replicate: int
    strategy: str
    organization_seed: int
    agent_seed: int
    seeding_seed: int
    dynamics_seed: int
    seed_count: int
    final_adoption: float
    dead_departments: int
    converged: bool
    attribution_share: dict[str, float]
    curve: list[float]


class ExperimentResult(StrictModel):
    result_id: str
    protocol_id: str
    engine_version: str
    engine_source_commit: str
    synthetic_data: Literal[True] = True
    forecast: Literal[False] = False
    protocol_snapshot: ExperimentProtocol
    raw_runs: list[RawRun]
    ranked_summaries: list[StrategySummary]
    broadcast_reference: StrategySummary | None
    base_ranking: list[str]
    budget_ledger: list[BudgetLedgerEntry]
    sensitivity: list[SensitivityOutcome]
    ranking_is_sensitive: bool
    non_identifiability: list[NonIdentifiabilityFlag]
    run_warnings: list[str]


EvidenceMetric = Literal[
    "final_adoption_mean", "final_adoption_p10", "final_adoption_p90",
    "dead_departments_mean"
]


class EvidenceRef(StrictModel):
    strategy: str
    metric: EvidenceMetric
    value: float
    unit: Literal["fraction", "departments"]


class DecisionResultItem(StrictModel):
    statement: str = Field(min_length=3, max_length=800)
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=6)


class DecisionTextItem(StrictModel):
    statement: str = Field(min_length=3, max_length=1000)
    origin: Literal["sol", "system_guardrail", "offline_fixture"]


class NextDataItem(StrictModel):
    data: str = Field(min_length=3, max_length=500)
    why_it_matters: str = Field(min_length=3, max_length=700)
    collection_hint: str = Field(min_length=3, max_length=700)


class DecisionCard(StrictModel):
    card_id: str
    protocol_id: str
    title: str = Field(min_length=3, max_length=200)
    verdict: str = Field(min_length=3, max_length=1000)
    results: list[DecisionResultItem] = Field(min_length=1, max_length=8)
    assumptions: list[DecisionTextItem] = Field(min_length=1, max_length=12)
    limitations: list[DecisionTextItem] = Field(min_length=1, max_length=12)
    next_data: list[NextDataItem] = Field(min_length=1, max_length=6)
    synthetic_disclaimer: str = Field(min_length=20, max_length=500)
    generated_by: Literal["gpt-5.6-sol", "offline_fixture"]


class SolTrace(StrictModel):
    model: Literal["gpt-5.6-sol"] = "gpt-5.6-sol"
    reasoning_effort: Literal["medium"] = "medium"
    design_response_id: str | None = None
    tool_response_id: str | None = None
    synthesis_response_id: str | None = None
    tool_call_id: str | None = None
    design_prompt_version: str
    decision_prompt_version: str
    store: Literal[False] = False
