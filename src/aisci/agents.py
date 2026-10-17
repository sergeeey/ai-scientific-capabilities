"""Three candidate mechanisms for law discovery under a fixed measurement budget.

M1  search within a fixed hypothesis space H0 (non-adaptive design, BIC selection)
M2  M1 + active choice of the next measurement where the top models disagree
M3  M2 + expansion: if H0 cannot fit the data, switch to the pre-specified FULL_LIB

Agents receive only an `oracle` with `.measure(x)` and the public BOUNDS.
They never see the hidden law. Every mechanism spends exactly `budget` measurements.

No LLM is involved: these are deterministic algorithmic stand-ins for the three
mechanisms named in the research question.
"""

from dataclasses import dataclass, field

from aisci.features import BASE_LIB, BOUNDS, DIM, FULL_LIB
from aisci.fit import fit_all

EXPANSION_MIN_N = 8
EXPANSION_TOL = 0.25  # in-sample RMSE above this (~2.5 x noise sigma) means H0 failed
POOL_SIZE = 200
N_INITIAL = 6
TOP_MODELS = 10


@dataclass
class Result:
    mechanism: str
    chosen_terms: tuple
    chosen: object  # Model
    n_measurements: int
    expanded_at: int = None  # measurement index at which expansion happened
    history: list = field(default_factory=list)


def _sample_x(rng):
    lo, hi = BOUNDS
    return tuple(rng.uniform(lo, hi) for _ in range(DIM))


def _measure(oracle, x, X, y):
    X.append(x)
    y.append(oracle.measure(x))


def m1_fixed_search(oracle, budget, rng):
    X, y = [], []
    for _ in range(budget):
        _measure(oracle, _sample_x(rng), X, y)
    best = fit_all(X, y, BASE_LIB)[0]
    return Result("M1_fixed_search", best.names, best, len(y))


def _next_point(models, rng):
    """Pick the candidate where the top models disagree most (max predictive variance)."""
    best_bic = models[0].bic
    top = [m for m in models if m.bic - best_bic <= 2.0][:TOP_MODELS]
    if len(top) < 2:
        top = models[:2]
    pool = [_sample_x(rng) for _ in range(POOL_SIZE)]
    best_x, best_var = None, -1.0
    for x in pool:
        preds = [m.predict(x) for m in top]
        mu = sum(preds) / len(preds)
        var = sum((p - mu) ** 2 for p in preds) / len(preds)
        if var > best_var:
            best_x, best_var = x, var
    return best_x


def _active(oracle, budget, rng, expand):
    X, y = [], []
    for _ in range(min(N_INITIAL, budget)):
        _measure(oracle, _sample_x(rng), X, y)
    lib = BASE_LIB
    expanded_at = None
    history = []
    while len(y) < budget:
        models = fit_all(X, y, lib)
        if expand and expanded_at is None and len(y) >= EXPANSION_MIN_N:
            base_best = models if lib is BASE_LIB else fit_all(X, y, BASE_LIB)
            if base_best[0].rmse > EXPANSION_TOL:
                lib = FULL_LIB
                expanded_at = len(y)
                models = fit_all(X, y, lib)
        history.append((len(y), models[0].names, round(models[0].rmse, 4)))
        _measure(oracle, _next_point(models, rng), X, y)
    final = fit_all(X, y, lib)[0]
    name = "M3_expand" if expand else "M2_active_fixed_space"
    return Result(name, final.names, final, len(y), expanded_at, history)


def m2_active_fixed_space(oracle, budget, rng):
    return _active(oracle, budget, rng, expand=False)


def m3_active_expand(oracle, budget, rng):
    return _active(oracle, budget, rng, expand=True)


MECHANISMS = {
    "M1_fixed_search": m1_fixed_search,
    "M2_active_fixed_space": m2_active_fixed_space,
    "M3_expand": m3_active_expand,
}
