from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from normlab import ENGINE_SOURCE_COMMIT
from normlab.legacy_engine.dynamics import SimParams, run_simulation
from normlab.legacy_engine.orggen import generate_org
from normlab.legacy_engine.seeding import make_seeding


ROOT = Path(__file__).resolve().parents[1]


def test_legacy_sources_match_frozen_manifest_byte_for_byte():
    manifest = json.loads(
        (ROOT / "docs/provenance/LEGACY_ENGINE.json").read_text(encoding="utf-8")
    )
    assert manifest["source_commit"] == ENGINE_SOURCE_COMMIT
    for item in manifest["files"]:
        actual = hashlib.sha256((ROOT / item["destination"]).read_bytes()).hexdigest()
        assert actual == item["sha256"], item["destination"]


def test_legacy_golden_determinism_and_curve_shape():
    compiled = generate_org(n_agents=200, n_departments=4, seed=11).compile()
    params = SimParams(relapse_prob=0.1, max_steps=20)
    seeding_1 = make_seeding("random", compiled, 0.05, rng=11)
    seeding_2 = make_seeding("random", compiled, 0.05, rng=11)
    run_1 = run_simulation(compiled, params, seeding_1, rng=11)
    run_2 = run_simulation(compiled, params, seeding_2, rng=11)
    np.testing.assert_array_equal(run_1.curve, run_2.curve)
    np.testing.assert_array_equal(run_1.adopted, run_2.adopted)
    assert len(run_1.curve) == 21


def test_legacy_seed_budget_rule_is_preserved():
    compiled = generate_org(n_agents=200, n_departments=4, seed=5).compile()
    for strategy in ("random", "champions", "cluster", "line_manager_first"):
        seeding = make_seeding(strategy, compiled, budget=0.05, rng=1)
        assert seeding.initial_adopters.size == 10
        assert not seeding.broadcast
    broadcast = make_seeding("broadcast", compiled, budget=0.05, rng=1)
    assert broadcast.initial_adopters.size == 0
    assert broadcast.broadcast
