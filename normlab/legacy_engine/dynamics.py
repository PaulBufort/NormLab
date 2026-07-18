"""Complex-contagion engine: fractional thresholds + ready/willing/able gating.

The model (decisions D1–D8, defaults in core/defaults.py):

- Each agent i has threshold theta_i ~ mixture( P(p_innovator): 0,
  else Beta(mean=theta_mean+role_offset, concentration=kappa) )         (D1, D2)
- exposure share_i(t) = (sum of credibility weights of adopted contacts,
  each scaled by the source's visibility v_j (D17)
  [+ w_comms while a broadcast runs — comms is fully visible by nature]) /
  (total credible contact weight [+ w_comms while a broadcast runs])    (D3, D8, D17)
- ready_i(t)   = share_i(t) > 0  AND  share_i(t) >= theta_i             (D4)
- willing_i    ~ Bernoulli(p_willing[role]) drawn once at t=0           (D5)
- able_i       ~ Bernoulli(able_rate[department]) drawn once at t=0     (D6)
- adoption: not-yet-adopter with ready & willing & able adopts.
  Synchronous updates. Optional relapse: an adopter whose current share
  < retention_factor * theta_i relapses with prob relapse_prob per step (D7).
- Seeds adopt unconditionally at t=0 (pilot groups are given access); they
  remain subject to relapse like everyone else (D9).

Every non-adoption is attributable to exactly one missing condition, which is
what makes the diagnostic maps legible (spec §2.2).

Stack policy: numpy + stdlib only.
"""

from __future__ import annotations

import dataclasses

import numpy as np

from . import defaults
from .orggen import CompiledOrg, _segment_sum
from .seeding import Seeding

ATTR_ADOPTED, ATTR_NOT_ABLE, ATTR_NOT_WILLING, ATTR_NOT_READY, ATTR_RELAPSED = range(5)
ATTRIBUTION_LABELS = {
    ATTR_ADOPTED: "adopted",
    ATTR_NOT_ABLE: "not_able",
    ATTR_NOT_WILLING: "not_willing",
    ATTR_NOT_READY: "not_ready",
    ATTR_RELAPSED: "relapsed",
}


@dataclasses.dataclass
class SimParams:
    """Dynamics parameters. Defaults trace to docs/decisions.md via core/defaults.py.

    Regime note: the default theta_concentration (κ=20) matches the ratified
    headline regime (D1 amendment, 2026-06-10), so out-of-the-box behavior
    matches the published figures. D1 is dual-regime — κ=12 is the documented
    "lottery" companion and κ=8 the original neutral sensitivity value. For full
    published scenarios, prefer building params from the scenario file:
    ``build_sim_params(load_scenario("experiments/scenarios/headline.toml"))``."""

    theta_mean: float = defaults.AGENTS["theta_mean"]
    theta_concentration: float = defaults.AGENTS["theta_concentration"]
    theta_role_offsets: tuple = tuple(defaults.AGENTS["theta_role_offsets"])
    p_innovator: float = defaults.AGENTS["p_innovator"]
    p_willing: tuple = tuple(defaults.AGENTS["p_willing"])
    able_rates: float | dict = defaults.AGENTS["able_rate_default"]
    visibility: float = defaults.AGENTS["visibility"]
    w_comms: float = defaults.WEIGHTS["comms"]
    broadcast_steps: int = defaults.DYNAMICS["broadcast_steps"]
    retention_factor: float = defaults.DYNAMICS["retention_factor"]
    relapse_prob: float = defaults.DYNAMICS["relapse_prob"]
    max_steps: int = defaults.DYNAMICS["max_steps"]
    record_team_curves: bool = False

    def validate(self) -> None:
        if not 0.01 <= self.theta_mean <= 0.99:
            raise ValueError("theta_mean must be in [0.01, 0.99]")
        if self.theta_concentration <= 0:
            raise ValueError("theta_concentration must be positive")
        for name in ("p_innovator", "relapse_prob", "visibility"):
            v = getattr(self, name)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.max_steps < 1:
            raise ValueError("max_steps must be >= 1")


@dataclasses.dataclass
class RunResult:
    """One simulation run. ``curve`` always has length max_steps + 1 (padded with
    the fixed-point value after convergence) so replicates stack cleanly."""

    curve: np.ndarray            # adopted fraction among active agents, t = 0..max
    team_final: np.ndarray       # final adoption rate per team
    adopted: np.ndarray          # bool, final
    ever_adopted: np.ndarray     # bool
    attribution_code: np.ndarray  # int8, ATTR_* per agent (active agents)
    theta: np.ndarray
    willing: np.ndarray
    able: np.ndarray
    steps_to_fixed_point: int    # = max_steps when not converged
    converged: bool
    team_curves: np.ndarray | None = None

    @property
    def final_rate(self) -> float:
        return float(self.curve[-1])

    @property
    def peak_rate(self) -> float:
        return float(self.curve.max())

    def attribution_counts(self) -> dict:
        codes, counts = np.unique(self.attribution_code, return_counts=True)
        out = {label: 0 for label in ATTRIBUTION_LABELS.values()}
        for c, k in zip(codes, counts):
            if c >= 0:  # -1 marks inactive (knocked-out) agents
                out[ATTRIBUTION_LABELS[int(c)]] = int(k)
        return out


