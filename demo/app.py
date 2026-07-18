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
    page_title="NormLab — organizational change experiments",
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
        "provided": "Provided by you",
        "inferred": "Sol assumption",
        "system_default": "Versioned default",
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
                "Field": path,
                "Value": value,
                "Provenance": _source_label(source),
                "Rationale": sourced.justification,
            }
        )
    return pd.DataFrame(rows)


def _pct(value: float) -> str:
    return f"{100 * value:.1f} %"


if "session_identifier" not in st.session_state:
    st.session_state.session_identifier = str(uuid.uuid4())

with st.expander("Test GPT‑5.6 Sol with a temporary API key", expanded=False):
    st.caption(
        "Optional: use a project API key. It remains in this session and is neither "
        "stored by NormLab nor included in exports."
    )
    st.text_input(
        "Temporary OpenAI API key",
        type="password",
        key="user_api_key",
        placeholder="sk-…",
        help=(
            "Calls are billed to the account associated with this key. Do not use an "
            "uncapped personal key on a shared device."
        ),
    )
    if str(st.session_state.get("user_api_key", "")).strip():
        st.success("Temporary key loaded for this session.")
        st.button("Clear key and session", on_click=_clear_user_api_key)
    st.caption("The reproducible offline demo remains available without a key.")

key = _api_key()
user_supplied_key = bool(str(st.session_state.get("user_api_key", "")).strip())
if user_supplied_key:
    mode = "GPT‑5.6 Sol active — temporary evaluator key"
elif key:
    mode = "GPT‑5.6 Sol active — deployment key"
else:
    mode = "Offline fixture — Sol not called"

st.markdown('<div class="eyebrow">OpenAI Build Week 2026 · NormLab</div>', unsafe_allow_html=True)
st.title("Experiment before you recommend.")
st.markdown(
    '<div class="hero-copy">Describe an organizational AI-adoption problem. GPT‑5.6 '
    "Sol turns it into an inspectable protocol, critiques the assumptions, then calls "
    "a deterministic threshold-agent engine. The engine decides; Sol explains.</div>",
    unsafe_allow_html=True,
)
st.markdown(f'<span class="mode-pill">{mode}</span>', unsafe_allow_html=True)
st.markdown(
    '<div class="honesty"><strong>Not a forecast.</strong> All organizations, thresholds, '
    "and outputs are synthetic and uncalibrated. NormLab compares mechanisms under "
    "assumptions; it does not predict a real deployment.</div>",
    unsafe_allow_html=True,
)

st.markdown('<div class="step">01 · QUESTION</div>', unsafe_allow_html=True)
default_question = (
    "Our organization has 600 people across 6 departments. We want teams to adopt an "
    "AI copilot for client deliverables, but they work in silos. We can support 5% of "
    "employees as initial pilots. Should we disperse the pilots, choose champions, "
    "saturate a few teams, or start with line managers?"
)
question = st.text_area(
    "Organizational change problem",
    value=st.session_state.get("question", default_question),
    height=150,
    help="Do not include personal, confidential, or proprietary information.",
)
design_clicked = st.button("Design and critique the protocol", type="primary")

if design_clicked:
    st.session_state.question = question
    try:
        with st.spinner("Sol is formalizing the experiment…" if key else "Building the inspectable fixture…"):
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
        st.error(f"The protocol could not be created: {exc}")

