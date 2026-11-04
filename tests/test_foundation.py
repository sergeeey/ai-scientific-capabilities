"""Foundation v0.1 checks: metadata, budgets, reproducibility, isolation, ledger traceability.

Isolation tests are split into two kinds:
  * guards: paths that MUST be closed (attribute access, module imports by agent-side code)
  * documented residuals: paths that stay open in-process; the test records them so the
    limit is visible, and fails if someone silently changes the design
"""

import ast
import hashlib
import importlib
import json
import os

import pytest

from aisci import checker, ledger, provenance
from aisci.agents import MECHANISMS
from aisci.environment import BudgetExceeded, Oracle
from aisci.exp_config import EXP01_LAWS
from aisci.hidden_laws import LAWS
from aisci.run import config_for, main, run_all, runs_csv_text

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS = os.path.join(ROOT, "results")
SRC = os.path.join(ROOT, "src", "aisci")
# ledger.py and provenance.py are runner-side (ledger imports LAWS to label entries).
AGENT_SIDE = ["agents.py", "environment.py", "features.py", "fit.py"]
COMMITTED_RUNS_SHA = "8731f8bc8232d099dc5bf57b73bf7976b57236373c90042e25c08fe347a12185"


def _sha(path):
    return provenance.sha256_file(path)


# ---------- budgets ----------


def test_oracle_budget_is_a_hard_cap():
    o = Oracle(lambda x: 1.0, sigma=0.0, seed=0, budget=3)
    for _ in range(3):
        o.measure((0.0, 0.0, 0.0))
    with pytest.raises(BudgetExceeded):
        o.measure((0.0, 0.0, 0.0))
    assert o.calls == 3


def test_every_mechanism_spends_exactly_the_shared_budget():
    rows = run_all(seeds=2, budget=20, sigma=0.1)
    assert len(rows) == len(EXP01_LAWS) * len(MECHANISMS) * 2
    assert {r["n_calls"] for r in rows} == {20}


# ---------- metadata ----------


def test_run_metadata_has_required_fields(tmp_path):
    main(["--seeds", "2", "--budget", "12", "--sigma", "0.1", "--out", str(tmp_path)])
    meta = json.loads((tmp_path / "run_metadata.json").read_text(encoding="utf-8"))
    for key in [
        "run_id",
        "command",
        "config",
        "algorithms",
        "baseline",
        "environment",
        "git",
        "code_sha256",
        "artifacts",
    ]:
        assert key in meta, key
    assert meta["config"]["budget"] == 12
    assert meta["config"]["seeds"] == 2
    assert meta["baseline"] == "M1_fixed_search"
    assert meta["environment"]["python"]
    assert "src/aisci/run.py" in meta["code_sha256"]
    assert meta["environment"]["third_party_dependencies"] == []


def test_artifact_hashes_in_metadata_match_files(tmp_path):
    main(["--seeds", "2", "--budget", "12", "--sigma", "0.1", "--out", str(tmp_path)])
    meta = json.loads((tmp_path / "run_metadata.json").read_text(encoding="utf-8"))
    for name, info in meta["artifacts"].items():
        assert _sha(tmp_path / name) == info["sha256"], name


def test_run_id_depends_on_config_only():
    a = provenance.sha256_text(provenance.canonical_json(config_for(30, 30, 0.1)))[:12]
    b = provenance.sha256_text(provenance.canonical_json(config_for(30, 30, 0.1)))[:12]
    c = provenance.sha256_text(provenance.canonical_json(config_for(30, 31, 0.1)))[:12]
    assert a == b and a != c


# ---------- reproducibility ----------


def test_reproduces_committed_exp01_byte_for_byte():
    text = runs_csv_text(run_all(seeds=30, budget=30, sigma=0.1))
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert digest == COMMITTED_RUNS_SHA
    assert _sha(os.path.join(RESULTS, "runs.csv")) == COMMITTED_RUNS_SHA


def test_same_seed_same_rows():
    a = run_all(seeds=3, budget=15, sigma=0.1)
    b = run_all(seeds=3, budget=15, sigma=0.1)
    assert a == b


