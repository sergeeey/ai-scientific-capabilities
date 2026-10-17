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
src/aisci/run.py           runner, writes results/runs.csv and results/summary.md
tests/test_core.py         9 checks: fit, isolation, budget, scoring, scenario control, reproducibility
docs/PREREG_exp01.md       pre-registration (written before the first run)
docs/RESEARCH_LOG.md       decisions, deviations, falsified predictions, next experiment
results/                   outputs of the reported run
```

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
(Use `PYTHONPATH=src` in bash: `PYTHONPATH=src python -m aisci.run ...`.)
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
