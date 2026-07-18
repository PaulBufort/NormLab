"""Output metrics (spec §2.3): plateau/relapse, unit maps, dead pockets, pivot nodes.

Definitions are decisions D11 (dead pockets) and D12 (pivot nodes).
Stack policy: networkx + numpy + stdlib only.
"""

from __future__ import annotations

import dataclasses

import networkx as nx
import numpy as np

from . import defaults
from .dynamics import RunResult, SimParams, run_simulation
from .orggen import CompiledOrg, OrgGraph


# --- Curve summaries ---------------------------------------------------------

def plateau(curve: np.ndarray, tail: int = defaults.ANALYSIS["plateau_tail_steps"]) -> float:
    """Mean adoption over the last ``tail`` steps (the settled level)."""
    return float(np.mean(curve[-tail:]))


def relapse_magnitude(curve: np.ndarray, tail: int = defaults.ANALYSIS["plateau_tail_steps"]) -> float:
    """Peak minus plateau: the 'spike then relapse' size (0 without decay)."""
    return float(curve.max() - plateau(curve, tail))


def time_to_level(curve: np.ndarray, level: float) -> int | None:
    """First step at which adoption reaches ``level`` (None if never)."""
    hits = np.flatnonzero(curve >= level)
    return int(hits[0]) if hits.size else None


# --- Unit-level maps (D11) ----------------------------------------------------

def dept_rates(result: RunResult, compiled: CompiledOrg) -> dict[int, float]:
    """Final adoption rate per department (among active agents; CEO dept -1 excluded)."""
    out = {}
    for d in sorted(set(compiled.dept.tolist())):
        if d < 0:
            continue
        mask = (compiled.dept == d) & compiled.active
        if mask.sum():
            out[int(d)] = float(result.adopted[mask].mean())
    return out


def dead_pockets(
    unit_rates: dict[int, float] | np.ndarray,
    cutoff: float = defaults.ANALYSIS["dead_pocket_cutoff"],
) -> list[int]:
    """Units below critical mass: final adoption < cutoff (D11, default 0.25)."""
    if isinstance(unit_rates, dict):
        return sorted(u for u, r in unit_rates.items() if r < cutoff)
    return np.flatnonzero(np.asarray(unit_rates) < cutoff).tolist()


def attribution_by_unit(result: RunResult, compiled: CompiledOrg, level: str = "dept") -> dict:
    """Why people did not adopt, per unit: counts of each attribution category.

    The legibility payoff of the R/W/A decomposition (spec §2.2)."""
    from .dynamics import ATTRIBUTION_LABELS

    ids = compiled.dept if level == "dept" else compiled.team
    out: dict[int, dict[str, int]] = {}
    for u in sorted(set(ids[compiled.active].tolist())):
        mask = (ids == u) & compiled.active
        codes, counts = np.unique(result.attribution_code[mask], return_counts=True)
        out[int(u)] = {ATTRIBUTION_LABELS[int(c)]: int(k) for c, k in zip(codes, counts) if c >= 0}
    return out


# --- Pivot nodes (D12) ---------------------------------------------------------

def betweenness_candidates(org: OrgGraph, top_m: int = defaults.ANALYSIS["pivot_candidates"],
                           rng_seed: int = 0) -> list[int]:
    """Top-m informal-layer betweenness nodes: the knockout screening set (D12).

    Exact betweenness up to 2,000 nodes, k-sample approximation beyond."""
    g = org.informal
    if g.number_of_nodes() <= 2000:
        bc = nx.betweenness_centrality(g)
    else:
        bc = nx.betweenness_centrality(g, k=200, seed=rng_seed)
    return [int(n) for n, _ in sorted(bc.items(), key=lambda kv: -kv[1])[:top_m]]


@dataclasses.dataclass
class PivotReport:
    node: int
    delta_plateau: float       # baseline mean plateau - knockout mean plateau
    baseline: float
    knockout: float
    is_pivot: bool


def pivot_nodes(
    compiled: CompiledOrg,
    params: SimParams,
    seeding_factory,
    candidates: list[int],
    reps: int = 5,
    rng_seed: int = 0,
    delta_threshold: float = defaults.ANALYSIS["pivot_delta_pp"],
    agents: tuple | None = None,
) -> list[PivotReport]:
    """Counterfactual knockouts (D12): re-run the simulation without each candidate
    and report the plateau shift. seeding_factory(compiled, rng) -> Seeding must
    draw seeds among *active* agents only (all built-in strategies do).

    Pass ``agents`` (theta, willing, able from dynamics.draw_agents) to evaluate
    pivots for one *fixed* workforce — the diagnostic-map semantics: "in this
    organization, with these people, whose departure changes the outcome?"
    Without it, deltas average over re-drawn workforces and individual relay
    effects wash out into replicate noise (measured 2026-06-10).
    """
    def mean_plateau(c: CompiledOrg) -> float:
        vals = []
        for rep in range(reps):
            rng = np.random.default_rng((rng_seed, rep))
            seeding = seeding_factory(c, rng)
            res = run_simulation(c, params, seeding, rng=rng, agents=agents)
            vals.append(plateau(res.curve))
        return float(np.mean(vals))

    base = mean_plateau(compiled)
    reports = []
    for v in candidates:
        ko = mean_plateau(compiled.without_node(int(v)))
        delta = base - ko
        reports.append(PivotReport(int(v), delta, base, ko, delta > delta_threshold))
    reports.sort(key=lambda r: -r.delta_plateau)
    return reports
