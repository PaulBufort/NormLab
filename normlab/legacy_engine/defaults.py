"""Default model parameters — single source of truth.

Every value here corresponds to a ratified decision in docs/decisions.md
(D-numbers in comments). Change the decision there, then change the value here;
nothing else in the codebase hard-codes these numbers.
"""

# --- Organization generator (D10, D13) -------------------------------------
ORG = {
    "n_agents": 1000,
    "n_departments": 8,
    "mean_team_size": 8,        # manager + ICs
    "silo_strength": 0.8,       # s in [0,1]; 1 = near-hermetic departments
    "p_team": 0.90,             # within-team informal tie probability
    "dept_degree": 3.0,         # expected within-dept, cross-team informal degree
    "team_locality": 0.7,       # D15: ring-distance concentration of dept ties
                                # (geometric p; 0 = uniform mixing, narrow bridges)
    "cross_dept_degree_max": 3.0,  # cross-dept expected degree at silo_strength = 0
    "noise_degree": 0.2,        # expected uniformly-random ties per agent (any pair)
    "connector_fraction": 0.05, # agents given extra cross-unit ties (tenure-biased)
    "connector_extra_degree": 4,
    "tenure_homophily": 1.0,    # weight of |Δtenure| penalty in cross-unit tie choice
    "tenure_mean_years": 6.0,   # gamma(shape=2) -> right-skewed, mean 6
}

# --- Credibility weights (D3, incl. closeness amendment) --------------------
WEIGHTS = {
    "peer_close": 1.0,          # same team OR ring-adjacent sister-team collaborator
    "peer_far": 0.6,            # any other peer tie (distant dept, cross-dept, noise)
    "manager_report": 0.7,
    "comms": 0.3,               # central communications, used by broadcast (D8)
}

# --- Agent states and thresholds (D1, D2, D5, D6) ---------------------------
AGENTS = {
    "theta_mean": 0.30,                 # Beta mean (D1)
    "theta_concentration": 20.0,        # Beta kappa (D1 amendment 2026-06-10):
                                        # aligned to the ratified headline regime
                                        # for least surprise; kappa=8 remains the
                                        # documented sensitivity value
    "theta_role_offsets": [0.0, 0.0, 0.0],  # ic, manager, leadership (D1; neutral)
    "p_innovator": 0.025,               # P(theta = 0) atom (D2)
    "p_willing": [0.85, 0.85, 0.85],    # per role: ic, manager, leadership (D5)
    "able_rate_default": 1.0,           # per-department Bernoulli rate (D6)
    "visibility": 1.0,                  # D17: fraction of an adopted contact's
                                        # adoption that is visible to neighbors
}

# --- Dynamics (D4, D7, D8) ---------------------------------------------------
DYNAMICS = {
    "max_steps": 100,
    "broadcast_steps": 1,       # T_b: steps the comms term stays active (D8)
    "retention_factor": 0.5,    # r: relapse risk when share < r * theta (D7)
    "relapse_prob": 0.0,        # rho: 0 = decay off (headline default, D7)
}

# --- Seeding (D9) ------------------------------------------------------------
SEEDING = {
    "budget": 0.05,             # seed fraction of N for all seeded strategies
    "champion_metric": "degree",
}

# --- Analysis (D11, D12, D14) -------------------------------------------------
ANALYSIS = {
    "dead_pocket_cutoff": 0.25,     # D11
    "plateau_tail_steps": 10,
    "pivot_candidates": 20,         # D12
    "pivot_delta_pp": 0.05,         # D12: pivot if removal shifts plateau > 5 pp
    "replicates": 20,               # D14
}

ROLE_IC, ROLE_MANAGER, ROLE_LEADERSHIP = 0, 1, 2
ROLE_NAMES = {ROLE_IC: "ic", ROLE_MANAGER: "manager", ROLE_LEADERSHIP: "leadership"}
