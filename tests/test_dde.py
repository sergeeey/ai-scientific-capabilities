"""exp04 checks: integrator, oracle budget, agent-side isolation, pre-registration and artifacts."""

import ast
import json
import math
import os
import random

import pytest

from aisci import dde, exp04, provenance
from aisci.dde import DelayOracle, deriv_tol, simulate, truth_rhs
from aisci.environment import BudgetExceeded
from aisci.hidden_laws import load_dde_worlds

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXP04 = os.path.join(ROOT, "results", "exp04")


def test_integrator_matches_exact_exponential_without_delay():
    # b = 0: x' = -a x, exact solution x0 * exp(-a t). Euler error with step 0.01 is small.
    phi = [1.0] * dde.N_KNOTS  # constant history at 1.0
    xs = simulate(truth_rhs(0.5, 0.0), round(0.4 / dde.SIM_DT), phi)
    for k, x in enumerate(xs):
        t = k * dde.SAMPLE_DT
        assert x == pytest.approx(math.exp(-0.5 * t), abs=5e-3)


def test_oracle_budget_is_a_hard_cap():
    o = DelayOracle(0.5, 0.6, 0.4, sigma=0.0, seed=0, budget=3)
    phi = [0.0] * dde.N_KNOTS
    for _ in range(3):
        o.experiment(phi)
    with pytest.raises(BudgetExceeded):
        o.experiment(phi)
    assert o.calls == 3


def test_agent_side_module_does_not_import_hidden_worlds():
    with open(os.path.join(ROOT, "src", "aisci", "dde.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[-1] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[-1])
    assert not mods & {"hidden_laws", "checker", "run", "exp04"}


def test_threshold_is_noise_derived_and_shrinks_with_rows():
    assert deriv_tol(10) > deriv_tol(1000) > dde.DERIV_SIGMA
    assert dde.DERIV_SIGMA == pytest.approx(0.01 * math.sqrt(2) / (2 * 0.05))


def test_vault_has_twelve_worlds_with_grid_delays():
    worlds = load_dde_worlds()
    assert len(worlds) == 12
    for w in worlds.values():
        if w["kind"] == "delay":
            assert w["tau"] in dde.TAUS


def test_classify_rules():
    assert exp04.classify("delay", 0.4, "delay:0.4") == (True, False, False)
    assert exp04.classify("delay", 0.4, "delay:0.8") == (False, False, True)
    assert exp04.classify("delay", 0.4, "UNEXPLAINED") == (False, True, False)
    assert exp04.classify("memoryless", 0.4, "memoryless") == (True, False, False)
    assert exp04.classify("memoryless", 0.4, "delay:0.4") == (False, False, True)
    assert exp04.classify("weak", 0.6, "NON_IDENTIFIABLE") == (True, True, False)


def test_prereg_matches_code_constants():
    with open(os.path.join(ROOT, "docs", "PREREG_exp04.md"), encoding="utf-8") as f:
        text = f.read()
    assert list(exp04.CAL_SEEDS) == [1000, 1001, 1002, 1003, 1004]
    assert list(exp04.TEST_SEEDS) == list(range(10))
    assert "budget" in text.lower() and dde.BUDGET == 30
    assert "61 noisy samples" in text and dde.N_SAMPLES == 61
    assert "0.05" in text and dde.SAMPLE_DT == 0.05


@pytest.mark.parametrize("out_dir", ["exp04", "exp04_confirm"])
def test_exp04_artifacts_match_recorded_hashes(out_dir):
    base = os.path.join(ROOT, "results", out_dir)
    with open(os.path.join(base, "run_metadata.json"), encoding="utf-8") as f:
        meta = json.load(f)
    for name, digest in meta["artifacts"].items():
        assert provenance.sha256_file(os.path.join(base, name)) == digest, name


def test_exp04_calibration_gate_passed_before_test_run():
    with open(os.path.join(EXP04, "calibration.json"), encoding="utf-8") as f:
        cal = json.load(f)
    assert cal["gate_passed"] is True
    assert cal["gate"]["G1_positive_w01_tau04_vs_08"] == "IDENTIFIABLE"
    assert cal["gate"]["G1_negative_c03_tau06_vs_08"] == "NON_IDENTIFIABLE"


def test_exp04_ledger_entries_match_summary():
    with open(os.path.join(EXP04, "summary.json"), encoding="utf-8") as f:
        summary = json.load(f)["summary"]
    entries = {e["id"]: e for e in pinned_ledger(os.path.join(EXP04, "ledger.jsonl"))}
    assert entries["E4-D-007"]["value"] == pytest.approx(summary["A3"]["delay_correct_rate"])
    assert entries["E4-D-002"]["value"] == pytest.approx(summary["A1"]["delay_abstain_rate"])


def pinned_ledger(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_random_histories_are_reproducible():
    a = dde.random_phi(random.Random(3))
    b = dde.random_phi(random.Random(3))
    assert a == b
