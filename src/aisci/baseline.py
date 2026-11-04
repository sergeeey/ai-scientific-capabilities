"""Null baseline: what a procedure's RMSE is when there is NO law to find.

Finite-sample fitting on pure noise gives a nonzero holdout RMSE. The exp03 null control
showed this matters (ratio 0.917 with no law). This module MEASURES that expected value for
each procedure at the same budget, so an effect can be read as a difference from it.

Runner-side. It uses a zero law defined here, so it needs no vault. The P26 formula
(1.63*sigma/sqrt(N)) is written to the output only for comparison; it is not used.

Usage:
    PYTHONPATH=src python -m aisci.baseline --out results/baseline
"""

import argparse
import json
import math
import os
import random
import statistics

from aisci import checker, pinned, provenance
from aisci.agents import MECHANISMS
from aisci.environment import Oracle

SIGMA = 0.1
BUDGET = 30
CAL_SEEDS = range(1000, 1200)
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _zero(x):
    return 0.0


class _NullLaw:
    fn = staticmethod(_zero)
    terms = frozenset()


NULL_LAW = _NullLaw()


def null_rmse(mech_name, seed, budget=BUDGET, sigma=SIGMA):
    oracle = Oracle(_zero, sigma=sigma, seed=seed, budget=budget)
    rng = random.Random(seed * 1000 + sorted(MECHANISMS).index(mech_name))
    res = MECHANISMS[mech_name](oracle, budget, rng)
    return checker.score(res.chosen, NULL_LAW)["test_rmse"]


def measure(mech_name, seeds=CAL_SEEDS, budget=BUDGET, sigma=SIGMA):
    vals = [null_rmse(mech_name, s, budget, sigma) for s in seeds]
    return {
        "mechanism": mech_name,
        "n_seeds": len(vals),
        "mean": statistics.fmean(vals),
        "median": statistics.median(vals),
        "formula_p26_for_comparison": 1.63 * sigma / math.sqrt(budget),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/baseline")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    out = {
        "seeds": [CAL_SEEDS.start, CAL_SEEDS.stop - 1],
        "budget": BUDGET,
        "sigma": SIGMA,
        "per_mechanism": {m: measure(m) for m in sorted(MECHANISMS)},
        "environment": provenance.environment_info(),
        "git": provenance.git_info(REPO_DIR),
    }
    path = os.path.join(a.out, "null_baseline.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    m1 = out["per_mechanism"]["M1_fixed_search"]
    pinned.artifact_ledger(
        a.out,
        "BL",
        ["null_baseline.json"],
        [
            ("M1_null_median", m1["median"], "null_baseline.json"),
            (
                "M1_formula_p26_for_comparison",
                m1["formula_p26_for_comparison"],
                "null_baseline.json",
            ),
        ],
    )
    print(json.dumps(out["per_mechanism"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
