"""exp02 runner: calibration on seeds 1000-1199, test on seeds 0-199, per docs/PREREG_exp02.md.

Runner-side (imports hidden laws). Mechanisms are unchanged; RecordingOracle wraps the
Oracle and stores each (x, y) so rules can be applied to the same data afterwards.

Usage:
    PYTHONPATH=src python -m aisci.exp02 --out results/exp02
"""

import argparse
import csv
import io
import json
import os
import random

from aisci import provenance
from aisci.agents import MECHANISMS
from aisci.checker import score
from aisci.environment import Oracle
from aisci.exp_config import EXP01_LAWS
from aisci.hidden_laws import LAWS
from aisci.rules import abstain_select, margin_select

BUDGET = 30
SIGMA = 0.1
CAL_SEEDS = range(1000, 1200)
TEST_SEEDS = range(200)
MARGIN_GRID = [0, 2, 4, 6, 8, 10]
TAU_GRID = [0.10, 0.15, 0.20, 0.25, 0.30]
FDR_MAX = 0.05
RECOVERY_MIN = 0.80
ABSTAIN_MAX_NULL_LIKE = 0.05
ABSTAIN_MIN_EXPANSION = 0.90
BOOT_RESAMPLES = 10000
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

FIELDS = [
    "law",
    "seed",
    "procedure",
    "chosen_terms",
    "exact_terms",
    "false_terms",
    "abstained",
    "test_rmse",
    "recovered",
]


class RecordingOracle:
    """Pass-through to Oracle that records every (x, y). Measurements are unchanged."""

    def __init__(self, inner):
        self.inner = inner
        self.X = []
        self.y = []

    def measure(self, x):
        v = self.inner.measure(x)
        self.X.append(x)
        self.y.append(v)
        return v

    @property
    def calls(self):
        return self.inner.calls


def _mech_rng(seed, mech_name):
    # Same stream as aisci.run.run_one, so M1/M2 match exp01 on seeds 0-29.
    return random.Random(seed * 1000 + sorted(MECHANISMS).index(mech_name))


def _measure_run(law_name, mech_name, seed):
    law = LAWS[law_name]
    inner = Oracle(law.fn, sigma=SIGMA, seed=seed, budget=BUDGET)
    rec = RecordingOracle(inner)
    res = MECHANISMS[mech_name](rec, BUDGET, _mech_rng(seed, mech_name))
    assert inner.calls == BUDGET
    return res.chosen, rec.X, rec.y


def _row(law_name, seed, procedure, model):
    law = LAWS[law_name]
    if model is None:
        return {
            "law": law_name,
            "seed": seed,
            "procedure": procedure,
            "chosen_terms": "UNEXPLAINED",
            "exact_terms": False,
            "false_terms": "",
            "abstained": True,
            "test_rmse": "",
            "recovered": False,
        }
    s = score(model, law)
    return {
        "law": law_name,
        "seed": seed,
        "procedure": procedure,
        "chosen_terms": "+".join(model.names) or "(intercept only)",
        "exact_terms": s["exact_terms"],
        "false_terms": "" if s["false_terms"] is None else "+".join(s["false_terms"]),
        "abstained": False,
        "test_rmse": round(s["test_rmse"], 6),
        "recovered": s["recovered"],
    }


def _rows_for(law_name, seed, need_m1=True, need_m2=True):
    out = []
    data = {}
    if need_m1:
        m1, X1, y1 = _measure_run(law_name, "M1_fixed_search", seed)
        out.append(_row(law_name, seed, "M1_raw", m1))
        data["M1"] = (X1, y1)
    if need_m2:
        m2, X2, y2 = _measure_run(law_name, "M2_active_fixed_space", seed)
        out.append(_row(law_name, seed, "M2_raw", m2))
        data["M2"] = (X2, y2)
    return out, data


