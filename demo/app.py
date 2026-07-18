"""NormLab Build Week demo: language → protocol → engine → decision card."""

from __future__ import annotations

import json
import os
import pathlib
import sys
import uuid

import pandas as pd
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from normlab.decisions import build_offline_decision_card
from normlab.protocols import (
    apply_user_overrides,
    design_offline_protocol,
    iter_sourced_values,
    mandatory_critique,
)
from normlab.runner import run_experiment
from normlab.sol import SolClient


st.set_page_config(
    page_title="NormLab — expériences de changement",
    page_icon="◐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
  .stApp { background: #F7F5F0; }
  .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 5rem; }
  h1, h2, h3 { letter-spacing: -0.035em; }
  h1 { font-size: 3.3rem !important; line-height: 0.98 !important; }
  .eyebrow { text-transform: uppercase; letter-spacing: .16em; font-size: .72rem;
             font-weight: 700; color: #6D4AFF; }
  .hero-copy { font-size: 1.18rem; color: #4D4858; max-width: 760px; line-height: 1.55; }
  .mode-pill { display:inline-block; border:1px solid #C7BFFF; border-radius:99px;
               padding:.3rem .7rem; background:#F0EDFF; color:#4D35C8;
               font-size:.76rem; font-weight:700; }
  .honesty { border-left: 4px solid #E34F4F; padding: .8rem 1rem; background:#FFF1EF;
             margin: 1rem 0 1.5rem; color:#612A28; }
  .step { color:#6D4AFF; font-weight:800; font-size:.8rem; letter-spacing:.1em; }
  [data-testid="stMetric"] { background:#FFFFFF; border:1px solid #E1DDD3;
                             padding:1rem; border-radius:14px; }
  [data-testid="stForm"] { background:#FFFFFF; border:1px solid #DED9CF;
                           padding:1.2rem; border-radius:18px; }
  div[data-testid="stExpander"] { background:#FFFFFF; border-radius:14px; }
  .decision-block { background:#FFFFFF; border:1px solid #DED9CF; border-radius:16px;
                    padding:1rem 1.1rem; min-height:160px; }
  .source-provided { color:#146C43; font-weight:700; }
  .source-inferred { color:#9A5A00; font-weight:700; }
  .source-system_default { color:#574F67; font-weight:700; }
</style>
""",
    unsafe_allow_html=True,
)


def _api_key() -> str | None:
    session_key = str(st.session_state.get("user_api_key", "")).strip()
    if session_key:
        return session_key
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    try:
        candidate = str(st.secrets.get("OPENAI_API_KEY", "")).strip()
        return candidate or None
    except Exception:
        return None


def _clear_user_api_key() -> None:
    st.session_state.user_api_key = ""
    st.session_state.pop("package", None)
    st.session_state.pop("sol_trace", None)
    st.session_state.pop("result", None)
    st.session_state.pop("card", None)
    st.session_state.pop("run_notice", None)


def _source_label(source: str) -> str:
    labels = {
        "provided": "Fourni par vous",
        "inferred": "Hypothèse Sol",
        "system_default": "Défaut versionné",
    }
    return labels.get(source, source)


def _protocol_table(protocol) -> pd.DataFrame:
    rows = []
    for path, sourced in iter_sourced_values(protocol):
        value = sourced.value
        if isinstance(value, list):
            value = ", ".join(value)
        else:
            value = str(value)
        source = sourced.source.value
        rows.append(
            {
                "Champ": path,
                "Valeur": value,
                "Provenance": _source_label(source),
                "Justification": sourced.justification,
            }
        )
    return pd.DataFrame(rows)


def _pct(value: float) -> str:
    return f"{100 * value:.1f} %"


if "session_identifier" not in st.session_state:
    st.session_state.session_identifier = str(uuid.uuid4())

with st.sidebar:
    st.subheader("Tester GPT‑5.6 Sol")
    st.caption(
        "Facultatif : utilisez une clé API de projet. Elle reste dans cette session "
        "et n’est ni enregistrée par NormLab, ni incluse dans les exports."
    )
    st.text_input(
        "Clé API OpenAI temporaire",
        type="password",
        key="user_api_key",
        placeholder="sk-…",
        help=(
            "Les appels sont facturés au compte associé à cette clé. "
            "N’utilisez pas une clé personnelle non plafonnée sur un appareil partagé."
        ),
    )
    if str(st.session_state.get("user_api_key", "")).strip():
        st.success("Clé temporaire chargée pour cette session.")
        st.button("Effacer la clé et la session", on_click=_clear_user_api_key)
    st.caption("Sans clé, la démonstration reproductible hors ligne reste disponible.")

key = _api_key()
user_supplied_key = bool(str(st.session_state.get("user_api_key", "")).strip())
if user_supplied_key:
    mode = "GPT‑5.6 Sol actif — clé temporaire du juré"
elif key:
    mode = "GPT‑5.6 Sol actif — clé de déploiement"
else:
    mode = "Fixture hors ligne — Sol non appelé"

st.markdown('<div class="eyebrow">OpenAI Build Week 2026 · NormLab</div>', unsafe_allow_html=True)
st.title("Expérimenter avant de recommander.")
st.markdown(
    '<div class="hero-copy">Décrivez un problème d’adoption de l’IA. GPT‑5.6 Sol '
    "le transforme en protocole inspectable, critique les hypothèses, puis appelle "
    "un moteur déterministe d’agents à seuil. Le moteur tranche ; Sol explique.</div>",
    unsafe_allow_html=True,
)
st.markdown(f'<span class="mode-pill">{mode}</span>', unsafe_allow_html=True)
st.markdown(
    '<div class="honesty"><strong>Pas une prévision.</strong> Toutes les organisations, '
    "seuils et sorties sont synthétiques et non calibrés. NormLab compare des mécanismes "
    "sous hypothèses ; il ne prédit aucun déploiement réel.</div>",
    unsafe_allow_html=True,
)

st.markdown('<div class="step">01 · QUESTION</div>', unsafe_allow_html=True)
default_question = (
    "Notre organisation compte 600 personnes dans 6 départements. Nous voulons faire "
    "adopter un copilote IA pour préparer des livrables clients, mais les équipes "
    "travaillent en silos. Nous pouvons accompagner 5 % des collaborateurs comme pilotes. "
    "Faut-il disperser les pilotes, choisir des champions, saturer quelques équipes ou "
    "commencer par les managers ?"
)
question = st.text_area(
    "Problème de changement organisationnel",
    value=st.session_state.get("question", default_question),
    height=150,
    help="N’ajoutez aucune donnée personnelle ou confidentielle.",
)
design_clicked = st.button("Concevoir et critiquer le protocole", type="primary")

if design_clicked:
    st.session_state.question = question
    try:
        with st.spinner("Sol formalise l’expérience…" if key else "Construction de la fixture inspectable…"):
            if key:
                client = SolClient(
                    api_key=key,
                    session_identifier=st.session_state.session_identifier,
                )
                package, trace = client.design_protocol(question)
            else:
                package = design_offline_protocol(question)
                trace = None
        st.session_state.package = package
        st.session_state.sol_trace = trace
        st.session_state.pop("result", None)
        st.session_state.pop("card", None)
        st.session_state.pop("run_notice", None)
    except Exception as exc:
        st.error(f"Le protocole n’a pas pu être construit : {exc}")

package = st.session_state.get("package")
if package is not None:
    protocol = package.protocol
    st.divider()
    st.markdown('<div class="step">02 · PROTOCOLE INSPECTABLE</div>', unsafe_allow_html=True)
    header_left, header_right = st.columns([3, 1])
    header_left.subheader(protocol.decision_context.value)
    header_right.code(protocol.protocol_id, language=None)
    if package.generated_by == "offline_fixture":
        st.warning(
            "Mode hors ligne : ce protocole provient d’une fixture déterministe, pas de Sol. "
            "Pour une expérience en direct, ouvrez la barre latérale et fournissez "
            "temporairement une clé API OpenAI."
        )

    tabs = st.tabs(["Tous les champs", "Fourni par vous", "Hypothèses", "Défauts"])
    frame = _protocol_table(protocol)
    with tabs[0]:
        st.dataframe(frame, width="stretch", hide_index=True)
    for tab, label in zip(tabs[1:], ["Fourni par vous", "Hypothèse Sol", "Défaut versionné"]):
        with tab:
            st.dataframe(
                frame[frame["Provenance"] == label], width="stretch", hide_index=True
            )

    st.markdown("#### Critique de l’expérience")
    critique_rows = [
        {
            "Sévérité": item.severity.value,
            "Code": item.code.value,
            "Diagnostic": item.message,
        }
        for item in package.critique.items
    ]
    st.dataframe(pd.DataFrame(critique_rows), width="stretch", hide_index=True)

    with st.expander("Ajuster les paramètres avant exécution", expanded=True):
        with st.form("protocol_editor"):
            a, b, c = st.columns(3)
            n_agents = a.number_input(
                "Population synthétique", 200, 3000, protocol.organization.n_agents.value, 50
            )
            n_departments = b.number_input(
                "Départements", 2, 20, protocol.organization.n_departments.value, 1
            )
            silo_strength = c.slider(
                "Force des silos", 0.0, 1.0, float(protocol.organization.silo_strength.value), 0.05
            )
            d, e, f = st.columns(3)
            theta_mean = d.slider(
                "Seuil moyen", 0.05, 0.60, float(protocol.adoption.theta_mean.value), 0.01
            )
            theta_concentration = e.slider(
                "Homogénéité des seuils κ", 4.0, 50.0,
                float(protocol.adoption.theta_concentration.value), 1.0
            )
            visibility = f.slider(
                "Visibilité des usages", 0.2, 1.0, float(protocol.adoption.visibility.value), 0.05
            )
            g, h, i = st.columns(3)
            budget_percent = g.slider(
                "Budget pilotes (%)", 1, 15,
                int(round(100 * protocol.interventions.seed_budget_fraction.value)), 1,
            )
            replicates = h.slider(
                "Réplications appariées", 3, 20, protocol.execution.replicates.value, 1
            )
            master_seed = i.number_input(
                "Graine maître", 0, 2_147_483_647, protocol.execution.master_seed.value, 1
            )
            strategies = st.multiselect(
                "Stratégies classées à budget égal",
                ["random", "champions", "cluster", "line_manager_first"],
                default=protocol.interventions.ranked_strategies.value,
            )
            execute_clicked = st.form_submit_button(
                "Approuver et exécuter l’expérience", type="primary"
            )

    if execute_clicked:
        try:
            approved = apply_user_overrides(
                protocol,
                n_agents=int(n_agents),
                n_departments=int(n_departments),
                silo_strength=float(silo_strength),
                theta_mean=float(theta_mean),
                theta_concentration=float(theta_concentration),
                visibility=float(visibility),
                seed_budget_fraction=float(budget_percent) / 100.0,
                replicates=int(replicates),
                master_seed=int(master_seed),
                strategies=list(strategies),
            )
            st.session_state.package = package.model_copy(
                update={
                    "protocol": approved,
                    "critique": mandatory_critique(approved),
                }
            )
            with st.spinner("Le moteur déterministe exécute les scénarios appariés…"):
                if key and package.generated_by == "gpt-5.6-sol":
                    client = SolClient(
                        api_key=key,
                        session_identifier=st.session_state.session_identifier,
                    )
                    result, card, trace = client.run_and_synthesize(
                        approved, run_experiment, st.session_state.get("sol_trace")
                    )
                    notice = "Sol a appelé l’outil déterministe puis produit une fiche vérifiée."
                    st.session_state.sol_trace = trace
                else:
                    result = run_experiment(approved)
                    card = build_offline_decision_card(approved, result)
                    notice = (
                        "Exécution locale et fiche déterministe hors ligne ; aucune réponse "
                        "Sol n’a été simulée."
                    )
            st.session_state.result = result
            st.session_state.card = card
            st.session_state.run_notice = notice
        except Exception as exc:
            st.error(f"L’expérience a échoué sans être présentée comme terminée : {exc}")

result = st.session_state.get("result")
card = st.session_state.get("card")
if result is not None and card is not None:
    protocol = st.session_state.package.protocol
    st.divider()
    st.markdown('<div class="step">03 · RÉSULTATS DU MOTEUR</div>', unsafe_allow_html=True)
    st.info(st.session_state.get("run_notice", ""))
    summaries = {item.strategy: item for item in result.ranked_summaries}
    leader = summaries[result.base_ranking[0]]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Leader central", result.base_ranking[0].replace("_", " "))
    m2.metric("Adoption synthétique", _pct(leader.final_adoption_mean))
    m3.metric("Budget comparable", f"{leader.seed_count} pilotes / stratégie")
    m4.metric("Classement sensible", "Oui" if result.ranking_is_sensitive else "Non")

    summary_rows = [
        {
            "Rang": result.base_ranking.index(item.strategy) + 1,
            "Stratégie": item.strategy,
            "Moyenne": item.final_adoption_mean,
            "P10": item.final_adoption_p10,
            "P90": item.final_adoption_p90,
            "Seeds": item.seed_count,
            "Départements morts (moy.)": item.dead_departments_mean,
        }
        for item in sorted(
            result.ranked_summaries,
            key=lambda row: result.base_ranking.index(row.strategy),
        )
    ]
    st.dataframe(
        pd.DataFrame(summary_rows).style.format(
            {"Moyenne": "{:.1%}", "P10": "{:.1%}", "P90": "{:.1%}"}
        ),
        width="stretch",
        hide_index=True,
    )

    curve_rows = []
    for item in result.ranked_summaries:
        curve_rows.extend(
            {"Étape": step, "Adoption": value, "Stratégie": item.strategy}
            for step, value in enumerate(item.curve.mean)
        )
    curve_frame = pd.DataFrame(curve_rows).pivot(
        index="Étape", columns="Stratégie", values="Adoption"
    )
    st.line_chart(curve_frame, y_label="Adoption synthétique", x_label="Ronde abstraite")

    if result.broadcast_reference is not None:
        with st.expander("Référence contextuelle non comparable : broadcast"):
            st.metric(
                "Adoption synthétique moyenne",
                _pct(result.broadcast_reference.final_adoption_mean),
                help="Zéro seed ; une exposition centrale. Hors classement principal.",
            )
            st.caption(
                "Broadcast n’utilise pas la même unité de ressource. NormLab refuse "
                "donc de le classer avec les stratégies à budget de pilotes égal."
            )

    st.markdown("#### Sensibilité des conclusions")
    sensitivity_frame = pd.DataFrame(
        [
            {
                "Facteur": item.factor,
                "Niveau": item.level,
                "Valeur": item.value,
                "Leader": item.top_strategy,
                "Adoption du leader": item.top_final_adoption,
                "Classement changé": item.ranking_changed,
            }
            for item in result.sensitivity
        ]
    )
    st.dataframe(
        sensitivity_frame.style.format({"Adoption du leader": "{:.1%}"}),
        width="stretch",
        hide_index=True,
    )
    for flag in result.non_identifiability:
        st.warning(f"Non-identifiabilité — {flag.explanation} {flag.consequence}")

    st.divider()
    st.markdown('<div class="step">04 · FICHE DE DÉCISION</div>', unsafe_allow_html=True)
    st.subheader(card.title)
    st.write(card.verdict)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("#### Résultats")
        for item in card.results:
            st.write(item.statement)
            for ev in item.evidence:
                formatted = _pct(ev.value) if ev.unit == "fraction" else f"{ev.value:.1f}"
                st.caption(f"{ev.strategy} · {ev.metric} = {formatted}")
    with c2:
        st.markdown("#### Hypothèses")
        for item in card.assumptions:
            st.write("• " + item.statement)
    with c3:
        st.markdown("#### Limites")
        for item in card.limitations:
            st.write("• " + item.statement)
    with c4:
        st.markdown("#### Prochaine donnée")
        for item in card.next_data:
            st.write("• **" + item.data + "**")
            st.caption(item.why_it_matters)

    st.markdown(
        f'<div class="honesty"><strong>{card.synthetic_disclaimer}</strong></div>',
        unsafe_allow_html=True,
    )
    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "Télécharger le protocole JSON",
        protocol.model_dump_json(indent=2),
        file_name=f"{protocol.protocol_id}.json",
        mime="application/json",
    )
    d2.download_button(
        "Télécharger les résultats JSON",
        result.model_dump_json(indent=2),
        file_name=f"{result.result_id}.json",
        mime="application/json",
    )
    d3.download_button(
        "Télécharger la fiche JSON",
        card.model_dump_json(indent=2),
        file_name=f"{card.card_id}.json",
        mime="application/json",
    )
    with st.expander("Trace d’audit de cette exécution"):
        trace = st.session_state.get("sol_trace")
        st.json(
            {
                "protocol_id": protocol.protocol_id,
                "result_id": result.result_id,
                "decision_card_id": card.card_id,
                "engine_version": result.engine_version,
                "engine_source_commit": result.engine_source_commit,
                "model_trace": trace.model_dump(mode="json") if trace else None,
                "raw_replications_in_result_export": len(result.raw_runs),
                "secrets_recorded": False,
                "private_reasoning_recorded": False,
            }
        )

st.divider()
st.caption(
    "NormLab · Build Week 2026 · GPT‑5.6 Sol conçoit et critique ; adoption-sim "
    "0.1.0 calcule ; les garde-fous locaux vérifient budget, provenance et preuves."
)
