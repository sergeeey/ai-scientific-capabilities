# Pre-registration: exp04 (delay-differential world, history-controlled oracle)

Written BEFORE the calibration run. Frozen by this file. Any change after results are seen is recorded as exploratory in RESEARCH_LOG.md.

## 1. L0 (EstimandOps)
**Descriptive.** How three algorithmic conditions behave on simulated delay worlds with known truth, at a fixed budget. No causal claim about any real system. No LLM in this experiment.

## 2. Question and competing hypotheses
Can an agent that only has memoryless models detect that its base space is insufficient (history matters), and can an expansion to the delay family recover the true delay?

| id | hypothesis | supported if | refuted if |
|---|---|---|---|
| H-A3 | With expansion (A3) the delay is named correctly | A3 correct rate on delay worlds >= 0.5 | < 0.5 |
| H-D | Without expansion (A1, A2) the agent abstains on delay worlds | A1 and A2 abstain rate on delay worlds >= 0.9 | either < 0.9 |
| H-N | No false delay on control worlds (A3) | false-delay rate on controls <= 0.10 | > 0.10 |

Null (H0) for H-A3 and H-D: the outcome is at chance or the agent names a delay without support.

## 3. Worlds (hidden; stored in the vault, pinned by SHA-256)
- Delay worlds `w01`..`w08`: `x' = -a x + b x(t - tau)`, tau in {0.4, 0.6, 0.8, 1.0}, 0 < b.
- Control worlds: `c01`, `c02` memoryless; `c03` weak (small delay effect); `c04` zero. Their parameter values are in the vault only (not stated here, so the controls stay blind).
- Worlds were written into the vault before this file was frozen. The protocol does not refer to their values; the agent never sees them.

## 4. Oracle, budget, conditions (fixed)
- Agent chooses a history: 6 knots on t in [-1, 0]. Oracle returns 61 noisy samples of x on t in [0, 3] with step 0.05, sigma = 0.01.
- Budget: 30 experiments per run, enforced by `DelayOracle`.
- A1: 30 random histories; base (memoryless) fit; abstain on misfit.
- A2: A1 with 6 random histories, then each next history maximises disagreement between the two base candidates (linear, cubic).
- A3: A2, plus expansion to the delay family once the base misfits and at least 8 experiments are in. Delay candidates tau in {0.4, 0.6, 0.8, 1.0}.
- Misfit / acceptance threshold: `deriv_tol(n) = DERIV_SIGMA * sqrt(1 + 3*sqrt(2/n))` with `DERIV_SIGMA = sigma*sqrt(2)/(2*0.05)`. Noise-derived, not tuned.
- Identifiability check before any delay is named: the two best delay candidates must be separable by some admissible history (max trajectory gap > 3*sigma).

## 5. Calibration gate (seeds 1000–1004; must pass before the test run)
- G1 positive control: identifiability of w01's truth with tau = 0.4 vs tau = 0.8 is IDENTIFIABLE.
- G1 negative control: identifiability of the weak control under two rival delays is NON_IDENTIFIABLE.
- G2: A3 correct rate on delay worlds >= 0.5.
- G3: A3 false-delay rate on control worlds <= 0.10.
If any gate fails, the test run does not start, and the failure is written to RESEARCH_LOG.md.

## 6. Test run (seeds 0–9; reported)
- All 12 worlds x 3 conditions x 10 seeds = 360 runs.
- Holdout: 10 fresh histories per run, noise-free truth. Metric: RMSE of the named model against truth (no model => no RMSE).
- Report per condition: correct rate, abstain rate, false-delay rate, median holdout RMSE on correct delays.

## 7. Known limits (stated before results)
- Ten seeds and eight delay worlds: descriptive only. No power claim.
- Synthetic, single family (linear in x and x(t - tau)). Not a test of open-ended discovery; the delay family is pre-specified (expansion).
- Euler integration with step 0.01; derivative estimates from samples with step 0.05 have a residual bias of about 2% on coefficients (measured, zero-noise).
- No LLM. Isolation is in-process only (as in exp01–exp03).