def _rule_rows(law_name, seed, data, margins, taus):
    out = []
    if "M2" in data:
        X, y = data["M2"]
        for m in margins:
            out.append(_row(law_name, seed, f"M2_margin_{m}", margin_select(X, y, m)))
    if "M1" in data:
        X, y = data["M1"]
        for t in taus:
            out.append(_row(law_name, seed, f"M1_abstain_{t:.2f}", abstain_select(X, y, t)))
    return out


def _fdr(rows, procedure):
    sub = [r for r in rows if r["procedure"] == procedure]
    return sum(1 for r in sub if r["false_terms"] != "") / len(sub)


def _abstain_rate(rows, procedure):
    sub = [r for r in rows if r["procedure"] == procedure]
    return sum(1 for r in sub if r["abstained"]) / len(sub)


def _exact_rate(rows, procedure):
    sub = [r for r in rows if r["procedure"] == procedure]
    return sum(1 for r in sub if r["exact_terms"]) / len(sub)


def calibrate():
    rows = []
    for seed in CAL_SEEDS:
        # null: margin rule (needs M2 data)
        out, data = _rows_for("null", seed, need_m1=False, need_m2=True)
        rows += out + _rule_rows("null", seed, data, MARGIN_GRID, [])
        # in_space: abstention threshold (needs M1 data)
        out, data = _rows_for("in_space", seed, need_m1=True, need_m2=False)
        rows += out + _rule_rows("in_space", seed, data, [], TAU_GRID)
    margin_star = None
    for m in MARGIN_GRID:
        if _fdr([r for r in rows if r["law"] == "null"], f"M2_margin_{m}") <= FDR_MAX:
            margin_star = m
            break
    tau_star = None
    for t in TAU_GRID:
        if (
            _abstain_rate([r for r in rows if r["law"] == "in_space"], f"M1_abstain_{t:.2f}")
            <= ABSTAIN_MAX_NULL_LIKE
        ):
            tau_star = t
            break
    cal = {
        "calibration_seeds": [CAL_SEEDS.start, CAL_SEEDS.stop - 1],
        "margin_grid": MARGIN_GRID,
        "margin_star": margin_star,
        "null_fdr_by_margin": {
            m: _fdr([r for r in rows if r["law"] == "null"], f"M2_margin_{m}") for m in MARGIN_GRID
        },
        "tau_grid": TAU_GRID,
        "tau_star": tau_star,
        "in_space_abstain_by_tau": {
            f"{t:.2f}": _abstain_rate(
                [r for r in rows if r["law"] == "in_space"], f"M1_abstain_{t:.2f}"
            )
            for t in TAU_GRID
        },
    }
    return cal, rows


def _bootstrap_ci(diffs, seed=0):
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(
        sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOT_RESAMPLES)
    )
    return means[int(0.025 * BOOT_RESAMPLES)], means[int(0.975 * BOOT_RESAMPLES)]


def test_run(cal):
    rows = []
    m_star = cal["margin_star"]
    t_star = cal["tau_star"]
    for law_name in EXP01_LAWS:
        for seed in TEST_SEEDS:
            out, data = _rows_for(law_name, seed)
            rows += out
            procs = []
            if m_star is not None:
                procs.append(("margin", m_star))
            if t_star is not None:
                procs.append(("abstain", t_star))
            for kind, val in procs:
                if kind == "margin":
                    rows.append(
                        _row(law_name, seed, f"M2_margin_{val}", margin_select(*data["M2"], val))
                    )
                else:
                    rows.append(
                        _row(
                            law_name,
                            seed,
                            f"M1_abstain_{val:.2f}",
                            abstain_select(*data["M1"], val),
                        )
                    )
    return rows