# ---------- isolation ----------


def test_guard_oracle_has_no_law_attribute():
    o = Oracle(LAWS["in_space"].fn, sigma=0.0, seed=0)
    assert not hasattr(o, "_law")
    assert all(v is not LAWS["in_space"].fn for v in vars(o).values())


def test_guard_agent_side_modules_do_not_import_hidden_or_holdout():
    forbidden = {"hidden_laws", "checker", "run"}
    for fname in AGENT_SIDE:
        with open(os.path.join(SRC, fname), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[-1] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module.split(".")[-1])
        assert not (mods & forbidden), (fname, mods & forbidden)


def test_guard_checker_holdout_is_private():
    assert not hasattr(checker, "holdout_labels")
    assert hasattr(checker, "_GRID")  # inputs only; labels require the law


def test_residual_closure_exposes_law_in_process():
    # DOCUMENTED RESIDUAL: the law is reachable through the measure closure.
    # Closing this needs a process boundary, which is out of Foundation v0.1 scope.
    o = Oracle(LAWS["in_space"].fn, sigma=0.0, seed=0)
    closure_values = [c.cell_contents for c in vars(o)["_measure"].__closure__]
    assert LAWS["in_space"].fn in closure_values


def test_residual_import_path_open_in_process():
    # DOCUMENTED RESIDUAL: nothing in-process stops an explicit import of the hidden module.
    mod = importlib.import_module("aisci.hidden_laws")
    assert "in_space" in mod.LAWS


def test_checker_scores_true_law_as_exact_recovery():
    law = LAWS["in_space"]

    class TrueModel:
        names = ("x1*x2", "x3^2")

        def predict(self, x):
            return law.fn(x)

    s = checker.score(TrueModel(), law)
    assert s["exact_terms"] and s["recovered"]


# ---------- ledger and claims ----------


def _ledger():
    return ledger.load(os.path.join(RESULTS, "evidence_ledger.jsonl"))


def test_ledger_measurements_cite_the_current_runs_file():
    entries = [e for e in _ledger() if e["type"] == "measurement"]
    assert len(entries) == len(EXP01_LAWS) * len(MECHANISMS) * 30
    shas = {e["source_sha256"] for e in entries}
    assert shas == {_sha(os.path.join(RESULTS, "runs.csv"))}


def test_ledger_measurements_respect_budget():
    for e in _ledger():
        if e["type"] == "measurement":
            assert e["n_calls"] == e["budget"] == 30


def test_ledger_derived_entries_recompute_from_their_inputs():
    by_id = {e["id"]: e for e in _ledger()}
    for e in by_id.values():
        if e["type"] != "derived":
            continue
        inputs = [by_id[i] for i in e["inputs"]]
        assert all(i["type"] == "measurement" for i in inputs)
        assert all(i["law"] == e["law"] and i["mechanism"] == e["mechanism"] for i in inputs)
        if e["metric"] == "recovered_count":
            assert e["value"] == sum(bool(i["recovered"]) for i in inputs)
        if e["metric"] == "exact_terms_count":
            assert e["value"] == sum(bool(i["exact_terms"]) for i in inputs)


def test_claims_resolve_to_matching_ledger_entries():
    with open(os.path.join(ROOT, "docs", "claims.json"), encoding="utf-8") as f:
        claims = json.load(f)["claims"]
    by_id = {e["id"]: e for e in _ledger()}
    statuses = {"supported", "falsified", "unverified"}
    for c in claims:
        assert c["status"] in statuses, c["id"]
        if c["status"] == "unverified":
            assert c["checks"] == [], c["id"]
            continue
        assert c["checks"], f"{c['id']} is {c['status']} but cites nothing"
        for chk in c["checks"]:
            e = by_id[chk["id"]]
            if "metric" in chk:
                assert e["type"] == "derived"
                assert (e["law"], e["mechanism"], e["metric"]) == (
                    chk["law"],
                    chk["mechanism"],
                    chk["metric"],
                ), c["id"]
                assert e["value"] == chk["value"], c["id"]
            else:
                assert e[chk["field"]] == chk["value"], c["id"]
