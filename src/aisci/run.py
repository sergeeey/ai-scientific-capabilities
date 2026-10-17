"""Runner: every mechanism x every law x fixed seeds, at one shared measurement budget.

Usage (from project root):
    set PYTHONPATH=src
    python -m aisci.run --seeds 30 --budget 30 --sigma 0.1 --out results
"""

import argparse
import csv
import os
import random
import statistics

from aisci.agents import MECHANISMS
from aisci.checker import score
from aisci.environment import Oracle
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


def run_one(law_name, mech_name, seed, budget, sigma):
    law = LAWS[law_name]
    oracle = Oracle(law.fn, sigma=sigma, seed=seed)  # noise stream: fixed per seed
    rng = random.Random(seed * 1000 + sorted(MECHANISMS).index(mech_name))  # design stream
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--budget", type=int, default=30)
    ap.add_argument("--sigma", type=float, default=0.1)
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = run_all(a.seeds, a.budget, a.sigma)
    with open(os.path.join(a.out, "runs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    table = summarize(rows)
    header = (
        f"# Summary (seeds={a.seeds}, budget={a.budget}, sigma={a.sigma})\n\n"
        "Synthetic data only. VERIFIED-SYNTHETIC. Not evidence about LLMs.\n\n"
    )
    with open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8") as f:
        f.write(header + table + "\n")
    print(header + table)


if __name__ == "__main__":
    main()
