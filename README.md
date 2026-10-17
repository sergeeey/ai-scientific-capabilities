# AI Scientific Capabilities — synthetic testbed

Question: can an LLM find discrepancies in known scientific explanations, build new mathematical representations, and find checkable regularities — or do its results come from algorithmic search and compute budget?

**Status (exp01):** the first testbed runs locally. It compares three *algorithmic stand-ins* for the candidate mechanisms on synthetic laws. **No LLM is in the loop yet, so the research question itself is NOT tested.**

## Honest state of the project
- The folder was **empty** when work started: no README, no docs, no git history, no earlier experiments. The task assumed an existing project; there was nothing to continue, so this is a fresh start inside the existing folder.
- Nothing here is evidence about LLMs. Every number is `VERIFIED-SYNTHETIC`.
- No paid API was used or requested.

## Layout
```
src/aisci/hidden_laws.py   hidden ground-truth laws (runner/checker only)
src/aisci/environment.py   Oracle: noisy measurement of a law; no access to the law
src/aisci/features.py      agent-side hypothesis spaces: BASE_LIB (H0), EXPANSION_LIB, FULL_LIB
src/aisci/fit.py           stdlib least squares, subset search, BIC
src/aisci/agents.py        the three mechanisms (M1, M2, M3)
src/aisci/checker.py       independent scorer: fixed test grid, uses the true law
src/aisci/provenance.py    config/versions/git/SHA-256 helpers (stdlib)
src/aisci/ledger.py        Evidence Ledger entries: measurement and derived (runner-side)
src/aisci/run.py           runner: runs.csv, summary.md, run_metadata.json, evidence_ledger.jsonl
tests/test_core.py         exp01 checks: fit, scoring, budget, scenario control, reproducibility
tests/test_foundation.py  Foundation v0.1: metadata, hard budget cap, byte-identical reproduction,
                          isolation guards and documented residuals, ledger and claim traceability
docs/PREREG_exp01.md       pre-registration (written before the first run)
docs/claims.json           claims with status; each check resolves to a ledger entry
docs/ROADMAP.md            ten questions, three stages, target architecture
docs/RESEARCH_LOG.md       decisions, deviations, falsified predictions
docs/EXP02_PLAN.md         draft plan for exp02 (not started)
results/                   exp01 artifacts: runs.csv, summary.md, run_metadata.json, evidence_ledger.jsonl
```

## Foundation v0.1 — what is and is not done
Done and tested:
- Every run writes `run_metadata.json`: config, seeds, budget, algorithm names, Python and pytest versions, git commit and dirty state for `src/tests/docs`, SHA-256 of each code file and each output artifact.
- `Oracle` has a **hard budget cap**: the 31st call to a 30-call budget raises `BudgetExceeded`.
- `runs.csv` from the current code is **byte-identical** to the committed exp01 file (sha256 `8731f8bc…2185`). exp01 is reproduced.
- `evidence_ledger.jsonl` has measurement entries (one per run, citing the runs.csv hash) and derived entries (counts and medians, listing their input entry ids). `docs/claims.json` cites ledger entries by law, mechanism and metric; tests check each one.
- Claims that are not verified are labelled `unverified` with no checks.

**Isolation is soft, and this is a real limit.** Found by probing the code before changing it:
- Fixed: the old `Oracle._law` attribute gave the hidden law to any caller. The law now sits in a closure, and `oracle._law` does not exist (`tests/test_foundation.py::test_guard_oracle_has_no_law_attribute`).
- Still open in-process (documented residuals, tested so they cannot change silently): the law can be read from the `measure` closure, and any code can `importlib.import_module("aisci.hidden_laws")`. The holdout labels are reachable the same way. Closing these needs a process boundary. This is enough for synthetic algorithms. It is **not enough for an LLM agent**, which must run in a separate process before exp02 uses any model.

Not done: exp02, any LLM run, the cost and human-effort parts of Q10, and cross-run validation of older results (none exist).

## The three mechanisms (all get the same budget of 30 measurements)
| id | mechanism | what it does |
|---|---|---|
| M1 | search in a fixed hypothesis space | random design, BIC choice over H0 (≤2 terms + intercept). Also the baseline. |
| M2 | M1 + active choice of experiments | after 6 random points, measures where the top BIC models disagree most |
| M3 | M2 + expansion | if H0 fits badly after ≥8 points (RMSE > 0.25), switches to the pre-specified FULL_LIB |

**Limit:** FULL_LIB is fixed in advance. M3 is search in a larger fixed space, not open-ended invention.

## Scenarios
- `in_space`: y = 1.5·x1·x2 − 0.8·x3² (in H0)
- `needs_expansion`: y = 2·tanh(x1)·x2 + 0.5·x3 (not in H0)
- `null`: y = 0 (only noise; any selected term is a false discovery)

## Reproduce
```bash
cd "<project folder>"
set PYTHONPATH=src
python -m pytest tests -q
python -m aisci.run --seeds 30 --budget 30 --sigma 0.1 --out results
```
(Use `PYTHONPATH=src` in bash: `PYTHONPATH=src python -m aisci.run ...`.) Running the command again rewrites `results/`. `runs.csv` must keep sha256 `8731f8bc…2185`. `summary.md` and `evidence_ledger.jsonl` are deterministic from the same inputs. `run_metadata.json` changes with the git commit and the dirty flag, so it is not byte-compared.
Seeds are fixed (0..29). Noise and design streams are seeded per run.

## Results (exp01, 30 seeds, sigma 0.1, budget 30)
See `results/summary.md` for the full table. Key findings:
- `needs_expansion`: M1 and M2 never succeed (0/30). M3 chooses the right terms in 30/30 runs, and expansion fires in 30/30. This follows from the design, because the expansion library was built to contain the answer.
- `in_space`: M1 27/30, M2 29/30, M3 28/30 recovered. Exact term sets 30/30 for all three. The difference is far below the pre-registered MCID (0.2), so **no evidence that active design helps here**.
- `null`: spurious terms were selected in 17/30 (M1), 18/30 (M2) and 19/30 (M3) runs. **This falsifies pre-registered prediction P3** (expected to be small).
- The `recovered` endpoint (RMSE < 0.05) is too strict at this noise level: some runs have the exact correct terms but RMSE 0.05–0.07. Read `exact_terms` as the primary endpoint.

Details and deviations: `docs/RESEARCH_LOG.md`.

## Roadmap
Full text of the ten questions, the target architecture, and the three stages (Foundation → Scientific Discovery → Production Validation): `docs/ROADMAP.md`.

Coverage after exp01:
- Partly covered: Q3 (fixed expansion only), Q4 (algorithmic ablation, no LLM), Q5 (active design, no stopping rule), Q9 (results and log, no ledger or checksums), Q10 (baseline at equal budget, no cost model).
- Not started: Q1, Q2, Q6, Q7, Q8.

Next decisive experiment: `docs/RESEARCH_LOG.md`, section "Next decisive experiment" (exp02, proposal, not run).