def draw_agents(
    compiled: CompiledOrg, params: SimParams, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Draw (theta, willing, able). Separate from the loop so tests and the demo
    can inspect or override the draws. RNG call order is fixed for reproducibility."""
    n, role = compiled.n, compiled.role
    offsets = np.asarray(params.theta_role_offsets, dtype=np.float64)
    mu = np.clip(params.theta_mean + offsets[role], 0.01, 0.99)
    kappa = params.theta_concentration
    theta = rng.beta(mu * kappa, (1.0 - mu) * kappa, size=n)
    theta[rng.random(n) < params.p_innovator] = 0.0  # innovator atom (D2)
    p_willing = np.asarray(params.p_willing, dtype=np.float64)[role]
    willing = rng.random(n) < p_willing
    if isinstance(params.able_rates, dict):
        rate = np.full(n, defaults.AGENTS["able_rate_default"])
        for d, r in params.able_rates.items():
            rate[compiled.dept == int(d)] = float(r)
    else:
        rate = np.full(n, float(params.able_rates))
    able = rng.random(n) < rate
    return theta, willing, able


def run_simulation(
    compiled: CompiledOrg,
    params: SimParams,
    seeding: Seeding,
    rng: np.random.Generator | int = 0,
    agents: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None,
    visibility: np.ndarray | None = None,
) -> RunResult:
    """Run one synchronous-update simulation to fixed point or max_steps.

    ``visibility`` optionally overrides the global ``params.visibility`` with a
    per-agent array (D17): agent j's adoption contributes v_j * w_ij to neighbor
    exposure. Used by the "observable pilots" intervention (seeds at v=1.0 while
    the rest of the world sits lower)."""
    params.validate()
    rng = np.random.default_rng(rng) if not isinstance(rng, np.random.Generator) else rng
    n = compiled.n
    active = compiled.active
    theta, willing, able = agents if agents is not None else draw_agents(compiled, params, rng)
    if visibility is None:
        vis = np.full(n, float(params.visibility))
    else:
        vis = np.asarray(visibility, dtype=np.float64)
        if vis.shape != (n,):
            raise ValueError(f"visibility array must have shape ({n},)")
        if vis.min() < 0.0 or vis.max() > 1.0:
            raise ValueError("visibility values must be in [0, 1]")

    adopted = np.zeros(n, dtype=bool)
    if seeding.initial_adopters.size:
        if not active[seeding.initial_adopters].all():
            raise ValueError("cannot seed a knocked-out (inactive) agent")
        adopted[seeding.initial_adopters] = True  # seeds adopt unconditionally (D9)
    ever = adopted.copy()

    n_active = int(active.sum())
    if n_active == 0:
        raise ValueError("no active agents")
    n_teams = compiled.n_teams
    T = params.max_steps
    curve = np.empty(T + 1)
    curve[0] = adopted[active].mean()
    team_curves = np.zeros((T + 1, n_teams)) if params.record_team_curves else None
    if team_curves is not None:
        team_curves[0] = _team_rates(adopted, compiled, n_teams)

    indptr, indices, weights = compiled.indptr, compiled.indices, compiled.weights
    total_w = compiled.total_weight
    rho, r = params.relapse_prob, params.retention_factor
    steps_done, converged = T, False

    for t in range(1, T + 1):
        # D17: contact j contributes v_j * w_ij once adopted (comms term exempt:
        # a broadcast is fully visible by nature).
        adopted_w = _segment_sum(weights * (adopted * vis)[indices], indptr)
        bc = params.w_comms if (seeding.broadcast and t <= params.broadcast_steps) else 0.0
        denom = total_w + bc
        with np.errstate(invalid="ignore", divide="ignore"):
            share = np.where(denom > 0, (adopted_w + bc) / denom, 0.0)
        ready = (share > 0.0) & (share >= theta - 1e-12)            # D4
        new = ready & willing & able & ~adopted & active
        if rho > 0.0:
            unreinforced = adopted & (share < r * theta)            # D7 hysteresis
            relapsing = unreinforced & (rng.random(n) < rho)
        else:
            unreinforced = None
            relapsing = False
        adopted = (adopted | new) & ~np.asarray(relapsing)
        ever |= adopted
        curve[t] = adopted[active].mean()
        if team_curves is not None:
            team_curves[t] = _team_rates(adopted, compiled, n_teams)
        # Fixed point: nothing changed and nothing *can* change stochastically.
        if not new.any() and (rho == 0.0 or not unreinforced.any()):
            steps_done, converged = t, True
            curve[t:] = curve[t]
            if team_curves is not None:
                team_curves[t:] = team_curves[t]
            break

    attribution = np.full(n, -1, dtype=np.int8)
    attribution[active] = ATTR_NOT_READY
    attribution[active & ~able] = ATTR_NOT_ABLE
    attribution[active & able & ~willing] = ATTR_NOT_WILLING
    attribution[active & able & willing & ever & ~adopted] = ATTR_RELAPSED
    attribution[adopted & active] = ATTR_ADOPTED

    return RunResult(
        curve=curve,
        team_final=_team_rates(adopted, compiled, n_teams),
        adopted=adopted,
        ever_adopted=ever,
        attribution_code=attribution,
        theta=theta,
        willing=willing,
        able=able,
        steps_to_fixed_point=steps_done,
        converged=converged,
        team_curves=team_curves,
    )


def _team_rates(adopted: np.ndarray, compiled: CompiledOrg, n_teams: int) -> np.ndarray:
    """Final adoption rate per team, among active members."""
    sums = np.bincount(compiled.team, weights=(adopted & compiled.active), minlength=n_teams)
    sizes = np.bincount(compiled.team, weights=compiled.active.astype(float), minlength=n_teams)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(sizes > 0, sums / sizes, 0.0)
