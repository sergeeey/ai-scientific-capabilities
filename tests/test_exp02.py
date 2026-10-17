"""exp02 checks: rules, recording wrapper, seed disjointness, artifact hashes.

The full exp02 run takes about 3 minutes, so it is not re-run here. Its artifacts are checked
by hash, and the wrapper is checked against exp01 on a single run.
"""

import json
import os
import random

from aisci import exp02, provenance
from aisci.agents import MECHANISMS
from aisci.environment import Oracle
from aisci.hidden_laws import LAWS
from aisci.rules import abstain_select, margin_select
from aisci.run import run_one

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXP02 = os.path.join(ROOT, "results", "exp02")
SRC = os.path.join(ROOT, "src", "aisci")


def test_calibration_and_test_seeds_are_disjoint():
    assert not set(exp02.CAL_SEEDS) & set(exp02.TEST_SEEDS)


def test_rules_module_does_not_import_hidden_or_runner_modules():
    import ast

    with open(os.path.join(SRC, "rules.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[-1] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[-1])
    assert not mods & {"hidden_laws", "checker", "run", "exp02"}


def test_margin_select_falls_back_to_intercept_for_huge_margin():
    rng = random.Random(0)
    X = [tuple(rng.uniform(-2, 2) for _ in range(3)) for _ in range(30)]
    y = [1.5 * x[0] * x[1] for x in X]
    assert margin_select(X, y, margin=1e9).names == ()


def test_margin_select_keeps_best_model_for_zero_margin_on_real_signal():
    rng = random.Random(1)
    X = [tuple(rng.uniform(-2, 2) for _ in range(3)) for _ in range(30)]
    y = [1.5 * x[0] * x[1] for x in X]
    assert margin_select(X, y, margin=0).names == ("x1*x2",)


def test_abstain_select_returns_none_on_misfit():
    rng = random.Random(2)
    X = [tuple(rng.uniform(-2, 2) for _ in range(3)) for _ in range(30)]
    y = [2 * __import__("math").tanh(x[0]) * x[1] for x in X]
    # Base space approximates tanh(x1)*x2 with RMSE ~0.24, so the frozen tau (0.15) must abstain.
    # A looser tau (0.25) would NOT abstain: this is why tau was calibrated, not chosen.
    assert abstain_select(X, y, tau=0.15) is None
    assert abstain_select(X, y, tau=0.25) is not None


def test_recording_wrapper_does_not_change_mechanism_output():
    # Same design/noise streams as exp01: M2 on in_space, seed 4, must match run_one exactly.
    law = LAWS["in_space"]
    inner = Oracle(law.fn, sigma=exp02.SIGMA, seed=4, budget=exp02.BUDGET)
    rec = exp02.RecordingOracle(inner)
    res = MECHANISMS["M2_active_fixed_space"](
        rec, exp02.BUDGET, exp02._mech_rng(4, "M2_active_fixed_space")
    )
    assert len(rec.X) == exp02.BUDGET == len(rec.y)
    direct = run_one(
        "in_space", "M2_active_fixed_space", seed=4, budget=exp02.BUDGET, sigma=exp02.SIGMA
    )
    assert "+".join(res.chosen_terms) == direct["chosen_terms"]


def test_exp02_artifact_hashes_match_files():
    with open(os.path.join(EXP02, "run_metadata.json"), encoding="utf-8") as f:
        meta = json.load(f)
    for name, digest in meta["artifacts"].items():
        assert provenance.sha256_file(os.path.join(EXP02, name)) == digest, name


def test_exp02_frozen_thresholds_are_the_calibrated_ones():
    with open(os.path.join(EXP02, "calibration.json"), encoding="utf-8") as f:
        cal = json.load(f)
    assert cal["margin_star"] == 10
    assert cal["tau_star"] == 0.15
    # margin_star sits at the grid edge: the pre-registered grid is the limit, not a finding.
    assert cal["margin_star"] == max(exp02.MARGIN_GRID)
