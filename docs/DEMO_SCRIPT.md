# NormLab demo video — final script and recording runbook

Target length: **2:42–2:48**. Hard limit: **under 3:00**. Language: English.
Track: **Work and Productivity**.

## Before recording

- Use the public URL: `https://normlab-build-week-2026.streamlit.app/`.
- Use a private browser window at 1920×1080 or 16:9, with notifications disabled.
- Load the temporary API key before recording, confirm the “GPT‑5.6 Sol active” badge,
  then collapse the key section. Never show the key or the OpenAI dashboard.
- Use the default English question and default protocol parameters.
- Record the Sol waiting periods, but remove them with two clean jump cuts.
- Keep the browser zoom between 80% and 90% so four-column results remain legible.
- Do not add copyrighted music. Clear spoken narration is sufficient.

## Timed shot list and voice-over

### 0:00–0:17 — Problem and promise

**Screen:** Hero, default question, active Sol badge, and “Not a forecast” warning.

**Narration:**

> AI-adoption programs often jump directly from a question to a recommendation.
> NormLab inserts an inspectable experiment in between. Here, an organization with
> six hundred people and a five-percent pilot budget asks where its initial AI-copilot
> users should be placed.

### 0:17–0:46 — GPT‑5.6 Sol designs and critiques

**Action:** Click **Design and critique the protocol**. Cut the waiting time. Show the
protocol tabs, then the critique.

**Narration:**

> GPT‑5.6 Sol converts that question into a typed experimental protocol. Every value
> is labeled as provided by the user, inferred by Sol, or supplied by a versioned
> system default, so an assumption cannot silently become a user fact. Sol also
> critiques missing data, budget comparability, sensitivity, and the known
> non-identifiability between adoption thresholds and usage visibility.

### 0:46–1:08 — Human approval and deterministic execution

**Screen:** Parameter editor and four strategies. Briefly point to the 5% budget and
paired replications.

**Action:** Click **Approve and run the experiment**. Cut the waiting time.

**Narration:**

> A human inspects the protocol before execution. The four ranked interventions share
> the same pilot budget and the same paired synthetic organizations and seeds.
> Broadcast uses a different resource unit, so NormLab displays it separately instead
> of forcing a misleading ranking.

### 1:08–1:34 — The engine decides

**Screen:** Base-case metrics, strategy table, chart, and sensitivity table.

**Narration:**

> Sol does not calculate adoption. A deterministic threshold-agent engine runs the
> scenarios. In this run, random seeding leads the base case, but the ranking changes
> under tested parameter settings. That sensitivity is part of the result, not a
> footnote. These are synthetic mechanism tests under assumptions, never forecasts of
> a real rollout.

### 1:34–1:58 — Decision card

**Screen:** The four decision-card columns.

**Narration:**

> Sol may now explain only the engine output. NormLab verifies every numerical
> reference and deterministically restores mandatory warnings if the model omits
> them. The decision card keeps results, assumptions, limitations, and the next data
> to collect visibly separate. The output is therefore not “choose random”; it is a
> conditional result plus a concrete measurement agenda.

### 1:58–2:14 — Auditability

**Screen:** Open **Audit trace for this run**, then point to the three JSON downloads.

**Narration:**

> The audit trace links the approved protocol, engine version and source commit,
> response and tool-call identifiers, raw paired replications, and the final decision
> card. The key and private reasoning are never exported, and OpenAI storage is
> disabled.

### 2:14–2:37 — What Codex built during Build Week

**Screen:** Switch briefly to the GitHub README sections **What is new for Build Week**
and **Roles of Codex and GPT‑5.6 Sol**.

**Narration:**

> Before Build Week, I had a deterministic complex-contagion engine. In the primary
> Codex thread, Codex inspected that frozen baseline in read-only mode, helped me make
> and document five scientific and product decisions, ported the engine with hash
> parity, and built the schemas, guardrails, OpenAI integration, interface, tests, and
> deployment. Live failures—including a truncated structured response and an omitted
> identifiability warning—became explicit, tested safeguards.

### 2:37–2:47 — Close

**Screen:** Return to the decision card or hero.

**Narration:**

> NormLab helps leaders and change teams experiment before they recommend: compute the
> mechanism, expose the assumptions, and identify what to measure next.

## Editing rules

- Aim for 2:48 maximum after cuts; judges are not required to watch beyond 3:00.
- Use only two jump cuts: after protocol design and after experiment execution.
- Do not accelerate the voice-over. Shorten pauses or remove a sentence instead.
- Keep on-screen text readable; avoid rapid scrolling.
- Listen once with the screen hidden: the narration must still explain what was built,
  how Codex was used, and what GPT‑5.6 Sol does.

## Claims to avoid

Never say “NormLab predicts,” “this adoption rate will happen,” “Sol simulated the
employees,” or “the winning strategy is random.” Say “in this synthetic scenario,”
“result under assumptions,” and “the deterministic threshold engine calculated.”
