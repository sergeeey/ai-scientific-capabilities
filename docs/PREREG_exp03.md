# Pre-registration: exp03 (sensitive endpoint for active design)

Written BEFORE any exp03 run. Frozen by this file. Thresholds are not changed after seeing results.

## 1. Why exp03
exp02 showed that `exact_terms` is at ceiling on `in_space` (M1 200/200, M2 200/200). The test of H-A (active design beats fixed design) therefore could not show an effect. exp03 uses a continuous endpoint that is not saturated, and first checks that the endpoint can see a known effect.

## 2. L0 (EstimandOps)
**Descriptive.** Performance of the same procedures under a continuous endpoint, on simulated laws with known truth. No causal claim. No LLM.

## 3. Primary endpoint and claim (frozen)
- **Endpoint:** test RMSE of the chosen model on the checker's fixed holdout grid (noise-free truth from the hidden law). Lower is better. Agents never see holdout labels.
- **Paired ratio per seed:** r_s = RMSE(M2, seed s) / RMSE(M1, seed s), law `in_space`, budget 30, test seeds 0–199.
- **Claim H-A':** active design reduces RMSE. Summary: median of r_s.
- **Minimum effect of interest (MCID, frozen):** median ratio ≤ 0.80 (a 20% reduction in RMSE).
- **Interval:** bootstrap 95% CI of the median ratio, 10,000 resamples, seed 0.

**Verdicts (frozen):**
- **Supported:** median ratio ≤ 0.80 AND CI upper bound < 1.00.
- **Refuted:** CI lower bound ≥ 0.80 (a 20% reduction is ruled out at this precision).
- **Inconclusive:** anything else. Reported as inconclusive, not as "no effect".

## 4. Sensitivity checks (calibration seeds 1000–1199 only)
exp03 test runs happen only if BOTH checks pass.

- **Positive control (the endpoint must see a known effect):** M1 at budget 60 vs M1 at budget 30, law `in_space`. Pass if median RMSE(b=60) / median RMSE(b=30) ≤ 0.80. More measurements must help, so a failure means the endpoint cannot see effects of this size.
- **Ceiling check:** fraction of seeds where RMSE(M2) = RMSE(M1) exactly, on `in_space`. Pass if < 5%.

If either check fails, exp03 is stopped and the reason is written to RESEARCH_LOG.md. No test seeds are used.

## 5. Negative control (reported, not a pass/fail gate)
Law `null`, test seeds 0–199, same ratio r_s. Expected: the bootstrap CI of the median ratio includes 1.00, i.e. no systematic RMSE improvement from active design when there is no law to find. If it excludes 1.00 in the improving direction, that is reported as a warning about the procedure, not as a finding about the law.

## 6. Procedures and budget
- M1 and M2: unchanged from exp01 (`agents.py` not modified).
- Budget 30 for both (shared, enforced by `Oracle`). The positive control uses M1 at 60 and 30.
- Same random streams as exp01 (`run.run_one`), so M1 and M2 at budget 30 reproduce exp01 on seeds 0–29.

## 7. Known limits (stated before results)
- Synthetic laws only. Expansion library is not used here (M1 and M2 only).
- RMSE measures fit on the holdout grid, not recovery of the exact term set. Exact recovery is reported as a secondary metric only.
- Isolation is soft (in-process). Not relevant to an LLM-free run, but it stays in the limits list.
- The MCID of 0.80 is a judgement, not derived from a cost model.
