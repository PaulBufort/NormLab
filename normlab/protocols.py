"""Protocol construction, stable identifiers and non-LLM guardrails."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .models import (
    AdoptionSpec,
    Assumption,
    CritiqueCode,
    CritiqueItem,
    CritiqueSeverity,
    ExecutionSpec,
    ExperimentCritique,
    ExperimentProtocol,
    FloatValue,
    IntValue,
    InterventionSpec,
    OrganizationSpec,
    ProtocolPackage,
    Provenance,
    SensitivityFactor,
    StrategySet,
    TextValue,
)
from .prompts import DESIGN_PROMPT_VERSION


DEFAULTS: dict[str, Any] = {
    "n_agents": 600,
    "n_departments": 6,
    "mean_team_size": 8,
    "silo_strength": 0.80,
    "theta_mean": 0.30,
    "theta_concentration": 20.0,
    "p_innovator": 0.025,
    "willingness": 0.85,
    "able_rate": 1.0,
    "visibility": 1.0,
    "relapse_probability": 0.0,
    "seed_budget_fraction": 0.05,
    "replicates": 4,
    "master_seed": 20260718,
    "max_steps": 60,
}


def _int(value: int, source: Provenance, reason: str) -> IntValue:
    return IntValue(value=value, source=source, justification=reason)


def _float(value: float, source: Provenance, reason: str) -> FloatValue:
    return FloatValue(value=value, source=source, justification=reason)


def _search_number(question: str, patterns: list[str], cast: type) -> Any | None:
    for pattern in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if match:
            raw = match.group(1).replace(",", ".")
            return cast(float(raw)) if cast is int else cast(raw)
    return None


def _provided_or_default(
    question: str,
    patterns: list[str],
    default_key: str,
    cast: type,
    provided_reason: str,
) -> tuple[Any, Provenance, str]:
    found = _search_number(question, patterns, cast)
    if found is not None:
        return found, Provenance.PROVIDED, provided_reason
    return (
        DEFAULTS[default_key],
        Provenance.SYSTEM_DEFAULT,
        "Valeur par défaut versionnée du MVP NormLab.",
    )


def assign_protocol_id(protocol: ExperimentProtocol) -> ExperimentProtocol:
    """Replace any model-supplied ID with a stable content hash."""
    payload = protocol.model_copy(update={"protocol_id": "content-addressed"})
    canonical = json.dumps(
        payload.model_dump(mode="json"), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return protocol.model_copy(update={"protocol_id": f"nlp-{digest}"})


def mandatory_critique(protocol: ExperimentProtocol) -> ExperimentCritique:
    """Guardrails that prose from Sol cannot remove."""
    inferred = []
    for path, value in iter_sourced_values(protocol):
        if value.source != Provenance.PROVIDED:
            inferred.append(path)
    items = [
        CritiqueItem(
            code=CritiqueCode.SYNTHETIC_NOT_FORECAST,
            severity=CritiqueSeverity.WARNING,
            message=(
                "Les résultats seront produits sur des organisations et comportements "
                "synthétiques non calibrés ; ils ne constituent pas une prévision."
            ),
            field_paths=[],
        ),
        CritiqueItem(
            code=CritiqueCode.NON_IDENTIFIABLE,
            severity=CritiqueSeverity.WARNING,
            message=(
                "Dans les scénarios sans broadcast, réduire la visibilité globale v "
                "est exactement équivalent à augmenter les seuils theta/v. Ces deux "
                "explications ne sont pas identifiables séparément."
            ),
            field_paths=["adoption.theta_mean", "adoption.visibility"],
        ),
        CritiqueItem(
            code=CritiqueCode.BUDGET_NON_COMPARABLE,
            severity=CritiqueSeverity.INFO,
            message=(
                "Broadcast utilise une exposition de communication et zéro seed ; il "
                "sera affiché séparément du classement à budget de seeds égal."
            ),
            field_paths=["interventions.broadcast_context_reference"],
        ),
        CritiqueItem(
            code=CritiqueCode.STRONG_ASSUMPTION,
            severity=CritiqueSeverity.WARNING,
            message=(
                "La distribution des seuils et les poids de crédibilité ne sont pas "
                "mesurés dans l’organisation décrite et peuvent changer le classement."
            ),
            field_paths=["adoption.theta_mean", "adoption.theta_concentration"],
        ),
        CritiqueItem(
            code=CritiqueCode.MISSING_USER_DATA,
            severity=CritiqueSeverity.WARNING,
            message=(
                f"{len(inferred)} champs du protocole ne viennent pas directement de "
                "l’utilisateur ; ils restent inspectables avant exécution."
            ),
            field_paths=inferred[:8],
        ),
    ]
    return ExperimentCritique(
        summary=(
            "Protocole exécutable comme expérience synthétique, sous réserve de "
            "conserver visibles les hypothèses et la sensibilité."
        ),
        items=items,
    )


def merge_mandatory_critique(
    protocol: ExperimentProtocol, critique: ExperimentCritique
) -> ExperimentCritique:
    mandatory = mandatory_critique(protocol)
    by_code = {item.code: item for item in critique.items}
    for item in mandatory.items:
        by_code[item.code] = item
    return ExperimentCritique(summary=critique.summary, items=list(by_code.values()))


def normalize_package(package: ProtocolPackage) -> ProtocolPackage:
    protocol = assign_protocol_id(package.protocol)
    critique = merge_mandatory_critique(protocol, package.critique)
    return package.model_copy(update={"protocol": protocol, "critique": critique})


def ground_protocol_in_question(
    protocol: ExperimentProtocol, question: str
) -> ExperimentProtocol:
    """Keep the verbatim question and downgrade unsupported numeric provenance.

    This is intentionally lexical, not semantic: it prevents Sol from promoting an
    invented number to a user fact. It does not claim to understand units or intent.
    Any downgraded value remains visible as an inference for human review.
    """
    grounded = protocol.model_copy(deep=True)
    grounded.question = TextValue(
        value=question.strip(),
        source=Provenance.PROVIDED,
        justification="Texte exact saisi par l’utilisateur.",
    )
    number_tokens = [
        (float(match.group(1).replace(",", ".")), bool(match.group(2)))
        for match in re.finditer(r"(-?\d+(?:[.,]\d+)?)\s*(%)?", question)
    ]

    def is_supported(value: int | float) -> bool:
        if isinstance(value, int):
            return any(
                not is_percent and abs(raw - value) < 1e-12
                for raw, is_percent in number_tokens
            )
        return any(
            abs((raw / 100.0 if is_percent else raw) - value) < 1e-12
            for raw, is_percent in number_tokens
        )

    for path, sourced in iter_sourced_values(grounded):
        if path == "question":
            continue
        if (
            isinstance(sourced, TextValue)
            and sourced.source == Provenance.PROVIDED
        ):
            sourced.source = Provenance.INFERRED
            sourced.justification = (
                "Provenance corrigée par le garde-fou local : ce texte est une "
                "formalisation du problème, pas la question utilisateur verbatim."
            )
            continue
        if (
            isinstance(sourced, (IntValue, FloatValue))
            and sourced.source == Provenance.PROVIDED
            and not is_supported(sourced.value)
        ):
            sourced.source = Provenance.INFERRED
            sourced.justification = (
                "Provenance corrigée par le garde-fou local : cette valeur numérique "
                "n’apparaît pas dans la question utilisateur."
            )
        default_key = path.rsplit(".", 1)[-1]
        if (
            isinstance(sourced, (IntValue, FloatValue))
            and sourced.source == Provenance.SYSTEM_DEFAULT
            and default_key in DEFAULTS
            and abs(sourced.value - DEFAULTS[default_key]) > 1e-12
        ):
            sourced.source = Provenance.INFERRED
            sourced.justification = (
                "Provenance corrigée par le garde-fou local : cette valeur diffère "
                "du défaut système versionné."
            )
    return assign_protocol_id(
        ExperimentProtocol.model_validate(grounded.model_dump(mode="json"))
    )


def iter_sourced_values(protocol: ExperimentProtocol):
    groups = {
        "question": protocol.question,
        "decision_context": protocol.decision_context,
        "organization.n_agents": protocol.organization.n_agents,
        "organization.n_departments": protocol.organization.n_departments,
        "organization.mean_team_size": protocol.organization.mean_team_size,
        "organization.silo_strength": protocol.organization.silo_strength,
        "adoption.behavior_definition": protocol.adoption.behavior_definition,
        "adoption.theta_mean": protocol.adoption.theta_mean,
        "adoption.theta_concentration": protocol.adoption.theta_concentration,
        "adoption.p_innovator": protocol.adoption.p_innovator,
        "adoption.willingness": protocol.adoption.willingness,
        "adoption.able_rate": protocol.adoption.able_rate,
        "adoption.visibility": protocol.adoption.visibility,
        "adoption.relapse_probability": protocol.adoption.relapse_probability,
        "interventions.ranked_strategies": protocol.interventions.ranked_strategies,
        "interventions.seed_budget_fraction": protocol.interventions.seed_budget_fraction,
        "execution.replicates": protocol.execution.replicates,
        "execution.master_seed": protocol.execution.master_seed,
        "execution.max_steps": protocol.execution.max_steps,
    }
    yield from groups.items()


def apply_user_overrides(
    protocol: ExperimentProtocol,
    *,
    n_agents: int,
    n_departments: int,
    silo_strength: float,
    theta_mean: float,
    theta_concentration: float,
    visibility: float,
    seed_budget_fraction: float,
    replicates: int,
    master_seed: int,
    strategies: list[str],
) -> ExperimentProtocol:
    """Apply visible UI edits and mark only changed values as user-provided."""

    def changed_int(old: IntValue, new: int) -> IntValue:
        if old.value == new:
            return old
        return IntValue(
            value=new,
            source=Provenance.PROVIDED,
            justification="Valeur modifiée explicitement par l’utilisateur avant exécution.",
        )

    def changed_float(old: FloatValue, new: float) -> FloatValue:
        if abs(old.value - new) < 1e-12:
            return old
        return FloatValue(
            value=new,
            source=Provenance.PROVIDED,
            justification="Valeur modifiée explicitement par l’utilisateur avant exécution.",
        )

    org = protocol.organization.model_copy(
        update={
            "n_agents": changed_int(protocol.organization.n_agents, n_agents),
            "n_departments": changed_int(
                protocol.organization.n_departments, n_departments
            ),
            "silo_strength": changed_float(
                protocol.organization.silo_strength, silo_strength
            ),
        }
    )
    adoption = protocol.adoption.model_copy(
        update={
            "theta_mean": changed_float(protocol.adoption.theta_mean, theta_mean),
            "theta_concentration": changed_float(
                protocol.adoption.theta_concentration, theta_concentration
            ),
            "visibility": changed_float(protocol.adoption.visibility, visibility),
        }
    )
    ranked = protocol.interventions.ranked_strategies
    if list(ranked.value) != list(strategies):
        ranked = StrategySet(
            value=strategies,
            source=Provenance.PROVIDED,
            justification="Stratégies sélectionnées explicitement avant exécution.",
        )
    interventions = protocol.interventions.model_copy(
        update={
            "ranked_strategies": ranked,
            "seed_budget_fraction": changed_float(
                protocol.interventions.seed_budget_fraction, seed_budget_fraction
            ),
        }
    )
    execution = protocol.execution.model_copy(
        update={
            "replicates": changed_int(protocol.execution.replicates, replicates),
            "master_seed": changed_int(protocol.execution.master_seed, master_seed),
        }
    )
    updated = protocol.model_copy(
        update={
            "organization": org,
            "adoption": adoption,
            "interventions": interventions,
            "execution": execution,
        }
    )
    return assign_protocol_id(ExperimentProtocol.model_validate(updated.model_dump()))


def design_offline_protocol(question: str) -> ProtocolPackage:
    """Deterministic fixture for tests and no-key demos; never presented as Sol."""
    question = question.strip()
    if len(question) < 20:
        raise ValueError("Décrivez le problème en au moins 20 caractères.")

    n_agents, n_agents_src, n_agents_reason = _provided_or_default(
        question,
        [r"(\d{3,4})\s*(?:personnes|collaborateurs|salariés|employees|people)"],
        "n_agents", int, "Taille explicitement fournie dans la question.",
    )
    n_depts, n_depts_src, n_depts_reason = _provided_or_default(
        question,
        [r"(\d{1,2})\s*(?:départements|departments|directions|units|unités)"],
        "n_departments", int, "Nombre d’unités explicitement fourni.",
    )
    budget, budget_src, budget_reason = _provided_or_default(
        question,
        [
            r"(?:budget|pilotes?|seeds?|champions?).{0,24}?(\d+(?:[.,]\d+)?)\s*%",
            r"(\d+(?:[.,]\d+)?)\s*%\s*(?:de\s*)?(?:pilotes?|seeds?|champions?)",
        ],
        "seed_budget_fraction", float, "Budget pilote explicitement fourni.",
    )
    if budget_src == Provenance.PROVIDED:
        budget /= 100.0

    protocol = ExperimentProtocol(
        protocol_id="draft",
        question=TextValue(
            value=question, source=Provenance.PROVIDED,
            justification="Texte exact saisi par l’utilisateur.",
        ),
        decision_context=TextValue(
            value="Comparer des stratégies de lancement d’un usage coûteux de l’IA.",
            source=Provenance.INFERRED,
            justification="Objectif expérimental déduit de la demande d’adoption.",
        ),
        organization=OrganizationSpec(
            n_agents=_int(n_agents, n_agents_src, n_agents_reason),
            n_departments=_int(n_depts, n_depts_src, n_depts_reason),
            mean_team_size=_int(
                DEFAULTS["mean_team_size"], Provenance.SYSTEM_DEFAULT,
                "Valeur par défaut versionnée du moteur historique.",
            ),
            silo_strength=_float(
                DEFAULTS["silo_strength"], Provenance.SYSTEM_DEFAULT,
                "Structure en silos non quantifiée par l’utilisateur.",
            ),
        ),
        adoption=AdoptionSpec(
            behavior_definition=TextValue(
                value=(
                    "Usage de production coûteux de l’IA nécessitant une réorganisation "
                    "du travail, et non une utilisation superficielle."
                ),
                source=Provenance.INFERRED,
                justification="Définition compatible avec le domaine du moteur à seuil.",
            ),
            theta_mean=_float(DEFAULTS["theta_mean"], Provenance.SYSTEM_DEFAULT,
                              "Seuil réel non observé."),
            theta_concentration=_float(
                DEFAULTS["theta_concentration"], Provenance.SYSTEM_DEFAULT,
                "Hétérogénéité réelle non observée.",
            ),
            p_innovator=_float(DEFAULTS["p_innovator"], Provenance.SYSTEM_DEFAULT,
                               "Masse historique d’innovateurs du moteur."),
            willingness=_float(DEFAULTS["willingness"], Provenance.SYSTEM_DEFAULT,
                               "Disposition non mesurée."),
            able_rate=_float(DEFAULTS["able_rate"], Provenance.SYSTEM_DEFAULT,
                             "Accès supposé complet faute d’information."),
            visibility=_float(DEFAULTS["visibility"], Provenance.SYSTEM_DEFAULT,
                              "Visibilité supposée complète faute d’information."),
            relapse_probability=_float(
                DEFAULTS["relapse_probability"], Provenance.SYSTEM_DEFAULT,
                "Décroissance désactivée dans la comparaison centrale.",
            ),
        ),
        interventions=InterventionSpec(
            ranked_strategies=StrategySet(
                value=["random", "champions", "cluster", "line_manager_first"],
                source=Provenance.INFERRED,
                justification="Ensemble comparable validé par l’arbitrage A3.",
            ),
            seed_budget_fraction=_float(budget, budget_src, budget_reason),
            broadcast_context_reference=True,
        ),
        execution=ExecutionSpec(
            replicates=_int(DEFAULTS["replicates"], Provenance.SYSTEM_DEFAULT,
                            "Compromis interactif précision/latence."),
            master_seed=_int(DEFAULTS["master_seed"], Provenance.SYSTEM_DEFAULT,
                             "Graine publique versionnée."),
            max_steps=_int(DEFAULTS["max_steps"], Provenance.SYSTEM_DEFAULT,
                           "Horizon abstrait du MVP."),
            paired_common_organizations=True,
        ),
        sensitivity=[
            SensitivityFactor(name="theta_mean", low=0.22, high=0.38,
                              rationale="Tester la résistance moyenne inconnue."),
            SensitivityFactor(name="theta_concentration", low=12.0, high=30.0,
                              rationale="Tester l’hétérogénéité inconnue des seuils."),
            SensitivityFactor(name="silo_strength", low=0.60, high=0.95,
                              rationale="Tester la connectivité entre unités."),
            SensitivityFactor(name="visibility", low=0.60, high=1.0,
                              rationale="Tester l’observabilité de l’usage."),
        ],
        assumptions=[
            Assumption(
                statement="L’adoption étudiée est un comportement coûteux à contagion complexe.",
                source=Provenance.INFERRED,
                impact="Une utilisation superficielle pourrait suivre une dynamique différente.",
            ),
            Assumption(
                statement="Les agents suivent les règles ready/willing/able historiques.",
                source=Provenance.SYSTEM_DEFAULT,
                impact="Le modèle n’inclut ni apprentissage stratégique ni persuasion temporelle.",
            ),
        ],
        missing_data=[
            "Distribution empirique des seuils d’adoption",
            "Structure des liens d’influence entre unités",
            "Coût comparable communication versus accompagnement pilote",
            "Visibilité réelle des usages de production",
        ],
        exclusions=[
            "Prévision d’un taux réel ou d’une date de déploiement",
            "Personas ou comportements pilotés par LLM",
            "Calibration sur données d’entreprise",
            "Classement de broadcast avec les stratégies à seeds égaux",
        ],
    )
    protocol = assign_protocol_id(protocol)
    return ProtocolPackage(
        protocol=protocol,
        critique=mandatory_critique(protocol),
        generated_by="offline_fixture",
        prompt_version=DESIGN_PROMPT_VERSION,
    )
