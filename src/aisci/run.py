"""Runner: every mechanism x every law x fixed seeds, at one shared measurement budget.

Usage (from project root, bash):
    PYTHONPATH=src python -m aisci.run --seeds 30 --budget 30 --sigma 0.1 --out results

Writes into --out:
    runs.csv              one row per run (format unchanged since exp01)
    summary.md            human-readable table; cites run_id and runs.csv SHA-256
    run_metadata.json     config, seeds, budget, algorithms, versions, git commit, artifact hashes
    evidence_ledger.jsonl machine-readable trace: measurement and derived entries
"""

import argparse
import csv
import io
import json
import os
import random
import statistics
import sys

from aisci import checker, ledger, provenance
from aisci.agents import MECHANISMS
from aisci.checker import score
from aisci.environment import Oracle
from aisci.features import BOUNDS, DIM
from aisci.hidden_laws import LAWS

FIELDS = [
    "law",
    "mechanism",
    "seed",
    "n_calls",
    "chosen_terms",
    "expanded_at",
    "test_rmse",
    "recovered",
    "exact_terms",
    "false_terms",
]

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def run_one(law_name, mech_name, seed, budget, sigma):
    law = LAWS[law_name]
    # Noise stream seeded per seed; design stream seeded per (seed, mechanism).
    oracle = Oracle(law.fn, sigma=sigma, seed=seed, budget=budget)
    rng = random.Random(seed * 1000 + sorted(MECHANISMS).index(mech_name))
    res = MECHANISMS[mech_name](oracle, budget, rng)
    if oracle.calls != budget:
        raise RuntimeError(f"budget violated: {oracle.calls} != {budget}")
    s = score(res.chosen, law)
    return {
        "law": law_name,
        "mechanism": mech_name,
        "seed": seed,
        "n_calls": oracle.calls,
        "chosen_terms": "+".join(res.chosen_terms) or "(intercept only)",
        "expanded_at": res.expanded_at if res.expanded_at is not None else "",
        "test_rmse": round(s["test_rmse"], 6),
        "recovered": s["recovered"],
        "exact_terms": s["exact_terms"],
        "false_terms": "" if s["false_terms"] is None else "+".join(s["false_terms"]),
    }


def run_all(seeds, budget, sigma):
    rows = []
    for law_name in LAWS:
        for mech_name in MECHANISMS:
            for seed in range(seeds):
                rows.append(run_one(law_name, mech_name, seed, budget, sigma))
    return rows


def runs_csv_text(rows):
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def config_for(seeds, budget, sigma):
    return {
        "laws": list(LAWS),
        "mechanisms": sorted(MECHANISMS),
        "seeds": seeds,
        "seed_range": [0, seeds - 1],
        "budget": budget,
        "sigma": sigma,
        "domain_bounds": list(BOUNDS),
        "dim": DIM,
        "test_seed": checker.TEST_SEED,
        "n_test": checker.N_TEST,
        "recovery_rmse": checker.RECOVERY_RMSE,
    }


def summarize(rows):
    lines = [
        "| law | mechanism | recovered | exact terms | median test RMSE | expansions | null: any false term |",
        "|---|---|---|---|---|---|---|",
    ]
    for law_name in LAWS:
        for mech_name in MECHANISMS:
            sub = [r for r in rows if r["law"] == law_name and r["mechanism"] == mech_name]
            n = len(sub)
            rec = sum(r["recovered"] for r in sub)
            exact = sum(r["exact_terms"] for r in sub)
            med = statistics.median(r["test_rmse"] for r in sub)
            exp = sum(1 for r in sub if r["expanded_at"] != "")
            fp = sum(1 for r in sub if r["false_terms"] != "")
            fp_cell = f"{fp}/{n}" if law_name == "null" else "-"
            lines.append(
                f"| {law_name} | {mech_name} | {rec}/{n} | {exact}/{n} | "
                f"{med:.4f} | {exp}/{n} | {fp_cell} |"
            )
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--budget", type=int, default=30)
    ap.add_argument("--sigma", type=float, default=0.1)
    ap.add_argument("--out", default="results")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    config = config_for(a.seeds, a.budget, a.sigma)
    run_id = provenance.sha256_text(provenance.canonical_json(config))[:12]

    rows = run_all(a.seeds, a.budget, a.sigma)
    csv_text = runs_csv_text(rows)
    runs_path = os.path.join(a.out, "runs.csv")
    with open(runs_path, "w", newline="", encoding="utf-8") as f:
        f.write(csv_text)
    runs_sha = provenance.sha256_file(runs_path)

    runs_rel = runs_path.replace("\\", "/")
    meas = ledger.measurement_entries(rows, run_id, runs_rel, runs_sha, a.budget)
    entries = meas + ledger.derived_entries(meas, run_id)
    ledger_text = ledger.dumps(entries)
    ledger_path = os.path.join(a.out, "evidence_ledger.jsonl")
    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write(ledger_text)

    header = (
        f"# Summary (seeds={a.seeds}, budget={a.budget}, sigma={a.sigma})\n\n"
        f"run_id: `{run_id}`; runs.csv sha256: `{runs_sha}`\n\n"
        "Synthetic data only. VERIFIED-SYNTHETIC. Not evidence about LLMs.\n\n"
    )
    table = summarize(rows)
    summary_path = os.path.join(a.out, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(header + table + "\n")

    metadata = {
        "run_id": run_id,
        "command": "PYTHONPATH=src python -m aisci.run " + " ".join(argv or sys.argv[1:]),
        "config": config,
        "algorithms": {
            "M1_fixed_search": "random design, BIC over H0 (<=2 terms + intercept)",
            "M2_active_fixed_space": "M1 + max predictive-variance design over top BIC models",
            "M3_expand": "M2 + switch to FULL_LIB when base RMSE > expansion tol",
        },
        "baseline": "M1_fixed_search",
        "budget_enforcement": "Oracle raises BudgetExceeded after `budget` calls",
        "environment": provenance.environment_info(),
        "git": provenance.git_info(REPO_DIR),
        "code_sha256": provenance.code_hashes(),
        "artifacts": {
            "runs.csv": {"sha256": runs_sha},
            "summary.md": {"sha256": provenance.sha256_file(summary_path)},
            "evidence_ledger.jsonl": {"sha256": provenance.sha256_file(ledger_path)},
        },
        "isolation": "soft: in-process; see src/aisci/environment.py docstring",
    }
    with open(os.path.join(a.out, "run_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    print(header + table)


if __name__ == "__main__":
    main()
