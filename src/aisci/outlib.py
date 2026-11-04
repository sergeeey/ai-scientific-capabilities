"""Out-of-library run: law x'-free primitive exp outside every library (vault law out_of_library).

Hypothesis D (insufficiency is detected, not a constructive expansion): under the frozen
abstention threshold from exp02 (tau = 0.15, pinned calibration), M1 data abstain on most runs,
and M3 never finds a true expansion (no library term matches exp).

Runner-side. Reuses exp02 measurement and rules. No threshold is re-tuned here.

Usage:
    PYTHONPATH=src python -m aisci.outlib --out results/outlib
"""

import argparse
import json
import os

from aisci import exp02, pinned, provenance
from aisci.rules import abstain_select

LAW = "out_of_library"
SEEDS = range(30)
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CAL_PATH = os.path.join(REPO_DIR, "results", "exp02", "calibration.json")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/outlib")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    cal = pinned.load_pinned_json(CAL_PATH, exp02.CAL_SHA256)
    tau = cal["tau_star"]

    abstain = 0
    m3_true = 0
    m3_expanded = 0
    for seed in SEEDS:
        _, X1, y1 = exp02._measure_run(LAW, "M1_fixed_search", seed)
        if abstain_select(X1, y1, tau) is None:
            abstain += 1
        m3_model, _, _ = exp02._measure_run(LAW, "M3_expand", seed)
        if m3_model.names:
            m3_expanded += 1
        if set(m3_model.names) == {"x1*exp(x2)"}:
            m3_true += 1  # cannot happen: no library term is named exp*
    out = {
        "law": LAW,
        "seeds": [SEEDS.start, SEEDS.stop - 1],
        "budget": exp02.BUDGET,
        "frozen_tau_from_exp02": tau,
        "M1_abstain_rate": abstain / len(SEEDS),
        "M3_named_any_term_rate": m3_expanded / len(SEEDS),
        "M3_matches_true_term_rate": m3_true / len(SEEDS),
        "environment": provenance.environment_info(),
        "git": provenance.git_info(REPO_DIR),
    }
    path = os.path.join(a.out, "summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    pinned.artifact_ledger(
        a.out,
        "OL",
        ["summary.json"],
        [
            ("M1_abstain_rate", out["M1_abstain_rate"], "summary.json"),
            ("M3_named_any_term_rate", out["M3_named_any_term_rate"], "summary.json"),
            ("M3_matches_true_term_rate", out["M3_matches_true_term_rate"], "summary.json"),
        ],
    )
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
