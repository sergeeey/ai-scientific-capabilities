# Pre-registration: exp02 (default scenario = exp01 laws)

Written BEFORE any exp02 run. Thresholds below are frozen by this file. A value is set only by the calibration procedure in section 3, on calibration seeds. Changing a rule or threshold after test seeds are seen makes the change exploratory and must be recorded in RESEARCH_LOG.md.

## 1. L0 (EstimandOps)
**Descriptive.** Performance of selection rules on simulated laws with known truth at a fixed budget. No causal claim. No LLM.

## 2. Hypotheses
| id | question | H1 (supported if...) | H0 (competing) |
|---|---|---|---|
| A | Does active design (M2) recover more than fixed design (M1)? | paired M2−M1 ≥ MCID 0.2 (bootstrap 95% CI lower bound > 0.2 on test seeds) | difference < MCID |
| B | Does plain BIC (M1, M2) control false discoveries? | null false-term rate ≤ 5% | rate > 5% |
| C | Does a margin rule (M2+margin) control false discoveries while keeping recovery? | null false-term rate ≤ 5% **and** in_space exact recovery ≥ 80% | either condition fails |
| D | Can the agent abstain (`UNEXPLAINED`) when the base space is insufficient? | base-only on needs_expansion: abstain ≥ 90%; on in_space and null: abstain ≤ 5% | any condition fails |

Refutation: H1 of A is refuted if the CI lies entirely below 0.2. B is "problem confirmed" if the null rate > 5%. C is refuted if its null rate > 5% or in_space recovery < 80%. D is refuted if any abstention condition fails.

## 3. Seeds and calibration (disjoint by design)
- **Calibration seeds 1000–1199**: used only to choose the margin m (rule C) and the abstention threshold τ (rule D).
- **Test seeds 0–199**: every reported number.
- Holdout: the checker's fixed test grid (seed 12345), noise-free labels from the hidden law. Agents never receive these labels.

Calibration procedure (fixed in advance):
- m is the smallest value in {0, 2, 4, 6, 8, 10} for which M2+margin on the **null** law, calibration seeds, gives a false-term rate ≤ 5%.
- τ is the smallest value in {0.10, 0.15, 0.20, 0.25, 0.30} for which base-only search on **in_space**, calibration seeds, abstains in ≤ 5% of runs.
- If no value in the grid satisfies the condition, that rule is reported as "not calibrated" and is not run on test seeds.
- Calibration output is written to `results/exp02/calibration.json` with the SHA-256 of that file recorded in RESEARCH_LOG.md.

## 4. Budget and procedures
- Budget: 30 measurements per run, same for all procedures (enforced by `Oracle`).
- M1 and M2: unchanged from exp01 (`agents.py` is not modified).
- **M2+margin:** the M2 procedure, then select the best BIC model only if it beats the intercept-only BIC by at least m. Otherwise return the intercept only.
- **Base-only abstention:** the M1 procedure, then return `UNEXPLAINED` if the best model's in-sample RMSE > τ.
- Baseline reference: M1.
- Reference upper bound: FULL_LIB exhaustive search with random design (reported, not compared against H1–H2 in this experiment).

## 5. Metrics
- Recovery: `exact_terms` (primary, per exp01 deviation note).
- False discovery: any non-intercept term on `null`.
- Abstention: fraction of runs returning `UNEXPLAINED`.
- Paired comparisons by seed. Bootstrap 95% CI over seeds (10,000 resamples, seed fixed at 0).

## 6. Known limits (stated before results)
- Synthetic only. Nothing transfers to real science.
- Expansion library (EXPANSION_LIB) is pre-specified and contains the true operator. Hypothesis D tests abstention, not the discovery of a new operator.
- Isolation is soft (in-process). See README.
- Power at 30 measurements per run was low in exp01. The 200 test seeds here address this for the paired A comparison only; no power claim is made for other comparisons.

## 7. Scenario choice
Default: exp01 laws. The delay-differential scenario (`ẋ = −a·x(t) + b·x(t−τ)`) is not part of this pre-registration. It needs its own pre-registration after the Foundation review and the user's decision.
