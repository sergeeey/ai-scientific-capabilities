# exp02 plan — false discoveries, insufficiency detection, abstention calibration

Status: **plan only, not started.** exp02 starts after Foundation v0.1 is accepted. Thresholds in this file must be frozen in `PREREG_exp02.md` before any exp02 run; this file is a draft of that pre-registration.

## L0 (EstimandOps)
**Descriptive.** The question is how the procedures behave on simulated laws with known truth at a fixed budget. No causal claim. No LLM.

## Questions and competing hypotheses
| id | question | H1 (the thing we want to support) | H0 (what it competes with) |
|---|---|---|---|
| A | Does active design (M2) recover the true terms more often than fixed design (M1)? | M2 − M1 ≥ MCID (0.2) in paired recovery | difference < MCID; exp01 saw +2/30 |
| B | Does plain BIC selection control false discoveries? | null false-term rate ≤ 5% | rate > 5%; exp01 saw 57–63% |
| C | Can a margin rule control false discoveries and keep recovery? | null false-term rate ≤ 5% **and** in_space exact recovery ≥ 80% | margin rule cuts recovery below 80% or does not control FDR |
| D | Can the agent detect that its base space is insufficient and abstain? | on needs_expansion with base-only search, abstain ≥ 90%; on in_space and null, abstain ≤ 5% | abstention cannot separate the cases |

## Laws and seeds (disjoint by design)
- Laws: `in_space`, `needs_expansion`, `null` (unchanged from exp01).
- **Calibration seeds** 1000–1199: used only to set the margin (C) and the abstention threshold (D). Nothing else.
- **Test seeds** 0–199: each reported number. Never used for tuning.
- Holdout grid: `checker` fixed grid (seed 12345), noise-free labels from the hidden law. The agent never gets labels from it.

## Budget
Shared, fixed per comparison: 30 measurements (main). Optional sweep 30/60 is reported as exploratory only.

## Procedures
- M1 fixed search; M2 active design (exp01 definitions, not modified).
- **M2+margin (rule C):** pick the best BIC model only if it beats the intercept-only model by margin m (m set on calibration seeds for the null law to give FDR ≤ 5%).
- **Abstention (rule D):** report `UNEXPLAINED` if the best model's in-sample RMSE > τ and no expansion is available. τ set on calibration seeds for `in_space` (≤ 5% abstain).
- Baselines: M1 (fixed), M2 (active), and an exhaustive FULL_LIB search with random design (upper bound on what the expansion library can do without design).

## Metrics
- Recovery: `exact_terms` (primary, per exp01 deviation note). `recovered` (RMSE) is reported but not used for null.
- False discovery: any non-intercept term on `null`.
- Paired comparisons by seed; report wins/losses and the mean difference with a bootstrap CI over seeds.

## Refutation criteria (written now, not after results)
- **A refuted** if the bootstrap 95% CI of M2 − M1 is entirely below MCID 0.2 on test seeds.
- **B confirmed as a problem** if null FDR > 5% on test seeds.
- **C refuted** if the margin rule gives null FDR > 5% on test seeds, or in_space recovery < 80%.
- **D refuted** if abstention on needs_expansion (base-only) < 90% or abstention on in_space/null > 5%.

## Ledger and provenance
Same as Foundation v0.1: every number cites `derived` ledger entries; every claim lists its checks in `docs/claims.json`; tests verify them. New derived metrics (margin, τ, bootstrap CI) get their own method strings.

## Known limits (must be stated in the report)
- Isolation is soft (in-process). A determined agent can reach the law through a closure or a direct import. This is acceptable for synthetic algorithms, not for an LLM agent. Before an LLM runs, the holdout must sit in a separate process.
- Expansion library is pre-specified. D tests abstention, not open-ended invention.
- Synthetic only. Nothing transfers to real science without new data.

## What to build (minimal)
1. `docs/PREREG_exp02.md` with the numbers above frozen.
2. `src/aisci/rules.py` (margin and abstention, agent-side, pure functions).
3. Calibration script that writes thresholds to `results/exp02/calibration.json` with hashes.
4. Test run on seeds 0–199, same ledger pipeline.
5. Report in `docs/RESEARCH_LOG.md` with each hypothesis verdict and the claims it rests on.

## Not in scope
LLM agents (no approved API), web interface, distributed runs, real datasets.
