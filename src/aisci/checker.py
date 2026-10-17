"""Independent checker: scores a discovered model against the hidden law.

It sees the truth; the agents do not. Scoring uses a separate, fixed test grid
that no mechanism ever measures.
"""

import math
import random

from aisci.features import BOUNDS, DIM

TEST_SEED = 12345
N_TEST = 400
RECOVERY_RMSE = 0.05  # noise-free test RMSE under which a model counts as recovering the law


def test_grid():
    rng = random.Random(TEST_SEED)
    lo, hi = BOUNDS
    return [tuple(rng.uniform(lo, hi) for _ in range(DIM)) for _ in range(N_TEST)]


_GRID = test_grid()


def score(model, law):
    truth = [law.fn(x) for x in _GRID]
    pred = [model.predict(x) for x in _GRID]
    rmse = math.sqrt(sum((p - t) ** 2 for p, t in zip(pred, truth)) / len(truth))
    return {
        "test_rmse": rmse,
        "recovered": rmse < RECOVERY_RMSE,
        "exact_terms": set(model.names) == set(law.terms),
        "false_terms": sorted(set(model.names) - set(law.terms)) if not law.terms else None,
    }