def verdicts(cal, rows):
    res = {}
    in_rows = [r for r in rows if r["law"] == "in_space"]
    null_rows = [r for r in rows if r["law"] == "null"]
    exp_rows = [r for r in rows if r["law"] == "needs_expansion"]

    # A: paired M2_raw - M1_raw exact recovery on in_space
    by_seed = {}
    for r in in_rows:
        by_seed.setdefault(r["seed"], {})[r["procedure"]] = int(bool(r["exact_terms"]))
    diffs = [by_seed[s]["M2_raw"] - by_seed[s]["M1_raw"] for s in TEST_SEEDS]
    lo, hi = _bootstrap_ci(diffs)
    mean = sum(diffs) / len(diffs)
    res["A_active_vs_fixed"] = {"mean_diff": mean, "ci95": [lo, hi], "supported": lo >= 0.2}
    # B: plain BIC null FDR
    res["B_plain_bic_null_fdr"] = {p: _fdr(null_rows, p) for p in ["M1_raw", "M2_raw"]}
    res["B_plain_bic_null_fdr"]["problem_confirmed"] = _fdr(null_rows, "M2_raw") > FDR_MAX
    # C: margin rule
    if cal["margin_star"] is not None:
        p = f"M2_margin_{cal['margin_star']}"
        fdr = _fdr(null_rows, p)
        rec = _exact_rate(in_rows, p)
        res["C_margin_rule"] = {
            "procedure": p,
            "null_fdr": fdr,
            "in_space_exact": rec,
            "supported": fdr <= FDR_MAX and rec >= RECOVERY_MIN,
        }
    else:
        res["C_margin_rule"] = {"status": "not calibrated"}
    # D: abstention
    if cal["tau_star"] is not None:
        p = f"M1_abstain_{cal['tau_star']:.2f}"
        res["D_abstention"] = {
            "procedure": p,
            "needs_expansion_abstain": _abstain_rate(exp_rows, p),
            "in_space_abstain": _abstain_rate(in_rows, p),
            "null_abstain": _abstain_rate(null_rows, p),
        }
        d = res["D_abstention"]
        d["supported"] = (
            d["needs_expansion_abstain"] >= ABSTAIN_MIN_EXPANSION
            and d["in_space_abstain"] <= ABSTAIN_MAX_NULL_LIKE
            and d["null_abstain"] <= ABSTAIN_MAX_NULL_LIKE
        )
    else:
        res["D_abstention"] = {"status": "not calibrated"}
    return res


def _write_rows(path, rows):
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(buf.getvalue())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/exp02")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    cal, cal_rows = calibrate()
    with open(os.path.join(a.out, "calibration.json"), "w", encoding="utf-8") as f:
        json.dump(cal, f, indent=2, sort_keys=True)
        f.write("\n")
    _write_rows(os.path.join(a.out, "calibration_runs.csv"), cal_rows)

    rows = test_run(cal)
    _write_rows(os.path.join(a.out, "test_runs.csv"), rows)
    v = verdicts(cal, rows)
    with open(os.path.join(a.out, "verdicts.json"), "w", encoding="utf-8") as f:
        json.dump(v, f, indent=2, sort_keys=True, default=float)
        f.write("\n")
    meta = {
        "config": {
            "budget": BUDGET,
            "sigma": SIGMA,
            "calibration_seeds": [1000, 1199],
            "test_seeds": [0, 199],
            "margin_grid": MARGIN_GRID,
            "tau_grid": TAU_GRID,
            "fdr_max": FDR_MAX,
            "recovery_min": RECOVERY_MIN,
        },
        "environment": provenance.environment_info(),
        "git": provenance.git_info(REPO_DIR),
        "code_sha256": provenance.code_hashes(),
        "artifacts": {
            name: provenance.sha256_file(os.path.join(a.out, name))
            for name in [
                "calibration.json",
                "calibration_runs.csv",
                "test_runs.csv",
                "verdicts.json",
            ]
        },
    }
    with open(os.path.join(a.out, "run_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"calibration": cal, "verdicts": v}, indent=2, sort_keys=True, default=float))


if __name__ == "__main__":
    main()
