"""exp04 runner: calibration gate (seeds 1000-1004), then the test run (seeds 0-9) if it passes.

Protocol: docs/PREREG_exp04.md. Runner-side (imports the hidden delay worlds from the vault).

Usage:
    PYTHONPATH=src python -m aisci.exp04 --out results/exp04
"""

import argparse
import csv
import io
import json
import math
import os
import random

from aisci import pinned, provenance
from aisci.dde import (
    BUDGET,
    SIGMA,
    SIM_DT,
    DelayOracle,
    delay_rhs,
    holdout_rmse,
    random_phi,
    run_condition,
    simulate,
    truth_rhs,
)
from aisci.hidden_laws import load_dde_worlds
from aisci.rules import identifiability_certificate

# SHA-256 of the vault file is pinned in hidden_laws.py; worlds come from that file.
CAL_SEEDS = range(1000, 1005)
TEST_SEEDS = range(10)
CONDS = ("A1", "A2", "A3")
N_HOLDOUT = 10
FIELDS = [
    "world",
    "kind",
    "cond",
    "seed",
    "outcome",
    "correct",
    "abstained",
    "false_delay",
    "expanded_at",
    "n",
    "tau_true",
    "holdout_rmse",
]
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def classify(kind, tau, outcome):
    abstained = outcome in ("UNEXPLAINED", "NON_IDENTIFIABLE")
    if kind == "delay":
        correct = outcome.startswith("delay:") and math.isclose(float(outcome.split(":", 1)[1]), tau)
        false_delay = outcome.startswith("delay:") and not correct
    elif kind == "weak":
        correct = outcome in ("memoryless", "NON_IDENTIFIABLE")
        false_delay = outcome.startswith("delay:")
    else:  # memoryless, zero
        correct = outcome == "memoryless"
        false_delay = outcome.startswith("delay:")
    return correct, abstained, false_delay


def run_one(name, world, cond, seed, widx):
    a, b, tau = world["a"], world["b"], world["tau"]
    oracle = DelayOracle(a, b, tau, sigma=SIGMA, seed=seed * 1000 + widx, budget=BUDGET)
    rng = random.Random(seed * 1000 + CONDS.index(cond) * 100 + widx)
    cert_rng = random.Random(seed * 1000 + 500 + widx)
    res = run_condition(cond, oracle, rng, cert_rng)
    test_rng = random.Random(999000 + seed * 100 + widx)
    phis = [random_phi(test_rng) for _ in range(N_HOLDOUT)]
    rmse = holdout_rmse(res["outcome"], res["model"], truth_rhs(a, b), round(tau / SIM_DT), phis)
    correct, abstained, false_delay = classify(world["kind"], tau, res["outcome"])
    assert oracle.calls == BUDGET
    return {
        "world": name,
        "kind": world["kind"],
        "cond": cond,
        "seed": seed,
        "outcome": res["outcome"],
        "correct": correct,
        "abstained": abstained,
        "false_delay": false_delay,
        "expanded_at": res["expanded_at"] or "",
        "n": res["n"],
        "tau_true": tau if world["kind"] == "delay" else "",
        "holdout_rmse": "" if rmse is None else round(rmse, 6),
    }


def gate(worlds):
    """Calibration checks. Returns (passed, details). Uses calibration seeds only."""
    pool = [random_phi(random.Random(77 + i)) for i in range(40)]
    w01 = worlds["w01"]
    c03 = worlds["c03"]

    def pred(world, tau):
        lag = round(tau / SIM_DT)
        rhs = delay_rhs(-world["a"], world["b"])
        return lambda u: simulate(rhs, lag, u)

    pos = identifiability_certificate([pred(w01, 0.4), pred(w01, 0.8)], pool, SIGMA, k=3.0)
    neg = identifiability_certificate([pred(c03, 0.6), pred(c03, 0.8)], pool, SIGMA, k=3.0)
    cal_rows = []
    for name, world in worlds.items():
        widx = sorted(worlds).index(name)
        for seed in CAL_SEEDS:
            cal_rows.append(run_one(name, world, "A3", seed, widx))
    delay_rows = [r for r in cal_rows if r["kind"] == "delay"]
    ctrl_rows = [r for r in cal_rows if r["kind"] != "delay"]
    g2 = sum(r["correct"] for r in delay_rows) / len(delay_rows)
    g3 = sum(r["false_delay"] for r in ctrl_rows) / len(ctrl_rows)
    details = {
        "G1_positive_w01_tau04_vs_08": pos["verdict"],
        "G1_negative_c03_tau06_vs_08": neg["verdict"],
        "G2_A3_correct_on_delay": g2,
        "G3_A3_false_delay_on_controls": g3,
    }
    passed = (
        pos["verdict"] == "IDENTIFIABLE"
        and neg["verdict"] == "NON_IDENTIFIABLE"
        and g2 >= 0.5
        and g3 <= 0.10
    )
    return passed, details, cal_rows


