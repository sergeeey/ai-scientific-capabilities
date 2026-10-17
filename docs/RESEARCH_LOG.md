# Research log — AI Scientific Capabilities

Evidence markers: VERIFIED-SYNTHETIC (run in this repo on simulated data), MODEL-CLAIM (claim about an LLM, not tested here), NOT-VERIFIED (no evidence yet).

## 2026-10-17 — start
- **[VERIFIED]** The folder `А - 5 ai-scientific-capabilities` was empty: no git, no README, no docs, no prior experiments. There were no earlier reports to check or reuse. The "existing project" assumption in the task did not hold.
- **Decision:** build the smallest testbed inside this folder (not a new repo elsewhere). Stdlib only, to avoid new dependencies.
- **L0 (EstimandOps):** Descriptive. The question is how the procedures perform on simulated data. No causal or LLM claim.
- **Decision:** the three candidate mechanisms are deterministic algorithms (M1, M2, M3). No model is queried, because the task bans paid APIs without approval and there is no approved LLM endpoint.

## 2026-10-17 — pre-registration
- Criteria written in `docs/PREREG_exp01.md` before the first run (predictions P1–P3).

## 2026-10-17 — run exp01
Command: `python -m aisci.run --seeds 30 --budget 30 --sigma 0.1 --out results`. Output: `results/runs.csv`, `results/summary.md`. Tests: 9 passed.

| law | mechanism | recovered | exact terms | median test RMSE | expansions |
|---|---|---|---|---|---|
| in_space | M1 | 27/30 | 30/30 | 0.0323 | 0/30 |
| in_space | M2 | 29/30 | 30/30 | 0.0213 | 0/30 |
| in_space | M3 | 28/30 | 30/30 | 0.0196 | 0/30 |
| needs_expansion | M1 | 0/30 | 0/30 | 0.3375 | 0/30 |
| needs_expansion | M2 | 0/30 | 0/30 | 0.3472 | 0/30 |
| needs_expansion | M3 | 29/30 | 30/30 | 0.0259 | 30/30 |
| null | M1 | — | — | 0.0407 | 0/30 (17/30 runs with a false term) |
| null | M2 | — | — | 0.0283 | 0/30 (18/30) |
| null | M3 | — | — | 0.0276 | 0/30 (19/30) |

### Verdicts against the pre-registration
- **P1 (M2 ≥ M1 on in_space): supported in direction, not meaningful.** Paired by seed, M2 wins 2 and loses 0 on `recovered`. The difference (2/30 ≈ 0.07) is under the MCID of 0.2. Exact term sets tie at 30/30. **No evidence of an advantage for active design.**
- **P2 (M3 recovers needs_expansion, M1/M2 cannot): supported.** M1 and M2 fail in 30/30. M3 expands in 30/30 and finds exact terms in 30/30. The control test `test_base_space_cannot_fit_expansion_law` confirms the scenario is out of H0. **Caveat:** the expansion library contains the true operator (tanh times x_i) by construction. This shows the mechanism works when the right operator is already in the library. It does not show open-ended discovery.
- **P3 (small false discovery on null): FALSIFIED.** 17–19 of 30 null runs selected at least one spurious term, for all three mechanisms. Mostly single small terms (e.g. x1^2, sin(x3)). With 78 candidate pairs and BIC at n=30, BIC does not prevent spurious picks at this noise level. This is a real finding about the selection rule, not a bug (tests pass, budget is respected). Reported as-is, not re-tuned.

### Deviations and post-hoc observations (not part of the pre-registered criteria)
1. **The `recovered` endpoint is too strict.** Some runs have exact correct terms and test RMSE 0.05–0.07 (in_space M1 seeds 8, 20, 28; M2 seed 8; M3 seeds 8, 28; needs_expansion M3 seed 8). The RMSE threshold of 0.05 is below the coefficient-estimation error at sigma 0.1 and n=30. **Primary endpoint from now on: `exact_terms`.** This was decided after seeing the data, so it is exploratory.
2. **Null-law rows in `summary.md` show no `recovered` figure in this log.** The table in `results/summary.md` shows it. On the null law, `recovered` is not a useful endpoint: a near-zero model passes the RMSE threshold even when it selected a spurious term. Use `false_terms` for null.
3. **Expansion trigger** (RMSE > 0.25) was not tuned. It fired 0/30 on in_space and null, 30/30 on needs_expansion. That is consistent with the design, but it is one setting, not a sweep.

## What this shows (VERIFIED-SYNTHETIC)
- In this synthetic setup, the **main effect** comes from having the right library term (H0 vs expansion). Active design made no measurable difference at 30 seeds.
- BIC-based selection over subsets of 12–21 terms selects spurious terms on pure noise in over half the runs. Any future claim about "discovery" from a search like this needs a false-discovery control.

## Not verified / NOT-VERIFIED
- Anything about LLMs (MODEL-CLAIM): no model was queried.
- Robustness to sigma, budget, domain, law family: not run.
- Whether active design helps at larger budget or with more seeds: not tested (power too low at 30 seeds).

## Next decisive experiment (proposal, not run)
**exp02: false-discovery control and power for the active-design claim.**
1. Use 200 seeds per cell (paired) for in_space and null. Run only M1 and M2, since M3 is not needed for this question.
2. Add a selection rule with a false-discovery control (for example, require the best model to beat the intercept-only model by a fixed BIC margin, with the margin set on null runs before testing on the in_space law). Pre-register the margin first.
3. Endpoint: `exact_terms`. Report the paired wins/losses of M2 vs M1 and the null false-term rate under each rule.
- **Would falsify** "active design helps": M2 vs M1 paired difference < MCID (0.2) with CI including 0.
- **Would falsify** "BIC is fine for discovery": null false-term rate stays above 5% after the control.

## 2026-10-17 — roadmap intake (document, not an experiment)
- A strategic document with ten questions, a target architecture (five blocks) and three stages was added as `docs/ROADMAP.md`. This is a plan, not a result: no new evidence was produced.
- Mapping: exp01 partly covers Q3, Q4, Q5, Q9, Q10. Q1, Q2, Q6, Q7, Q8 are not started.
- The document cites external work (FIRE-Bench, SciAgentArena, "Into the Unknown", figures 135 and 114, date 13.10.2026). **These are [UNKNOWN]: not opened, not verified.** They are listed in `ROADMAP.md` under "to verify" and must not be used as facts until checked against the primary sources.
- No code was changed in this step.

## Open decisions for the user
- The project's research question (LLM vs algorithm) needs an LLM. Approval is needed before any paid API is used, and the task says not to use one without approval. Until then the LLM part is NOT-VERIFIED.
- Whether to keep the folder as a standalone repo or move it into a larger workspace.
