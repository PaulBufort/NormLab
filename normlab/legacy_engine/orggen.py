"""Synthetic organization generator: two deliberately distinct layers.

- Formal layer: the org chart (a tree: CEO - department heads - team managers - ICs).
  Broadcast messages and role definitions live here.
- Informal layer: the influence network adoption actually travels on
  (team proximity + department proximity + tenure homophily + noise + connectors).

The divergence between the layers is the core demonstrative device (spec §2.1).
Modeling choices: docs/decisions.md D3 (edge credibility weights), D10 (generator
structure), D13 (tenure shapes ties only, never behavior).

Stack policy: this module imports networkx, numpy, stdlib only.
"""

from __future__ import annotations

import dataclasses

import networkx as nx
import numpy as np

from . import defaults

LEADERSHIP_TEAM = 0  # team id of the CEO + department heads group


@dataclasses.dataclass
class CompiledOrg:
    """Engine-ready arrays (CSR adjacency of the informal layer + node attributes).

    ``weights`` holds the credibility weight of each contact edge (D3). ``active``
    supports counterfactual node knockouts (D12): inactive nodes cannot adopt,
    expose nobody, and are excluded from metrics.
    """

    n: int
    indptr: np.ndarray      # int64, shape (n+1,)
    indices: np.ndarray     # int32, shape (2m,)
    weights: np.ndarray     # float64, shape (2m,)
    total_weight: np.ndarray  # float64, shape (n,): denominator of the exposure share
    team: np.ndarray        # int32
    dept: np.ndarray        # int32 (-1 for the CEO)
    role: np.ndarray        # int8: 0 ic, 1 manager, 2 leadership
    tenure: np.ndarray      # float64, years
    active: np.ndarray      # bool
    meta: dict

    @property
    def n_teams(self) -> int:
        return int(self.team.max()) + 1

    def team_members(self, t: int) -> np.ndarray:
        return np.flatnonzero(self.team == t)

    def degrees(self) -> np.ndarray:
        return np.diff(self.indptr)

    def without_node(self, v: int) -> "CompiledOrg":
        """Counterfactual copy with node v removed from the network (D12)."""
        weights = self.weights.copy()
        weights[self.indices == v] = 0.0
        weights[self.indptr[v]:self.indptr[v + 1]] = 0.0
        active = self.active.copy()
        active[v] = False
        total = _segment_sum(weights, self.indptr)
        return dataclasses.replace(
            self, weights=weights, total_weight=total, active=active
        )


@dataclasses.dataclass
class OrgGraph:
    """A generated (or ingested) organization: two NetworkX layers + parameters."""

    formal: nx.Graph
    informal: nx.Graph
    params: dict

    @property
    def n(self) -> int:
        return self.informal.number_of_nodes()

    def compile(self) -> CompiledOrg:
        """Flatten the informal layer to CSR numpy arrays for the simulation loop."""
        g = self.informal
        n = g.number_of_nodes()
        if n == 0:
            raise ValueError("empty organization")
        # Both directions of every undirected edge, sorted by source.
        m = g.number_of_edges()
        src = np.empty(2 * m, dtype=np.int64)
        dst = np.empty(2 * m, dtype=np.int64)
        w = np.empty(2 * m, dtype=np.float64)
        for k, (u, v, weight) in enumerate(g.edges(data="weight", default=1.0)):
            src[2 * k], dst[2 * k], w[2 * k] = u, v, weight
            src[2 * k + 1], dst[2 * k + 1], w[2 * k + 1] = v, u, weight
        order = np.argsort(src, kind="stable")
        src, dst, w = src[order], dst[order], w[order]
        indptr = np.searchsorted(src, np.arange(n + 1)).astype(np.int64)
        attrs = {a: nx.get_node_attributes(g, a) for a in ("team", "dept", "role", "tenure")}
        nodes = range(n)
        return CompiledOrg(
            n=n,
            indptr=indptr,
            indices=dst.astype(np.int32),
            weights=w,
            total_weight=_segment_sum(w, indptr),
            team=np.array([attrs["team"][i] for i in nodes], dtype=np.int32),
            dept=np.array([attrs["dept"][i] for i in nodes], dtype=np.int32),
            role=np.array([attrs["role"][i] for i in nodes], dtype=np.int8),
            tenure=np.array([attrs["tenure"][i] for i in nodes], dtype=np.float64),
            active=np.ones(n, dtype=bool),
            meta=dict(self.params),
        )