package = st.session_state.get("package")
if package is not None:
    protocol = package.protocol
    st.divider()
    st.markdown('<div class="step">02 · INSPECTABLE PROTOCOL</div>', unsafe_allow_html=True)
    header_left, header_right = st.columns([3, 1])
    header_left.subheader(protocol.decision_context.value)
    header_right.code(protocol.protocol_id, language=None)
    if package.generated_by == "offline_fixture":
        st.warning(
            "Offline mode: this protocol comes from a deterministic fixture, not Sol. "
            "For a live experiment, open “Test GPT‑5.6 Sol” at the top of the page "
            "and temporarily provide an OpenAI API key."
        )

    tabs = st.tabs(["All fields", "Provided by you", "Assumptions", "Defaults"])
    frame = _protocol_table(protocol)
    with tabs[0]:
        st.dataframe(frame, width="stretch", hide_index=True)
    for tab, label in zip(tabs[1:], ["Provided by you", "Sol assumption", "Versioned default"]):
        with tab:
            st.dataframe(
                frame[frame["Provenance"] == label], width="stretch", hide_index=True
            )

    st.markdown("#### Experiment critique")
    critique_rows = [
        {
            "Severity": item.severity.value,
            "Code": item.code.value,
            "Diagnostic": item.message,
        }
        for item in package.critique.items
    ]
    st.dataframe(pd.DataFrame(critique_rows), width="stretch", hide_index=True)

    with st.expander("Adjust parameters before execution", expanded=True):
        with st.form("protocol_editor"):
            a, b, c = st.columns(3)
            n_agents = a.number_input(
                "Synthetic population", 200, 3000, protocol.organization.n_agents.value, 50
            )
            n_departments = b.number_input(
                "Departments", 2, 20, protocol.organization.n_departments.value, 1
            )
            silo_strength = c.slider(
                "Silo strength", 0.0, 1.0, float(protocol.organization.silo_strength.value), 0.05
            )
            d, e, f = st.columns(3)
            theta_mean = d.slider(
                "Mean threshold", 0.05, 0.60, float(protocol.adoption.theta_mean.value), 0.01
            )
            theta_concentration = e.slider(
                "Threshold homogeneity κ", 4.0, 50.0,
                float(protocol.adoption.theta_concentration.value), 1.0
            )
            visibility = f.slider(
                "Usage visibility", 0.2, 1.0, float(protocol.adoption.visibility.value), 0.05
            )
            g, h, i = st.columns(3)
            budget_percent = g.slider(
                "Pilot budget (%)", 1, 15,
                int(round(100 * protocol.interventions.seed_budget_fraction.value)), 1,
            )
            replicates = h.slider(
                "Paired replications", 3, 20, protocol.execution.replicates.value, 1
            )
            master_seed = i.number_input(
                "Master seed", 0, 2_147_483_647, protocol.execution.master_seed.value, 1
            )
            strategies = st.multiselect(
                "Strategies ranked at equal budget",
                ["random", "champions", "cluster", "line_manager_first"],
                default=protocol.interventions.ranked_strategies.value,
            )
            execute_clicked = st.form_submit_button(
                "Approve and run the experiment", type="primary"
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
            with st.spinner("The deterministic engine is running paired scenarios…"):
                if key and package.generated_by == "gpt-5.6-sol":
                    client = SolClient(
                        api_key=key,
                        session_identifier=st.session_state.session_identifier,
                    )
                    result, card, trace = client.run_and_synthesize(
                        approved, run_experiment, st.session_state.get("sol_trace")
                    )
                    notice = "Sol called the deterministic tool and produced a verified decision card."
                    st.session_state.sol_trace = trace
                else:
                    result = run_experiment(approved)
                    card = build_offline_decision_card(approved, result)
                    notice = (
                        "Local execution and deterministic offline card; no Sol response "
                        "was simulated."
                    )
            st.session_state.result = result
            st.session_state.card = card
            st.session_state.run_notice = notice
        except Exception as exc:
            st.error(f"The experiment failed and was not presented as complete: {exc}")

result = st.session_state.get("result")
card = st.session_state.get("card")
if result is not None and card is not None:
    protocol = st.session_state.package.protocol
    st.divider()
    st.markdown('<div class="step">03 · ENGINE RESULTS</div>', unsafe_allow_html=True)
    st.info(st.session_state.get("run_notice", ""))
    summaries = {item.strategy: item for item in result.ranked_summaries}
    leader = summaries[result.base_ranking[0]]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Base-case leader", result.base_ranking[0].replace("_", " "))
    m2.metric("Synthetic adoption", _pct(leader.final_adoption_mean))
    m3.metric("Comparable budget", f"{leader.seed_count} pilots / strategy")
    m4.metric("Sensitive ranking", "Yes" if result.ranking_is_sensitive else "No")

    summary_rows = [
        {
            "Rank": result.base_ranking.index(item.strategy) + 1,
            "Strategy": item.strategy,
            "Mean": item.final_adoption_mean,
            "P10": item.final_adoption_p10,
            "P90": item.final_adoption_p90,
            "Seeds": item.seed_count,
            "Dead departments (mean)": item.dead_departments_mean,
        }
        for item in sorted(
            result.ranked_summaries,
            key=lambda row: result.base_ranking.index(row.strategy),
        )
    ]
    st.dataframe(
        pd.DataFrame(summary_rows).style.format(
            {"Mean": "{:.1%}", "P10": "{:.1%}", "P90": "{:.1%}"}
        ),
        width="stretch",
        hide_index=True,
    )

    curve_rows = []
    for item in result.ranked_summaries:
        curve_rows.extend(
            {"Step": step, "Adoption": value, "Strategy": item.strategy}
            for step, value in enumerate(item.curve.mean)
        )
    curve_frame = pd.DataFrame(curve_rows).pivot(
        index="Step", columns="Strategy", values="Adoption"
    )
    st.line_chart(curve_frame, y_label="Synthetic adoption", x_label="Abstract round")

    if result.broadcast_reference is not None:
        with st.expander("Non-comparable contextual reference: broadcast"):
            st.metric(
                "Mean synthetic adoption",
                _pct(result.broadcast_reference.final_adoption_mean),
                help="Zero seeds; one central exposure. Excluded from the main ranking.",
            )
            st.caption(
                "Broadcast does not use the same resource unit. NormLab therefore "
                "refuses to rank it alongside equal-pilot-budget strategies."
            )

    st.markdown("#### Sensitivity of conclusions")
    sensitivity_frame = pd.DataFrame(
        [
            {
                "Factor": item.factor,
                "Level": item.level,
                "Value": item.value,
                "Leader": item.top_strategy,
                "Leader adoption": item.top_final_adoption,
                "Ranking changed": item.ranking_changed,
            }
            for item in result.sensitivity
        ]
    )
    st.dataframe(
        sensitivity_frame.style.format({"Leader adoption": "{:.1%}"}),
        width="stretch",
        hide_index=True,
    )
    for flag in result.non_identifiability:
        st.warning(f"Non-identifiability — {flag.explanation} {flag.consequence}")

    st.divider()
    st.markdown('<div class="step">04 · DECISION CARD</div>', unsafe_allow_html=True)
    st.subheader(card.title)
    st.write(card.verdict)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("#### Results")
        for item in card.results:
            st.write(item.statement)
            for ev in item.evidence:
                formatted = _pct(ev.value) if ev.unit == "fraction" else f"{ev.value:.1f}"
                st.caption(f"{ev.strategy} · {ev.metric} = {formatted}")
    with c2:
        st.markdown("#### Assumptions")
        for item in card.assumptions:
            st.write("• " + item.statement)
    with c3:
        st.markdown("#### Limitations")
        for item in card.limitations:
            st.write("• " + item.statement)
    with c4:
        st.markdown("#### Next data")
        for item in card.next_data:
            st.write("• **" + item.data + "**")
            st.caption(item.why_it_matters)

    st.markdown(
        f'<div class="honesty"><strong>{card.synthetic_disclaimer}</strong></div>',
        unsafe_allow_html=True,
    )
    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "Download protocol JSON",
        protocol.model_dump_json(indent=2),
        file_name=f"{protocol.protocol_id}.json",
        mime="application/json",
    )
    d2.download_button(
        "Download results JSON",
        result.model_dump_json(indent=2),
        file_name=f"{result.result_id}.json",
        mime="application/json",
    )
    d3.download_button(
        "Download decision card JSON",
        card.model_dump_json(indent=2),
        file_name=f"{card.card_id}.json",
        mime="application/json",
    )
    with st.expander("Audit trace for this run"):
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
    "NormLab · Build Week 2026 · GPT‑5.6 Sol designs and critiques; adoption-sim "
    "0.1.0 computes; local guardrails verify budgets, provenance, and evidence."
)
