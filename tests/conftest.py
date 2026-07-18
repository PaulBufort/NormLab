from __future__ import annotations

import pytest

from normlab.protocols import apply_user_overrides, design_offline_protocol
from normlab.runner import run_experiment


QUESTION = (
    "Nous avons 200 personnes dans 4 départements et un budget pilotes de 5 %. "
    "Nous voulons adopter un copilote IA de production entre des équipes en silos."
)


@pytest.fixture(scope="session")
def protocol():
    base = design_offline_protocol(QUESTION).protocol
    return apply_user_overrides(
        base,
        n_agents=200,
        n_departments=4,
        silo_strength=0.8,
        theta_mean=0.3,
        theta_concentration=20.0,
        visibility=1.0,
        seed_budget_fraction=0.05,
        replicates=3,
        master_seed=123,
        strategies=["random", "champions", "cluster", "line_manager_first"],
    )


@pytest.fixture(scope="session")
def result(protocol):
    return run_experiment(protocol)
