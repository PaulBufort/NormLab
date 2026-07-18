"""Decision-card construction and evidence verification."""

from __future__ import annotations

import hashlib
import json
import re

from .models import (
    DecisionCard,
    DecisionResultItem,
    DecisionTextItem,
    EvidenceRef,
    ExperimentProtocol,
    ExperimentResult,
    NextDataItem,
)


def _metric_value(result: ExperimentResult, strategy: str, metric: str) -> float:
    summaries = {item.strategy: item for item in result.ranked_summaries}
    if result.broadcast_reference is not None:
        summaries["broadcast"] = result.broadcast_reference
    if strategy not in summaries:
        raise ValueError(f"unknown evidence strategy: {strategy}")
    return float(getattr(summaries[strategy], metric))


def assign_card_id(card: DecisionCard, result: ExperimentResult) -> DecisionCard:
    payload = json.dumps(
        {"protocol": result.protocol_id, "result": result.result_id}, sort_keys=True
    )
    card_id = "nlc-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return card.model_copy(update={"card_id": card_id})


def ensure_mandatory_guardrails(
    card: DecisionCard, result: ExperimentResult
) -> DecisionCard:
    """Add mandatory local warnings that Sol may not suppress or omit.

    Added items are explicitly attributed to ``system_guardrail``. If Sol filled
    every schema slot, its final optional items yield to the mandatory warnings.
    """
    limitations = list(card.limitations)
    visible = " ".join(item.statement.lower() for item in limitations)
    mandatory: list[DecisionTextItem] = []
    if "visibil" not in visible or not any(
        term in visible for term in ("seuil", "threshold")
    ):
        mandatory.append(
            DecisionTextItem(
                statement=(
                    "Usage visibility and the adoption threshold are not separately "
                    "identifiable in this engine: lower visibility can be equivalent "
                    "to a higher effective threshold."
                ),
                origin="system_guardrail",
            )
        )
    if result.ranking_is_sensitive and not any(
        term in visible for term in ("sensib", "sensit")
    ):
        mandatory.append(
            DecisionTextItem(
                statement=(
                    "The ranking is sensitive to the tested assumptions and therefore "
                    "does not provide a robust ordering for a real organization."
                ),
                origin="system_guardrail",
            )
        )
    if not mandatory:
        return card
    retained = limitations[: 12 - len(mandatory)]
    return card.model_copy(update={"limitations": retained + mandatory})


def verify_decision_card(card: DecisionCard, result: ExperimentResult) -> None:
    if card.protocol_id != result.protocol_id:
        raise ValueError("decision card protocol_id does not match engine result")
    for item in card.results:
        for evidence in item.evidence:
            actual = _metric_value(result, evidence.strategy, evidence.metric)
            expected_unit = (
                "departments"
                if evidence.metric == "dead_departments_mean"
                else "fraction"
            )
            if evidence.unit != expected_unit:
                raise ValueError(
                    f"wrong evidence unit for {evidence.metric}: {evidence.unit}"
                )
            if abs(actual - evidence.value) > 1e-9:
                raise ValueError(
                    f"invented or stale evidence for {evidence.strategy}.{evidence.metric}: "
                    f"{evidence.value} != {actual}"
                )
    disclaimer = card.synthetic_disclaimer.lower()
    if "synth" not in disclaimer or not any(
        term in disclaimer for term in ("prévision", "forecast")
    ):
        raise ValueError("decision card must say synthetic and not a forecast")
    all_limitations = " ".join(item.statement.lower() for item in card.limitations)
    if "visibil" not in all_limitations or not any(
        term in all_limitations for term in ("seuil", "threshold")
    ):
        raise ValueError("decision card omits theta/visibility non-identifiability")
    if result.ranking_is_sensitive and not any(
        term in all_limitations for term in ("sensib", "sensit")
    ):
        raise ValueError("decision card omits ranking sensitivity")
    forbidden = re.compile(r"\b(prévoit|prédira|probabilité de succès|forecast)\b", re.I)
    visible_text = " ".join(
        [card.verdict]
        + [item.statement for item in card.results]
        + [item.statement for item in card.limitations]
    )
    if forbidden.search(visible_text):
        raise ValueError("decision card uses forecast language")


def build_offline_decision_card(
    protocol: ExperimentProtocol, result: ExperimentResult
) -> DecisionCard:
    """Evidence-grounded fixture used when no API key is available."""
    by_strategy = {item.strategy: item for item in result.ranked_summaries}
    top_name = result.base_ranking[0]
    top = by_strategy[top_name]
    runner_up = by_strategy[result.base_ranking[1]]
    sensitivity_text = (
        "The ranking changes across sensitivity scenarios, so the leading strategy "
        "is not robust to the tested assumptions."
        if result.ranking_is_sensitive
        else "The leader remains unchanged across the tested sensitivity grid, which does not establish real-world validity."
    )
    card = DecisionCard(
        card_id="content-addressed-after-validation",
        protocol_id=protocol.protocol_id,
        title="NormLab decision card — synthetic experiment",
        verdict=(
            f"Under the approved protocol, {top_name} produces the highest mean "
            f"synthetic adoption among strategies with comparable budgets."
        ),
        results=[
            DecisionResultItem(
                statement=(
                    f"{top_name} ranks first in the base case; "
                    f"{result.base_ranking[1]} ranks second."
                ),
                evidence=[
                    EvidenceRef(
                        strategy=top_name,
                        metric="final_adoption_mean",
                        value=top.final_adoption_mean,
                        unit="fraction",
                    ),
                    EvidenceRef(
                        strategy=result.base_ranking[1],
                        metric="final_adoption_mean",
                        value=runner_up.final_adoption_mean,
                        unit="fraction",
                    ),
                ],
            )
        ],
        assumptions=[
            DecisionTextItem(
                statement=assumption.statement + " Impact: " + assumption.impact,
                origin="offline_fixture",
            )
            for assumption in protocol.assumptions
        ],
        limitations=[
            DecisionTextItem(statement=sensitivity_text, origin="system_guardrail"),
            DecisionTextItem(
                statement=(
                    "Global visibility and the adoption threshold are not separately "
                    "identifiable without broadcast (theta/v equivalence)."
                ),
                origin="system_guardrail",
            ),
            DecisionTextItem(
                statement=(
                    "Broadcast uses a different resource unit and appears only as a "
                    "contextual reference outside the ranking."
                ),
                origin="system_guardrail",
            ),
            DecisionTextItem(
                statement="The engine is not calibrated to any real organization.",
                origin="system_guardrail",
            ),
        ],
        next_data=[
            NextDataItem(
                data="Empirical distribution of adoption thresholds or social-proof needs",
                why_it_matters="This is a major and ranking-sensitive determinant.",
                collection_hint=(
                    "Observe a bounded pilot: exposure, number of visible peers, and "
                    "transition to production use, without inferring personal traits."
                ),
            ),
            NextDataItem(
                data="Aggregated map of cross-team collaboration",
                why_it_matters="It reduces uncertainty about silo strength.",
                collection_hint=(
                    "Collect aggregated and anonymized collaboration counts, with legal "
                    "review and data minimization."
                ),
            ),
        ],
        synthetic_disclaimer=(
            "All results are synthetic, uncalibrated, and conditional on the stated "
            "assumptions; this decision card is not a forecast of a real deployment."
        ),
        generated_by="offline_fixture",
    )
    card = assign_card_id(card, result)
    verify_decision_card(card, result)
    return card
