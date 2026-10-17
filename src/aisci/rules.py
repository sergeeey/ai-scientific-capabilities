"""Selection rules for exp02, applied to recorded measurements. Agent-side: stdlib + fit only.

margin_select   rule C: accept the best BIC model only if it beats the intercept-only model by >= margin
abstain_select  rule D: return UNEXPLAINED (None) if the best base-space model misfits by more than tau

Both take the same (X, y) that a mechanism measured, so they do not change how measurements
are taken. Thresholds come from calibration (see docs/PREREG_exp02.md), never from test seeds.
"""

from aisci.features import BASE_LIB
from aisci.fit import fit_all


def margin_select(X, y, margin, lib=BASE_LIB, k=2):
    models = fit_all(X, y, lib, k)
    best = models[0]
    intercept_only = next(m for m in models if m.names == ())
    if best.names and (intercept_only.bic - best.bic) < margin:
        return intercept_only
    return best


def abstain_select(X, y, tau, lib=BASE_LIB, k=2):
    best = fit_all(X, y, lib, k)[0]
    if best.rmse > tau:
        return None  # UNEXPLAINED
    return best
