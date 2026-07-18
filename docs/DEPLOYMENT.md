# Streamlit deployment and evaluator smoke test

## Current deployment

- URL: `https://normlab-build-week-2026.streamlit.app/`
- repository: `https://github.com/PaulBufort/NormLab`
- branch: `codex/build-week-mvp`
- entry point: `demo/app.py`
- first deployed commit: `b142bd2`
- public offline smoke test: passed on July 18, 2026
- local live GPT‑5.6 Sol smoke test: passed on July 18, 2026;
- public live GPT‑5.6 Sol smoke test: passed on July 19, 2026 with a temporary
  owner-provided key; the key was never shared with Codex or stored in the repository

## Requirements

- a remote Git repository containing this code and a green test suite;
- `demo/app.py` as the Streamlit entry point;
- dependencies listed in `requirements.txt`;
- no key in Git, its history, or an `.env` file;
- no owner key required in Streamlit Community Cloud secrets.

## Deploy or update

1. In Streamlit Community Cloud, create an app from the NormLab repository.
2. Select branch `codex/build-week-mvp` and entry point `demo/app.py`.
3. Do not configure an owner-funded API key in application secrets. For a live Sol
   test, an evaluator may temporarily supply a project key billed to its own account.
4. Deploy, wait for a clean start, then record the URL, commit, date, and smoke-test
   result in `BUILD_WEEK.md`.

An URL is “accessible to evaluators” only after testing it without repository or
Streamlit authentication.

## Evaluator smoke-test checklist

- the page loads and immediately displays “Not a forecast”;
- after a temporary key is entered, the badge confirms “GPT‑5.6 Sol active”;
- a free-text question produces an inspectable protocol and critique;
- tabs distinguish `provided`, `inferred`, and `system_default` values;
- execution starts only after explicit human approval;
- the main table contains four strategies with identical pilot counts;
- `broadcast` appears outside the ranking;
- sensitivity and threshold/visibility non-identifiability are visible;
- the card contains Results, Assumptions, Limitations, and Next data;
- all three JSON exports work and the trace exposes neither keys nor private reasoning;
- the clear button removes the key and session artifacts;
- a second run of the same protocol produces the same `result_id`.

## Rollback behavior

If a live API call fails, the interface must show the error and must not present the
run as complete. The offline fixture remains available for tests and deterministic
demonstration, but it must never be confused with a successful Sol run.
