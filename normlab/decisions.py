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
    if "visibil" not in visible or "seuil" not in visible:
        mandatory.append(
            DecisionTextItem(
                statement=(
                    "La visibilité des usages et le seuil d’adoption ne sont pas "
                    "identifiables séparément dans ce moteur : une visibilité plus "
                    "faible peut être équivalente à un seuil effectif plus élevé."
                ),
                origin="system_guardrail",
            )
        )
    if result.ranking_is_sensitive and "sensib" not in visible:
        mandatory.append(
            DecisionTextItem(
                statement=(
                    "Le classement est sensible aux hypothèses testées et ne constitue "
                    "donc pas un ordre robuste pour une organisation réelle."
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
    if "visibil" not in all_limitations or "seuil" not in all_limitations:
        raise ValueError("decision card omits theta/visibility non-identifiability")
    if result.ranking_is_sensitive and "sensib" not in all_limitations:
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
        "Le classement change dans les scénarios de sensibilité ; la stratégie en tête "
        "n’est donc pas robuste aux hypothèses testées."
        if result.ranking_is_sensitive
        else "Le leader reste le même dans la grille de sensibilité testée, sans que cela prouve sa validité réelle."
    )
    card = DecisionCard(
        card_id="content-addressed-after-validation",
        protocol_id=protocol.protocol_id,
        title="Fiche de décision NormLab — expérience synthétique",
        verdict=(
            f"Sous le protocole approuvé, {top_name} obtient la plus forte adoption "
            f"simulée moyenne parmi les stratégies à budget comparable."
        ),
        results=[
            DecisionResultItem(
                statement=(
                    f"{top_name} est premier dans le scénario central ; "
                    f"{result.base_ranking[1]} est second."
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
                statement=assumption.statement + " Impact : " + assumption.impact,
                origin="offline_fixture",
            )
            for assumption in protocol.assumptions
        ],
        limitations=[
            DecisionTextItem(statement=sensitivity_text, origin="system_guardrail"),
            DecisionTextItem(
                statement=(
                    "Visibilité globale et seuil d’adoption ne sont pas identifiables "
                    "séparément dans les scénarios sans broadcast (équivalence theta/v)."
                ),
                origin="system_guardrail",
            ),
            DecisionTextItem(
                statement=(
                    "Broadcast a une unité de ressource différente et apparaît seulement "
                    "comme référence contextuelle, hors classement."
                ),
                origin="system_guardrail",
            ),
            DecisionTextItem(
                statement="Le moteur n’est calibré sur aucune organisation réelle.",
                origin="system_guardrail",
            ),
        ],
        next_data=[
            NextDataItem(
                data="Distribution empirique des seuils ou besoins de preuve sociale",
                why_it_matters="C’est un déterminant majeur et sensible du classement.",
                collection_hint=(
                    "Observer un pilote borné : exposition, nombre de pairs visibles et "
                    "passage à un usage de production, sans déduire de traits individuels."
                ),
            ),
            NextDataItem(
                data="Carte agrégée des collaborations entre équipes",
                why_it_matters="Elle réduit l’incertitude sur la force des silos.",
                collection_hint=(
                    "Collecter des comptes agrégés et anonymisés de collaborations, avec "
                    "revue juridique et minimisation des données."
                ),
            ),
        ],
        synthetic_disclaimer=(
            "Tous les résultats sont synthétiques, non calibrés et conditionnels aux "
            "hypothèses ; cette fiche n’est pas une prévision d’un déploiement réel."
        ),
        generated_by="offline_fixture",
    )
    card = assign_card_id(card, result)
    verify_decision_card(card, result)
    return card
