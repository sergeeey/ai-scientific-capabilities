# Pre-registration: exp01 (synthetic, three mechanisms)

Written BEFORE the first run of `aisci.run`. Changing a criterion after results are seen makes the change exploratory.

## L0 classification (estimand-ops)
**Descriptive.** The question is: how do three procedures perform on simulated data with a known law, at a fixed measurement budget? No causal claim about the world. No claim about LLMs.

## Estimand
- Population: 3 synthetic laws x 30 seeds per mechanism (seeds 0..29).
- Intervention: mechanism M1, M2 or M3.
- Comparator: M1 (fixed-space search, non-adaptive) is the baseline.
- Endpoint: `recovered` = noise-free RMSE on a fixed independent test grid < 0.05; plus `exact_terms` (chosen term set equals the true term set).
- Summary: counts out of 30; paired comparisons by seed.
- Budget: 30 measurements per run for every mechanism (`n_calls` is asserted).

## Fixed settings
sigma = 0.1 (Gaussian observation noise); domain [-2,2]^3; H0 = BASE_LIB, at most 2 terms + intercept; BIC selection; expansion trigger RMSE > 0.25 after at least 8 points; initial design 6 random points; candidate pool 200.

## Design / power (EstimandOps line)
`n, baseline_or_sigma, alpha, power, MDE, MCID`: 30 seeds per cell (clusters = seeds, one run each); baseline_or_sigma = sigma 0.1; alpha 0.05 two-sided; power 0.8 not targeted. With n=30 paired seeds, the MDE on a recovery rate difference is large (roughly 0.3 at baseline 0.5). **So only large differences are detectable.** MCID = 0.2 recovery-rate difference (fixed before the data).

## Predictions (written before results)
- P1 (in_space): M2 and M3 recover at least as often as M1. Null expectation: no difference.
- P2 (needs_expansion): M1 and M2 cannot recover (base space cannot fit tanh; control test enforces this). M3 recovers in most seeds.
- P3 (null): false-term rate is small for all mechanisms; M2 and M3 active design may increase false selections. Report it, whatever it is.

## What would falsify the claim "active choice or expansion helps"
- P2 fails if M3 recovers < 50% on needs_expansion.
- P1 falsified if M2 recovers meaningfully less than M1 on in_space (difference >= 0.2 in favour of M1).

## What this experiment cannot show
- Anything about LLMs. The mechanisms are algorithmic stand-ins; no model was queried.
- Open-ended discovery. The expansion library is pre-specified, so expansion is a search over a larger fixed space.
- Robustness to other noise levels, other laws, or other budgets. Only the cells above were run.
