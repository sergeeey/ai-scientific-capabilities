"""Evidence Ledger: machine-readable trace from each conclusion to real runs.

Entry types:
  measurement  one row of runs.csv: a real run of a mechanism on a law (machine-generated)
  derived      a summary statistic computed from named measurement entries (machine-generated)
  claim        a statement with a status and cited evidence; authored in docs/claims.json,
               checked by tests/test_foundation.py (it does not come from the runner)

A claim is only "supported" or "falsified" if it cites entries that exist in the ledger.
"""

import json
import statistics

from aisci.agents import MECHANISMS
from aisci.hidden_laws import LAWS


def measurement_entries(rows, run_id, runs_file, runs_sha256, budget):
    out = []
    for i, r in enumerate(rows, start=1):
        out.append(
            {
                "id": f"M-{i:04d}",
                "type": "measurement",
                "run_id": run_id,
                "law": r["law"],
                "mechanism": r["mechanism"],
                "seed": r["seed"],
                "budget": budget,
                "n_calls": r["n_calls"],
                "exact_terms": r["exact_terms"],
                "recovered": r["recovered"],
                "test_rmse": r["test_rmse"],
                "chosen_terms": r["chosen_terms"],
                "false_terms": r["false_terms"],
                "expanded_at": r["expanded_at"],
                "source": runs_file,
                "source_sha256": runs_sha256,
                "source_row": i,
            }
        )
    return out


def derived_entries(meas, run_id):
    out = []
    k = 0
    for law in LAWS:
        for mech in MECHANISMS:
            sub = [m for m in meas if m["law"] == law and m["mechanism"] == mech]
            if not sub:
                continue
            ids = [m["id"] for m in sub]
            metrics = {
                "exact_terms_count": sum(bool(m["exact_terms"]) for m in sub),
                "recovered_count": sum(bool(m["recovered"]) for m in sub),
                "expansion_count": sum(m["expanded_at"] != "" for m in sub),
                "false_term_runs": sum(m["false_terms"] != "" for m in sub),
                "median_test_rmse": round(statistics.median(m["test_rmse"] for m in sub), 4),
                "n_runs": len(sub),
            }
            for name, value in metrics.items():
                k += 1
                out.append(
                    {
                        "id": f"D-{k:04d}",
                        "type": "derived",
                        "run_id": run_id,
                        "law": law,
                        "mechanism": mech,
                        "metric": name,
                        "value": value,
                        "inputs": ids,
                        "method": "count or median over inputs",
                    }
                )
    return out


def dumps(entries):
    return "".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in entries)


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