def summarize(rows):
    out = {}
    for cond in CONDS:
        sub = [r for r in rows if r["cond"] == cond]
        delay = [r for r in sub if r["kind"] == "delay"]
        ctrl = [r for r in sub if r["kind"] != "delay"]
        rmses = [r["holdout_rmse"] for r in delay if r["correct"] and r["holdout_rmse"] != ""]
        out[cond] = {
            "delay_correct_rate": sum(r["correct"] for r in delay) / len(delay),
            "delay_abstain_rate": sum(r["abstained"] for r in delay) / len(delay),
            "control_false_delay_rate": sum(r["false_delay"] for r in ctrl) / len(ctrl),
            "delay_correct_median_holdout_rmse": (
                sorted(rmses)[len(rmses) // 2] if rmses else None
            ),
            "n_runs": len(sub),
        }
    verdict = {
        "H-A3": "supported" if out["A3"]["delay_correct_rate"] >= 0.5 else "refuted",
        "H-D": (
            "supported"
            if out["A1"]["delay_abstain_rate"] >= 0.9 and out["A2"]["delay_abstain_rate"] >= 0.9
            else "refuted"
        ),
        "H-N": ("supported" if out["A3"]["control_false_delay_rate"] <= 0.10 else "refuted"),
    }
    return out, verdict


def _write_csv(path, rows):
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(buf.getvalue())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/exp04")
    # Default: development-contaminated seeds 0-9 (see RESEARCH_LOG). Confirmation: 10-19.
    ap.add_argument("--test-start", type=int, default=0)
    ap.add_argument("--test-n", type=int, default=10)
    a = ap.parse_args(argv)
    test_seeds = range(a.test_start, a.test_start + a.test_n)
    os.makedirs(a.out, exist_ok=True)
    # Per-run files reveal the hidden worlds (a correct run names the true tau). They go to a
    # private directory OUTSIDE the repo; only aggregates and hashes are committed.
    out_abs = os.path.abspath(a.out)
    if not out_abs.startswith(os.path.join(REPO_DIR, "results") + os.sep):
        raise ValueError("--out must be a folder under results/")
    private = os.path.join(REPO_DIR, "..", "aisci-private-results", os.path.basename(out_abs))
    os.makedirs(private, exist_ok=True)
    worlds = load_dde_worlds()

    passed, details, cal_rows = gate(worlds)
    _write_csv(os.path.join(private, "calibration_runs.csv"), cal_rows)
    cal = {"seeds": [CAL_SEEDS.start, CAL_SEEDS.stop - 1], "gate_passed": passed, "gate": details}
    with open(os.path.join(a.out, "calibration.json"), "w", encoding="utf-8") as f:
        json.dump(cal, f, indent=2, sort_keys=True)
        f.write("\n")

    files = ["calibration.json"]
    if passed:
        rows = []
        for name, world in worlds.items():
            widx = sorted(worlds).index(name)
            for cond in CONDS:
                for seed in test_seeds:
                    rows.append(run_one(name, world, cond, seed, widx))
        _write_csv(os.path.join(private, "test_runs.csv"), rows)
        summary, verdict = summarize(rows)
        result = {"summary": summary, "verdict": verdict}
    else:
        result = {"status": "not run: calibration gate failed; see calibration.json"}
    with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True, default=float)
        f.write("\n")
    files.append("summary.json")

    derived = []
    if passed:
        for cond in CONDS:
            s = result["summary"][cond]
            derived += [
                (f"{cond}_delay_correct_rate", s["delay_correct_rate"], "summary.json"),
                (f"{cond}_delay_abstain_rate", s["delay_abstain_rate"], "summary.json"),
                (f"{cond}_control_false_delay_rate", s["control_false_delay_rate"], "summary.json"),
            ]
    pinned.artifact_ledger(a.out, "E4", files, derived)

    meta = {
        "config": {
            "budget": BUDGET,
            "sigma": SIGMA,
            "calibration_seeds": [1000, 1004],
            "test_seeds": [a.test_start, a.test_start + a.test_n - 1],
            "conditions": list(CONDS),
            "n_holdout": N_HOLDOUT,
        },
        "environment": provenance.environment_info(),
        "git": provenance.git_info(REPO_DIR),
        "code_sha256": provenance.code_hashes(),
        "artifacts": {name: provenance.sha256_file(os.path.join(a.out, name)) for name in files},
        "private_artifacts_outside_repo": {
            name: provenance.sha256_file(os.path.join(private, name))
            for name in sorted(os.listdir(private))
        },
    }
    with open(os.path.join(a.out, "run_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    print(
        json.dumps(
            {
                "calibration": cal,
                **({"verdict": result["verdict"]} if passed else {"status": result["status"]}),
            },
            indent=2,
            sort_keys=True,
            default=float,
        )
    )


if __name__ == "__main__":
    main()
