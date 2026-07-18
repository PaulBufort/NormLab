# Devpost submission copy — ready to paste

Official track: **Work and Productivity**

## Project name

NormLab

## Tagline

Experiment before you recommend AI adoption.

## Short description

GPT‑5.6 Sol turns organizational AI-adoption questions into inspectable protocols;
a deterministic threshold-agent engine compares equal-budget interventions and
exposes assumptions, sensitivity, non-identifiability, and the next data to collect.

## Project story

### Inspiration

AI-adoption decisions are often made before an organization has enough evidence to
separate plausible mechanisms. Should limited pilot support be dispersed, allocated
to highly connected champions, concentrated inside a few teams, or given to line
managers first? A persuasive narrative can answer that question too easily.

NormLab starts from a different principle: **GPT‑5.6 Sol designs and critiques the
experiment; a deterministic engine computes the result.** The product does not claim
to forecast a real organization. It makes assumptions inspectable and turns missing
evidence into a concrete data-collection agenda.

### What it does

An evaluator describes an organizational AI-adoption problem in natural language.
GPT‑5.6 Sol produces a typed protocol and critique. Every value is visibly labeled as
`provided`, `inferred`, or `system_default`. A human can inspect and edit the protocol
before approving execution.

NormLab then forces a strict tool call into a deterministic complex-contagion engine.
Four interventions are compared with identical pilot budgets, paired synthetic
organizations, and shared seeds. A broadcast intervention uses a different resource
unit and is therefore kept outside the main ranking. Coded sensitivity analysis
reports ranking changes, and a mandatory flag exposes the threshold/visibility
non-identifiability.

Finally, Sol writes a decision card grounded only in engine output. Local validators
check every numeric reference and keep Results, Assumptions, Limitations, and Next
data separate. All visible outputs state that the simulation is synthetic,
uncalibrated, and not a forecast.

### How we built it

NormLab uses Python, Streamlit, Pydantic, NetworkX, NumPy, pandas, pytest, and the
OpenAI Responses API with the explicit `gpt-5.6-sol` model. Sol uses structured
outputs for protocol and decision-card schemas and a single strict deterministic tool.
The integration uses `store=False`; no API key or private reasoning is written to the
repository or exports.

The numerical engine is a deterministic threshold-agent simulation. It existed
before Build Week and was frozen at commit
`0e2d2601332b64981a80c816a4820e5a5a25c669`. During Build Week, six required engine
files were ported verbatim under AGPL‑3.0 and verified by SHA-256 parity tests. The
language-to-protocol workflow, provenance model, validators, paired orchestrator,
budget ledger, sensitivity analysis, Sol tool integration, decision card, interface,
tests, audit exports, and deployment are all new Build Week work.

### How Codex contributed

The majority of NormLab’s core functionality was built in one primary Codex thread.
Codex first inspected the frozen historical project in read-only mode and documented
the pre-Build Week baseline. It proposed five explicit scientific and product
decisions; I reviewed and approved them before implementation. Codex then ported the
engine with attribution and parity checks, built the typed schemas and guardrails,
implemented the Sol integration and Streamlit product, wrote the tests and evals, and
deployed the public demo.

Codex also helped turn live failures into product safeguards. A truncated structured
response led to a bounded decision-card prompt and a tested token reserve. When Sol
omitted a required identifiability warning, Codex added a deterministic
`system_guardrail` layer while preserving visible provenance. This collaboration is
recorded in dated commits and `BUILD_WEEK.md`.

### Challenges

- Keeping Sol useful without allowing it to replace deterministic computation.
- Preserving user facts separately from model inferences and system defaults.
- Comparing strategies fairly despite different intervention mechanics.
- Showing sensitivity and non-identifiability without presenting synthetic results
  as forecasts.
- Making the live Sol path testable without committing or publicly funding an API key.

### Accomplishments

- A complete public journey from natural-language question to verified decision card.
- Deterministic reproducibility, paired scenarios, equal-budget checks, and raw-run
  exports.
- A live public GPT‑5.6 Sol smoke test with three coherent audit artifacts.
- 26 passing tests, including legacy parity, invented-evidence rejection, tool-call
  substitution rejection, and the offline Streamlit journey.
- Clear documentation separating the pre-existing engine from Build Week work.

### What we learned

LLMs are most credible in simulation products when they improve the experimental
contract rather than impersonate the simulated people. The difficult product problem
is not generating a recommendation; it is making provenance, comparability,
sensitivity, and uncertainty impossible to hide.

### What’s next

After Build Week, NormLab could add calibration workflows for aggregated,
privacy-preserving organizational data, protocol comparison across repeated pilots,
and exportable research reports. Those extensions would require validation and new
scientific decisions; they are intentionally outside this submission.

## Built with

- GPT‑5.6 Sol
- OpenAI Responses API
- Codex
- Python
- Streamlit
- Pydantic
- NetworkX
- NumPy and pandas
- pytest and GitHub Actions

## Links

- Live demo: https://normlab-build-week-2026.streamlit.app/
- Source code: https://github.com/PaulBufort/NormLab
- License: AGPL‑3.0-only
- YouTube demo: `[ADD AFTER UPLOAD]`
- Codex `/feedback` session ID: `[ADD BEFORE SUBMISSION]`

## Testing instructions for evaluators

1. Open the public demo. No account or API key is required.
2. Leave the app in **Offline fixture — Sol not called** mode.
3. Click **Design and critique the protocol**.
4. Inspect the provenance tabs and experiment critique.
5. Click **Approve and run the experiment** with the default parameters.
6. Review equal budgets, sensitivity, non-identifiability, the four decision-card
   sections, audit trace, and JSON downloads.

The offline journey is free, deterministic, and exercises the full interface and
engine. The submitted video demonstrates the live GPT‑5.6 Sol journey. Evaluators who
choose to test Sol live may provide a temporary project API key in the password field;
calls are billed to that key’s account, the key remains in session memory, and it is
excluded from all exports.

## YouTube metadata

### Title

NormLab — Experiment Before You Recommend AI Adoption | OpenAI Build Week 2026

### Description

NormLab turns an organizational AI-adoption question into an inspectable experiment.
GPT‑5.6 Sol designs and critiques a typed protocol; a deterministic threshold-agent
engine compares equal-budget interventions; local guardrails verify the evidence and
separate results, assumptions, limitations, and next data.

Built with Codex and GPT‑5.6 Sol for OpenAI Build Week 2026.

Live demo: https://normlab-build-week-2026.streamlit.app/
Source: https://github.com/PaulBufort/NormLab

All simulation outputs are synthetic, uncalibrated, and not forecasts of real
organizational adoption.

### Suggested thumbnail text

EXPERIMENT BEFORE YOU RECOMMEND

Small subtitle: AI adoption under inspectable assumptions
