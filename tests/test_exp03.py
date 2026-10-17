"""exp03 checks: frozen constants match the pre-registration, seeds are disjoint, artifacts hash-match.

The full exp03 run takes about 100 seconds, so it is not re-run here.
"""

import json
import os

from aisci import exp03, provenance

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXP03 = os.path.join(ROOT, "results", "exp03")


def test_calibration_and_test_seeds_are_disjoint():
    assert not set(exp03.CAL_SEEDS) & set(exp03.TEST_SEEDS)


def test_frozen_constants_match_prereg():
    with open(os.path.join(ROOT, "docs", "PREREG_exp03.md"), encoding="utf-8") as f:
        text = f.read()
    assert exp03.MCID_RATIO == 0.80 and "median ratio ≤ 0.80" in text
    assert exp03.POS_CONTROL_MAX_RATIO == 0.80
    assert exp03.CEILING_MAX == 0.05 and "< 5%" in text
    assert exp03.BUDGET == 30 and exp03.SIGMA == 0.1


def test_verdict_rule_supported_and_refuted_branches():
    def res(med, lo, hi):
        return {
            "in_space": {"median_ratio": med, "ci95": [lo, hi]},
            "null": {"median_ratio": 1.0, "ci95": [0.9, 1.1]},
        }

    # supported: median <= 0.80 AND upper CI < 1.00
    assert exp03.verdict(res(0.77, 0.70, 0.84))["H-A_prime"] == "supported"
    # refuted: lower CI bound >= 0.80 (checked before inconclusive, as in the pre-registration)
    assert exp03.verdict(res(0.90, 0.85, 1.05))["H-A_prime"] == "refuted"
    assert exp03.verdict(res(0.95, 0.80, 1.1))["H-A_prime"] == "refuted"
    assert exp03.verdict(res(1.0, 0.85, 1.2))["H-A_prime"] == "refuted"
    # inconclusive: CI straddles 0.80, or point estimate ok but upper CI reaches 1
    assert exp03.verdict(res(0.90, 0.75, 1.05))["H-A_prime"] == "inconclusive"
    assert exp03.verdict(res(0.78, 0.70, 1.02))["H-A_prime"] == "inconclusive"


def test_exp03_artifact_hashes_match_files():
    with open(os.path.join(EXP03, "run_metadata.json"), encoding="utf-8") as f:
        meta = json.load(f)
    for name, digest in meta["artifacts"].items():
        assert provenance.sha256_file(os.path.join(EXP03, name)) == digest, name


def test_exp03_calibration_passed_before_test_run():
    with open(os.path.join(EXP03, "calibration.json"), encoding="utf-8") as f:
        cal = json.load(f)
    assert cal["passed"] is True
    assert os.path.exists(os.path.join(EXP03, "verdicts.json"))