def _segment_sum(values: np.ndarray, indptr: np.ndarray) -> np.ndarray:
    """Per-node sums over CSR segments via cumsum diff (safe for empty segments,
    unlike np.add.reduceat)."""
    c = np.concatenate(([0.0], np.cumsum(values)))
    return c[indptr[1:]] - c[indptr[:-1]]


def generate_org(
    n_agents: int = defaults.ORG["n_agents"],
    n_departments: int = defaults.ORG["n_departments"],
    mean_team_size: int = defaults.ORG["mean_team_size"],
    silo_strength: float = defaults.ORG["silo_strength"],
    seed: int | np.random.Generator = 0,
    *,
    p_team: float = defaults.ORG["p_team"],
    dept_degree: float = defaults.ORG["dept_degree"],
    team_locality: float = defaults.ORG["team_locality"],
    cross_dept_degree_max: float = defaults.ORG["cross_dept_degree_max"],
    noise_degree: float = defaults.ORG["noise_degree"],
    connector_fraction: float = defaults.ORG["connector_fraction"],
    connector_extra_degree: int = defaults.ORG["connector_extra_degree"],
    tenure_homophily: float = defaults.ORG["tenure_homophily"],
    tenure_mean_years: float = defaults.ORG["tenure_mean_years"],
    weights: dict | None = None,
    sister_close: bool = True,
) -> OrgGraph:
    """Generate a two-layer synthetic organization (D10).

    silo_strength s in [0, 1] is the headline structural knob: expected cross-
    department informal degree is cross_dept_degree_max * (1 - s). At s = 1
    departments are near-hermetic (only ``noise_degree`` random ties leak).
    """
    if not 200 <= n_agents <= 20_000:
        raise ValueError("n_agents must be in [200, 20000] (spec §2.1)")
    if not 0.0 <= silo_strength <= 1.0:
        raise ValueError("silo_strength must be in [0, 1]")
    if not 0.0 <= team_locality <= 0.95:
        raise ValueError("team_locality must be in [0, 0.95]")
    if n_departments < 2:
        raise ValueError("need at least 2 departments to speak of silos")
    rng = np.random.default_rng(seed)
    wts = dict(defaults.WEIGHTS, **(weights or {}))

    # --- Structure: CEO(0), dept heads (1..D), then line teams -------------
    n_leadership = 1 + n_departments
    n_line = n_agents - n_leadership
    n_teams_line = max(n_departments, int(round(n_line / mean_team_size)))
    sizes = _team_sizes(n_line, n_teams_line, rng)  # each >= 3 (manager + 2 ICs)

    team = np.empty(n_agents, dtype=np.int32)
    dept = np.empty(n_agents, dtype=np.int32)
    role = np.full(n_agents, defaults.ROLE_IC, dtype=np.int8)
    team[0], dept[0], role[0] = LEADERSHIP_TEAM, -1, defaults.ROLE_LEADERSHIP
    heads = np.arange(1, 1 + n_departments)
    team[heads] = LEADERSHIP_TEAM
    dept[heads] = np.arange(n_departments)
    role[heads] = defaults.ROLE_LEADERSHIP

    formal_edges: list[tuple[int, int]] = [(0, int(h)) for h in heads]
    informal: list[tuple[int, int, float, str]] = [
        (0, int(h), wts["manager_report"], "manager") for h in heads
    ]

    managers: list[int] = []
    nxt = n_leadership
    team_dept = np.array([t % n_departments for t in range(n_teams_line)])
    team_members: dict[int, list[int]] = {}
    for t, size in enumerate(sizes):
        tid = t + 1  # team 0 is leadership
        members = list(range(nxt, nxt + size))
        nxt += size
        team[members] = tid
        dept[members] = team_dept[t]
        mgr = members[0]
        role[mgr] = defaults.ROLE_MANAGER
        managers.append(mgr)
        team_members[tid] = members
        head = 1 + team_dept[t]
        formal_edges.append((int(head), mgr))
        informal.append((int(head), mgr, wts["manager_report"], "manager"))
        for ic in members[1:]:
            formal_edges.append((mgr, ic))
            informal.append((mgr, ic, wts["manager_report"], "manager"))

    tenure = np.clip(rng.gamma(2.0, tenure_mean_years / 2.0, n_agents), 0.1, 40.0)

    # --- Informal layer ------------------------------------------------------
    existing: set[int] = set()

    def key(u: int, v: int) -> int:
        a, b = (u, v) if u < v else (v, u)
        return a * n_agents + b

    for u, v, _, _ in informal:
        existing.add(key(u, v))

    # 1. Within-team peer ties (dense cliques among ICs and manager included
    #    only via the manager edges above; D3 gives the dyad its manager weight).
    for tid, members in team_members.items():
        ics = members[1:]
        for i in range(len(ics)):
            for j in range(i + 1, len(ics)):
                if rng.random() < p_team:
                    u, v = ics[i], ics[j]
                    existing.add(key(u, v))
                    informal.append((u, v, wts["peer_close"], "team"))

    def add_pair_batch(quota, sampler, constraint, homophily, kind, weight_fn=None):
        """Sample non-duplicate informal ties in vectorized batches.

        weight_fn(u, v) -> credibility weight; defaults to the flat far-peer
        weight. Dept ties grade by ring distance (D3 closeness amendment)."""
        added = 0
        attempts = 0
        while added < quota and attempts < 40:
            attempts += 1
            u, v = sampler(max(64, 2 * (quota - added)))
            ok = (u != v) & constraint(u, v)
            if homophily > 0:
                gap = np.abs(tenure[u] - tenure[v]) / tenure_mean_years
                ok &= rng.random(u.size) < np.exp(-homophily * gap)
            for uu, vv in zip(u[ok], v[ok]):
                if added >= quota:
                    break
                k = key(int(uu), int(vv))
                if k in existing:
                    continue
                existing.add(k)
                w = wts["peer_far"] if weight_fn is None else weight_fn(int(uu), int(vv))
                informal.append((int(uu), int(vv), w, kind))
                added += 1
        return added

    # 2. Within-department, cross-team ties (proximity + tenure homophily).
    #    Partner team chosen at ring distance d ~ Geometric(team_locality): high
    #    locality concentrates ties on adjacent "sister teams" — wide bridges;
    #    locality -> 0 recovers uniform mixing — narrow bridges (D15).
    for d in range(n_departments):
        teams_d = [t + 1 for t in range(n_teams_line) if team_dept[t] == d]
        if len(teams_d) < 2:
            continue
        members_d = np.flatnonzero((dept == d) & (team != LEADERSHIP_TEAM))
        quota = int(round(dept_degree * members_d.size / 2))
        ring_pos = {tid: i for i, tid in enumerate(teams_d)}
        T_d = len(teams_d)
        members_of = {tid: [m for m in team_members[tid]] for tid in teams_d}

        def dept_sampler(b, md=members_d, rp=ring_pos, td=teams_d, T=T_d, mo=members_of):
            u = rng.choice(md, b)
            if team_locality > 0.0:
                dist = (rng.geometric(team_locality, b) - 1) % (T - 1) + 1
            else:
                dist = rng.integers(1, T, b)
            side = rng.choice((-1, 1), b)
            pos = np.array([rp[t] for t in team[u]])
            partner = (pos + side * dist) % T
            v = np.array([mo[td[p]][rng.integers(len(mo[td[p]]))] for p in partner])
            return u, v

        def dept_weight(uu, vv, rp=ring_pos, T=T_d):
            dr = abs(rp[int(team[uu])] - rp[int(team[vv])])
            dr = min(dr, T - dr)
            return wts["peer_close"] if (dr == 1 and sister_close) else wts["peer_far"]

        add_pair_batch(
            quota,
            dept_sampler,
            lambda u, v: team[u] != team[v],
            tenure_homophily,
            "dept",
            weight_fn=dept_weight,
        )

    # 3. Cross-department ties — the silo permeability knob (D10).
    cross_quota = int(round(cross_dept_degree_max * (1 - silo_strength) * n_agents / 2))
    add_pair_batch(
        cross_quota,
        lambda b: (rng.integers(0, n_agents, b), rng.integers(0, n_agents, b)),
        lambda u, v: dept[u] != dept[v],
        tenure_homophily,
        "cross",
    )

    # 4. Uniform noise ties (constant small leak; same-team duplicates skipped).
    add_pair_batch(
        int(round(noise_degree * n_agents / 2)),
        lambda b: (rng.integers(0, n_agents, b), rng.integers(0, n_agents, b)),
        lambda u, v: np.ones(u.size, dtype=bool),
        0.0,
        "noise",
    )

    # 5. Connectors: tenure-biased agents with extra bridging ties; partner is
    #    cross-department with prob (1 - s), else cross-team within department,
    #    so silo_strength keeps strict control of department isolation.
    n_connectors = int(round(connector_fraction * n_agents))
    if n_connectors:
        p = tenure / tenure.sum()
        connectors = rng.choice(n_agents, n_connectors, replace=False, p=p)
        for c in connectors:
            c = int(c)
            for _ in range(connector_extra_degree):
                go_cross = rng.random() < (1 - silo_strength) and n_departments > 1
                pool = (
                    np.flatnonzero(dept != dept[c])
                    if go_cross
                    else np.flatnonzero((dept == dept[c]) & (team != team[c]))
                )
                if pool.size == 0:
                    continue
                v = int(rng.choice(pool))
                k = key(c, v)
                if k not in existing:
                    existing.add(k)
                    informal.append((c, v, wts["peer_far"], "connector"))

    # --- Assemble NetworkX layers -------------------------------------------
    node_attrs = {
        i: {
            "team": int(team[i]),
            "dept": int(dept[i]),
            "role": int(role[i]),
            "tenure": float(tenure[i]),
        }
        for i in range(n_agents)
    }
    formal = nx.Graph()
    formal.add_nodes_from(node_attrs.items())
    formal.add_edges_from(formal_edges)
    informal_g = nx.Graph()
    informal_g.add_nodes_from(node_attrs.items())
    informal_g.add_edges_from(
        (u, v, {"weight": w, "kind": kind}) for u, v, w, kind in informal
    )

    params = {
        "kind": "synthetic",
        "n_agents": n_agents,
        "n_departments": n_departments,
        "mean_team_size": mean_team_size,
        "silo_strength": silo_strength,
        "p_team": p_team,
        "dept_degree": dept_degree,
        "team_locality": team_locality,
        "cross_dept_degree_max": cross_dept_degree_max,
        "noise_degree": noise_degree,
        "connector_fraction": connector_fraction,
        "connector_extra_degree": connector_extra_degree,
        "tenure_homophily": tenure_homophily,
        "tenure_mean_years": tenure_mean_years,
        "weights": wts,
    }
    return OrgGraph(formal=formal, informal=informal_g, params=params)


def _team_sizes(total: int, n_teams: int, rng: np.random.Generator) -> list[int]:
    """Split ``total`` agents into ``n_teams`` teams of size >= 3, mean ~ total/n_teams."""
    if total < 3 * n_teams:
        n_teams = max(1, total // 3)
    sizes = np.maximum(3, rng.poisson(max(total / n_teams - 3, 0), n_teams) + 3)
    # Repair the sum while respecting the minimum size of 3.
    diff = total - int(sizes.sum())
    i = 0
    while diff != 0:
        j = i % n_teams
        if diff > 0:
            sizes[j] += 1
            diff -= 1
        elif sizes[j] > 3:
            sizes[j] -= 1
            diff += 1
        i += 1
    return [int(s) for s in sizes]
