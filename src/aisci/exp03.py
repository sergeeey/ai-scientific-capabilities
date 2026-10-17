"""exp03 runner: sensitivity checks on calibration seeds, then the test run only if they pass.

Protocol: docs/PREREG_exp03.md. Runner-side. Uses run_one (unchanged) for every run, so the
M1/M2 numbers at budget 30 are the same as exp01 on seeds 0-29.

Usage:
    PYTHONPATH=src python -m aisci.exp03 --out results/exp03
"""

import argparse
import json
import os
import random

from aisci import provenance
from aisci.run import run_one

BUDGET = 30
SIGMA = 0.1
CAL_SEEDS = range(1000, 1200)
TEST_SEEDS = range(200)
MCID_RATIO = 0.80
POS_CONTROL_MAX_RATIO = 0.80
CEILING_MAX = 0.05
BOOT = 10000
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _rmse(law, mech, seed, budget):
    return run_one(law, mech, seed, budget, SIGMA)["test_rmse"]


def _median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _boot_median_ci(xs, seed=0):
    rng = random.Random(seed)
    n = len(xs)
    meds = sorted(_median([xs[rng.randrange(n)] for _ in range(n)]) for _ in range(BOOT))
    return meds[int(0.025 * BOOT)], meds[int(0.975 * BOOT)]


def calibrate():
    pos_m60, pos_m30, m1, m2 = [], [], [], []
    for seed in CAL_SEEDS:
        pos_m60.append(_rmse("in_space", "M1_fixed_search", seed, 60))
        pos_m30.append(_rmse("in_space", "M1_fixed_search", seed, 30))
        m1.append(_rmse("in_space", "M1_fixed_search", seed, BUDGET))
        m2.append(_rmse("in_space", "M2_active_fixed_space", seed, BUDGET))
    pos_ratio = _median(pos_m60) / _median(pos_m30)
    ceiling = sum(1 for a, b in zip(m1, m2) if a == b) / len(m1)
    cal = {
        "calibration_seeds": [CAL_SEEDS.start, CAL_SEEDS.stop - 1],
        "positive_control": {
            "median_rmse_m1_b30": _median(pos_m30),
            "median_rmse_m1_b60": _median(pos_m60),
            "ratio_b60_over_b30": pos_ratio,
            "pass": pos_ratio <= POS_CONTROL_MAX_RATIO,
        },
        "ceiling_check": {"fraction_exact_equal": ceiling, "pass": ceiling < CEILING_MAX},
    }
    cal["passed"] = cal["positive_control"]["pass"] and cal["ceiling_check"]["pass"]
    return cal


def test_run():
    out = {}
    for law in ["in_space", "null"]:
        ratios, m1s, m2s = [], [], []
        for seed in TEST_SEEDS:
            a = _rmse(law, "M1_fixed_search", seed, BUDGET)
            b = _rmse(law, "M2_active_fixed_space", seed, BUDGET)
            m1s.append(a)
            m2s.append(b)
            if a > 0:
                ratios.append(b / a)
        out[law] = {
            "n_seeds": len(ratios),
            "median_ratio": _median(ratios),
            "ci95": list(_boot_median_ci(ratios)),
            "rmse_median_m1": _median(m1s),
            "rmse_median_m2": _median(m2s),
            "ratios": ratios,
        }
    return out


def verdict(res):
    r = res["in_space"]
    lo, hi = r["ci95"]
    med = r["median_ratio"]
    if med <= MCID_RATIO and hi < 1.0:
        v = "supported"
    elif lo >= MCID_RATIO:
        v = "refuted"
    else:
        v = "inconclusive"
    n = res["null"]
    return {
        "H-A_prime": v,
        "in_space_median_ratio": med,
        "in_space_ci95": [lo, hi],
        "negative_control_null": {
            "median_ratio": n["median_ratio"],
            "ci95": n["ci95"],
            "ci_includes_1": n["ci95"][0] <= 1.0 <= n["ci95"][1],
        },
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/exp03")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    cal = calibrate()
    with open(os.path.join(a.out, "calibration.json"), "w", encoding="utf-8") as f:
        json.dump(cal, f, indent=2, sort_keys=True)
        f.write("\n")
    artifacts = ["calibration.json"]

    if cal["passed"]:
        res = test_run()
        with open(os.path.join(a.out, "test_results.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, sort_keys=True)
            f.write("\n")
        v = verdict(res)
        with open(os.path.join(a.out, "verdicts.json"), "w", encoding="utf-8") as f:
            json.dump(v, f, indent=2, sort_keys=True)
            f.write("\n")
        artifacts += ["test_results.json", "verdicts.json"]
    else:
        v = {"status": "not run: calibration checks failed; see calibration.json"}

    meta = {
        "config": {
            "budget": BUDGET,
            "sigma": SIGMA,
            "calibration_seeds": [1000, 1199],
            "test_seeds": [0, 199],
            "mcid_ratio": MCID_RATIO,
            "pos_control_max_ratio": POS_CONTROL_MAX_RATIO,
            "ceiling_max": CEILING_MAX,
        },
        "environment": provenance.environment_info(),
        "git": provenance.git_info(REPO_DIR),
        "code_sha256": provenance.code_hashes(),
        "artifacts": {
            name: provenance.sha256_file(os.path.join(a.out, name)) for name in artifacts
        },
    }
    with open(os.path.join(a.out, "run_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"calibration": cal, "verdict": v}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
