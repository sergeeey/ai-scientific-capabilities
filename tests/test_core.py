import math
import os
import random
import re

from aisci.agents import MECHANISMS
from aisci.checker import score
from aisci.environment import Oracle
from aisci.features import BASE_LIB, FULL_LIB
from aisci.fit import fit_all, lstsq
from aisci.hidden_laws import LAWS
from aisci.run import run_one

SRC = os.path.join(os.path.dirname(__file__), "..", "src", "aisci")
AGENT_SIDE = ["agents.py", "environment.py", "features.py", "fit.py"]


def test_lstsq_recovers_known_coefficients():
    rng = random.Random(0)
    x1 = [rng.uniform(-1, 1) for _ in range(50)]
    x2 = [rng.uniform(-1, 1) for _ in range(50)]
    y = [2.0 + 3.0 * a - 1.5 * b for a, b in zip(x1, x2)]
    coefs, rss = lstsq([[1.0] * 50, x1, x2], y)
    assert all(abs(c - t) < 1e-6 for c, t in zip(coefs, [2.0, 3.0, -1.5]))
    assert rss < 1e-10


def test_fit_all_finds_true_terms_on_noiseless_data():
    rng = random.Random(1)
    X = [tuple(rng.uniform(-2, 2) for _ in range(3)) for _ in range(40)]
    y = [1.5 * x[0] * x[1] - 0.8 * x[2] ** 2 for x in X]
    best = fit_all(X, y, BASE_LIB)[0]
    assert set(best.names) == {"x1*x2", "x3^2"}


def test_agents_cannot_import_hidden_laws():
    for fname in AGENT_SIDE:
        text = open(os.path.join(SRC, fname), encoding="utf-8").read()
        assert not re.search(r"hidden_laws|LAWS\b", text), fname


def test_oracle_counts_calls_and_hides_law():
    o = Oracle(lambda x: 7.0, sigma=0.0, seed=0)
    assert o.measure((0.0, 0.0, 0.0)) == 7.0
    assert o.calls == 1


def test_every_mechanism_uses_exact_budget():
    for name in MECHANISMS:
        row = run_one("in_space", name, seed=3, budget=25, sigma=0.1)
        assert row["n_calls"] == 25, name


def test_true_law_scores_as_recovered():
    law = LAWS["in_space"]

    class TrueModel:
        names = ("x1*x2", "x3^2")

        def predict(self, x):
            return law.fn(x)

    s = score(TrueModel(), law)
    assert s["recovered"] and s["exact_terms"] and s["test_rmse"] < 1e-9


def test_base_space_cannot_fit_expansion_law():
    # Control for the scenario design: the expansion law must NOT be fittable in H0.
    rng = random.Random(2)
    law = LAWS["needs_expansion"]
    X = [tuple(rng.uniform(-2, 2) for _ in range(3)) for _ in range(200)]
    y = [law.fn(x) for x in X]
    assert fit_all(X, y, BASE_LIB)[0].rmse > 0.25
    assert set(fit_all(X, y, FULL_LIB)[0].names) == {"tanh(x1)*x2", "x3"}


def test_run_is_reproducible():
    a = run_one("needs_expansion", "M3_expand", seed=5, budget=30, sigma=0.1)
    b = run_one("needs_expansion", "M3_expand", seed=5, budget=30, sigma=0.1)
    assert a == b


def test_null_law_has_no_true_terms():
    assert LAWS["null"].terms == frozenset()
    assert math.isclose(LAWS["null"].fn((1.0, 2.0, 0.5)), 0.0)
