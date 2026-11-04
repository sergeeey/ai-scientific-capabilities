"""Checks for the two corrections: identifiability certificate and measured null baseline."""

import json
import math
import os

import pytest

from aisci import baseline
from aisci.rules import identifiability_certificate

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_certificate_separates_disjoint_predictors():
    f = lambda u: u
    g = lambda u: u + 1.0
    out = identifiability_certificate([f, g], admissible_inputs=[0.0, 1.0, 2.0], sigma=0.1)
    assert out["verdict"] == "IDENTIFIABLE"
    assert out["min_pairwise_gap"] == pytest.approx(1.0)


def test_certificate_flags_identical_predictors():
    f = lambda u: u * u
    g = lambda u: u * u
    out = identifiability_certificate([f, g], admissible_inputs=[0.0, 1.0, 2.0], sigma=0.1)
    assert out["verdict"] == "NON_IDENTIFIABLE"


def test_certificate_threshold_is_k_times_sigma():
    f = lambda u: 0.0
    g = lambda u: 0.2
    small = identifiability_certificate([f, g], [0.0], sigma=0.1, k=3.0)  # 0.2 < 0.3
    big = identifiability_certificate([f, g], [0.0], sigma=0.05, k=3.0)  # 0.2 > 0.15
    assert small["verdict"] == "NON_IDENTIFIABLE"
    assert big["verdict"] == "IDENTIFIABLE"
    assert big["threshold"] == pytest.approx(0.15)


def test_null_rmse_is_deterministic_per_seed():
    a = baseline.null_rmse("M1_fixed_search", seed=1005)
    b = baseline.null_rmse("M1_fixed_search", seed=1005)
    assert a == b
    assert a > 0 and math.isfinite(a)


def test_measured_null_baseline_is_not_the_formula_for_m1():
    # The P26 formula is kept only for comparison. The file must hold measured values, and for M1
    # the measured median must differ from the formula by more than 20%.
    path = os.path.join(ROOT, "results", "baseline", "null_baseline.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    m1 = data["per_mechanism"]["M1_fixed_search"]
    rel = abs(m1["median"] - m1["formula_p26_for_comparison"]) / m1["median"]
    assert rel > 0.20
    assert m1["n_seeds"] == 200
