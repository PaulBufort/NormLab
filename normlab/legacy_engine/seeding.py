"""Seeding strategies (decision D9).

All seeded strategies receive exactly the same budget: floor(budget * n_active)
agents set to adopted (and given access) at t = 0. Broadcast seeds nobody — it
buys one step of universal awareness through the low-credibility comms channel
(D8) and serves as the reference floor in comparisons.

Stack policy: numpy + stdlib only.
"""

from __future__ import annotations

import dataclasses

import numpy as np

from . import defaults
from .orggen import CompiledOrg, LEADERSHIP_TEAM

STRATEGIES = {
    "broadcast": "everyone exposed once via central comms; zero seeded adopters",
    "random": "budget spent on uniformly random agents",
    "champions": "budget spent on the most-connected agents (informal degree)",
    "cluster": "budget spent filling whole line teams, one team at a time",
    "line_manager_first": "budget spent on randomly chosen line managers",
}


@dataclasses.dataclass
class Seeding:
    strategy: str
    initial_adopters: np.ndarray  # int64 node ids, sorted
    broadcast: bool
    meta: dict


def make_seeding(
    strategy: str,
    compiled: CompiledOrg,
    budget: float = defaults.SEEDING["budget"],
    rng: np.random.Generator | int = 0,
    scores: np.ndarray | None = None,
) -> Seeding:
    """Build the t=0 seed set for one strategy.

    ``scores`` optionally replaces informal degree as the champions ranking
    (e.g. betweenness computed by the caller), per D9's metric flag.
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}; choose from {sorted(STRATEGIES)}")
    if not 0.0 <= budget <= 0.5:
        raise ValueError("seed budget must be in [0, 0.5]")
    rng = np.random.default_rng(rng) if not isinstance(rng, np.random.Generator) else rng
    active_ids = np.flatnonzero(compiled.active)
    k = int(np.floor(budget * active_ids.size))

    if strategy == "broadcast":
        return Seeding("broadcast", np.empty(0, dtype=np.int64), True, {"k": 0})
    if k == 0:
        raise ValueError(
            f"budget {budget} yields 0 seeds for n_active={active_ids.size}; "
            "increase the budget or population"
        )

    if strategy == "random":
        seeds = rng.choice(active_ids, size=k, replace=False)
        meta = {}

    elif strategy == "champions":
        s = scores if scores is not None else compiled.degrees().astype(np.float64)
        s = s[active_ids]
        # Highest score first; random tie-break so replicates differ honestly.
        order = np.lexsort((rng.random(s.size), -s))
        seeds = active_ids[order[:k]]
        meta = {"metric": "custom" if scores is not None else "degree"}

    elif strategy == "cluster":
        team_ids = [t for t in range(compiled.n_teams) if t != LEADERSHIP_TEAM]
        rng.shuffle(team_ids)
        chosen: list[int] = []
        teams_used = []
        for t in team_ids:
            members = np.flatnonzero((compiled.team == t) & compiled.active)
            if members.size == 0:
                continue
            if len(chosen) + members.size <= k:
                chosen.extend(int(m) for m in members)
                teams_used.append(t)
            else:
                part = rng.permutation(members)[: k - len(chosen)]
                chosen.extend(int(m) for m in part)
                teams_used.append(t)
            if len(chosen) >= k:
                break
        seeds = np.array(chosen, dtype=np.int64)
        meta = {"teams_seeded": teams_used}

    elif strategy == "line_manager_first":
        managers = np.flatnonzero((compiled.role == defaults.ROLE_MANAGER) & compiled.active)
        if managers.size == 0:
            raise ValueError(
                "line_manager_first needs role data; imported real graphs have none "
                "(see core/ingest.py docstring)"
            )
        if k <= managers.size:
            seeds = rng.choice(managers, size=k, replace=False)
            meta = {"topped_up_with_random": 0}
        else:
            others = np.setdiff1d(active_ids, managers)
            extra = rng.choice(others, size=k - managers.size, replace=False)
            seeds = np.concatenate([managers, extra])
            meta = {"topped_up_with_random": int(k - managers.size)}

    seeds = np.unique(seeds.astype(np.int64))
    assert seeds.size == k, f"budget violated: {seeds.size} != {k}"
    return Seeding(strategy, seeds, False, {"k": k, **meta})
