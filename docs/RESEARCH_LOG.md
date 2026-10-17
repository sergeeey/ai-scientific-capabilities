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

## 2026-10-17 — Foundation v0.1
**Verdict: accepted with stated limits.** Not accepted as "isolation solved".

Probed before changing (not assumed from file layout):
- `Oracle._law` was a public-by-convention attribute: `oracle._law((1,2,0))` returned the law (3.0 for in_space). **Real leak, now closed** (law in a closure; test `test_guard_oracle_has_no_law_attribute`).
- Still reachable in-process: law through the `measure` closure; `importlib.import_module("aisci.hidden_laws")`. **Open residuals, documented and tested** (`test_residual_closure_exposes_law_in_process`, `test_residual_import_path_open_in_process`). A future change that silently closes or opens them will show up in the tests.

Changes:
- `Oracle` has a hard budget cap (`BudgetExceeded`). `calls` is now a property; the constructor stays backward compatible.
- `run_metadata.json`: run_id (hash of config), command, versions, git commit and dirty flag, code and artifact SHA-256.
- `evidence_ledger.jsonl`: 270 measurement entries (one per run, cite runs.csv hash) and derived entries (counts, medians, input ids). `docs/claims.json`: 7 claims; 5 supported or falsified with checks (C-05 checks the hash of the committed file), 2 unverified with no checks.
- New tests in `tests/test_foundation.py` (17 tests). Together with the 9 exp01 tests, all 26 pass locally.

Reproduction check:
- Current code produces `runs.csv` byte-identical to committed exp01 (sha256 `8731f8bc…2185`). Verified by hashing, and by `test_reproduces_committed_exp01_byte_for_byte`.
- `summary.md` gained a header line with run_id and the runs.csv hash. Its table is unchanged. This is an intentional format change, not a result change.

Deviations and bugs found during the work (recorded, not hidden):
1. **Hash bug, fixed.** `run.py` hashed the ledger text, but on Windows the text-mode write changes `\n` to `\r\n`, so the metadata hash did not match the file. Now the hash is taken from the written file. The first test run caught this.
2. **Regex test changed to AST.** `test_core.py::test_agents_cannot_import_hidden_laws` used a text regex. It failed on a docstring that mentions `hidden_laws`, which is not an import. Replaced by an AST import check, which is what the test is meant to verify. The guard itself was not weakened.
3. **Agent-side list fixed.** `ledger.py` imports `LAWS` to label entries, so it is runner-side, not agent-side. It is excluded from the agent-side list. An earlier draft included it by mistake.
4. The `recovered` endpoint and the exp01 verdicts were not changed. This work changes plumbing, not conclusions.

Not verified:
- Isolation against an adversarial or LLM agent. Requires a process boundary. Not built (out of Foundation scope, no LLM approved).
- Claim C-07 (external benchmarks) stays `unverified`.
- Reproducibility across machines and Python versions: only this machine (Python 3.13.2, Windows) was checked.

## 2026-10-17 — exp02 plan drafted (not started)
- `docs/EXP02_PLAN.md`: questions A–D, competing hypotheses, calibration seeds 1000–1199 disjoint from test seeds 0–199, refutation criteria written before any run. Exp02 does not start until its pre-registration is frozen.

## 2026-10-18 — Foundation review (narrow) and exp02 run
- **Review of ledger, claims and run.py:** independent reviewer, read-only, no defects found in claims-vs-ledger, derived-entry filters, or hash order. The earlier full review hit its turn limit and produced no report; this narrow one did finish. **Isolation was not in this review's scope** (it is covered by tests and documented as a soft residual).
- **Plumbing check:** exp02 `M2_raw` on in_space seeds 0–29 is identical to exp01 `M2` chosen terms (diff empty). The recording wrapper does not change the mechanism.
- **Calibration** (seeds 1000–1199, frozen values in `results/exp02/calibration.json`):
  - margin m = 10, the largest value in the grid. Null FDR by margin: 0→0.56, 2→0.35, 4→0.20, 6→0.105, 8→0.055, 10→0.03.
  - τ = 0.15. In-space abstention: τ=0.10→35%, τ≥0.15→0%.

**Test-seed verdicts** (seeds 0–199, `results/exp02/verdicts.json`):

| hyp | result | what it actually means |
|---|---|---|
| A active > fixed | mean diff 0.0, CI [0, 0]; by the pre-registered rule, **refuted** | Exact recovery on in_space is **at ceiling**: M1 200/200, M2 200/200. The endpoint has no room to show a difference, so this is not evidence that active design is useless. It is evidence that this endpoint cannot test A. |
| B plain BIC controls null FDR | M1 0.625, M2 0.565; **problem confirmed** | Consistent with exp01 (17/30, 18/30). |
| C margin rule | null FDR 0.015, in_space exact 1.00; **supported** | m=10 sits **on the grid edge**, so the true threshold may be higher. Nothing here shows what a larger margin costs on harder laws. |
| D abstention | needs_expansion 100%, in_space 0%, null 0%; **supported** | Works for this misfit only. The base-space approximation of tanh gives RMSE ≈0.24, just below the 0.25 used earlier. τ=0.15 separates it from the noise floor (≈0.10). A weaker misfit would not be separated. |

