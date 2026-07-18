"""adoption-sim core engine.

Complex contagion (fractional thresholds, ready/willing/able gating) on synthetic
two-layer organizational networks. NetworkX + NumPy + standard library only — a
unit test enforces this (see tests/test_stack_policy.py).

All modeling choices that affect scientific claims are logged in docs/decisions.md
with a D-number; code comments reference those numbers.
"""

__version__ = "0.1.0"

from .orggen import OrgGraph, CompiledOrg, generate_org
from .dynamics import SimParams, RunResult, run_simulation
from .seeding import Seeding, make_seeding, STRATEGIES