**Limits of this run:**
1. A cannot be tested with `exact_terms` on in_space. The next test needs a metric with headroom, for example test RMSE at a smaller budget, or a harder law. This is a design change and must be pre-registered before it runs.
2. C's margin grid ends at 10. A larger grid could give a different m. Extending it now, after seeing the result, would be exploratory.
3. exp02 artifacts are hashed in `results/exp02/run_metadata.json`, but **not yet in the evidence ledger** and not in `claims.json`. Under Foundation rules, exp02 conclusions are not yet traceable through the ledger. This is the next gap to close.
4. The default scenario is the exp01 laws, as I chose without your decision. The delay-differential scenario is not run.

**Narrow review of exp02 (commit f495ccd): LGTM, no P0 or P1.** Reviewer confirmed: calibration uses only seeds 1000–1199; margin and tau are the first grid values meeting the limit; verdicts use test seeds only for reporting; test-seed data does not choose thresholds. Its P2 notes and my response:
- **Calibration hash not recorded (PREREG section 3 requires it).** Recorded now: `results/exp02/calibration.json` sha256 `639dd3d4b915b2413753e3d5f0a3781e95e73869eb20ddffa14e443d43c8506f`. Re-running exp02 reproduced it.
- **Wording mismatch on A.** PREREG says "CI lower bound > 0.2"; `verdicts()` uses `>= 0.2`. The outcome is the same (bound is 0.0), so the PREREG text is not edited after seeing results. The mismatch stays on record here.
- **B checks only M2 in the verdict dict.** M1 (0.625) is also above 5%. The outcome is the same and both values are in the table above.
- **Thresholds are passed in memory, not reloaded from calibration.json.** A standalone rerun of the test phase would recalibrate, which gives the same values here. Left as is, recorded as a limit.

## 2026-10-18 — exp03: continuous endpoint for hypothesis A (pre-registered, run)
Protocol: `docs/PREREG_exp03.md` (written before any run). Runner: `src/aisci/exp03.py`, using `run_one` unchanged.

**Sensitivity checks on calibration seeds 1000–1199 (passed, gate for the test run):**
- Positive control: median RMSE of M1 at budget 60 / budget 30 = **0.721** (pass if ≤ 0.80). Doubling the budget gives about 28% lower RMSE, so the endpoint sees effects of this size.
- Ceiling check: RMSE of M1 and M2 exactly equal on 0% of seeds (pass if < 5%). Unlike `exact_terms`, RMSE is not saturated.

**Test run, seeds 0–199 (frozen rule):**
- Law `in_space`: median paired ratio RMSE(M2)/RMSE(M1) = **0.767**, bootstrap 95% CI [0.698, 0.843]. Verdict under the frozen rule: **supported** (median ≤ 0.80 and CI upper < 1.00).
- Negative control, law `null` (reported, not a gate): median ratio **0.917**, CI [0.712, 1.000].

**Warning, which weakens the in_space verdict:** on the null law, where there is nothing to discover, M2 still gives about 8% lower RMSE (CI reaches 1.00). So the RMSE endpoint rewards M2 even without a law. A plausible cause is that M2's design picks points that pull fitted models toward zero. That would make it a property of the metric and procedure, not evidence of discovering the law. The in_space result must not be read as proof that active design finds laws better. It shows only that M2's fitted models are closer to the true function on the holdout grid than M1's, and the null control suggests this may not be specific to real structure.

**What this changes:**
1. Hypothesis A now has a sensitive endpoint, and the calibration shows the endpoint is not saturated.
2. The next test must separate "closer to truth" from "closer to zero" on the null law, for example a null-law baseline that always returns intercept-only (its RMSE is set by the intercept). Pre-register it before running.
3. Like exp02, exp03 artifacts are hashed in `results/exp03/run_metadata.json` but are **not yet in the evidence ledger**. Foundation traceability does not yet cover exp02 or exp03.

**Decisions applied from the external review:** exp03 chosen as the next step (not the delay-differential scenario); isolation for LLM stays a prerequisite before any API call; `c49524a` on master left unchanged.

## Open decisions for the user
- The project's research question (LLM vs algorithm) needs an LLM. Approval is needed before any paid API is used, and the task says not to use one without approval. Until then the LLM part is NOT-VERIFIED.
- Whether to keep the folder as a standalone repo or move it into a larger workspace.
