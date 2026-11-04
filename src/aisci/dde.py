"""Delay-differential testbed (exp04): agent-side procedures and the history-controlled oracle.

World (hidden, runner-side): x'(t) = -a*x(t) + b*x(t - tau), tau in TAUS.
The agent chooses a history phi (6 knots on t in [-1, 0]) and receives 61 noisy samples of x
on t = 0, 0.05, ..., 3.0. Samples are noisy; the knots are exact (the agent set them).

This module must NOT import aisci.hidden_laws. The runner builds DelayOracle from world params.

Conditions (algorithmic, same budget):
  A1  fixed design (random histories), memoryless base only, abstains on misfit
  A2  A1 + adaptive design: next history maximises disagreement between base candidates
  A3  A2 + expansion to the delay family when the base misfits; a NON_IDENTIFIABLE check
      runs before a delay is named
"""

import math
import random

from aisci import fit
from aisci.environment import BudgetExceeded
from aisci.rules import identifiability_certificate

SIM_DT = 0.01
T_END = 3.0
SAMPLE_DT = 0.05
KNOT_DT = 0.2
HIST_T0 = -1.0
N_KNOTS = 6  # t = -1.0, -0.8, ..., 0.0
N_SAMPLES = 61  # t = 0.0, 0.05, ..., 3.0
SIGMA = 0.01
BUDGET = 30
N_INIT = 6
POOL = 40
EXPANSION_MIN_N = 8
DERIV_SIGMA = SIGMA * math.sqrt(2) / (2 * SAMPLE_DT)  # noise of a central-difference derivative


def deriv_tol(n_rows):
    """Noise-aware residual threshold: derivative noise, inflated by a 3-sigma chi-square margin.

    A correct model leaves residuals at the noise level; a misfit inflates them. The threshold
    depends only on sigma, the sample step and the number of rows, so it is not tuned on data.
    """
    return DERIV_SIGMA * math.sqrt(1 + 3 * math.sqrt(2 / max(n_rows, 1)))


TAUS = (0.4, 0.6, 0.8, 1.0)
DIVERGENCE_K = 3.0
ZERO_IDX = round(-HIST_T0 / SIM_DT)  # fine-grid index of t = 0


def phi_at(phi, t):
    """Piecewise-linear history on [-1, 0] from the 6 knots."""
    u = (t - HIST_T0) / KNOT_DT
    j = min(max(math.floor(u), 0), N_KNOTS - 2)
    w = u - j
    return phi[j] * (1 - w) + phi[j + 1] * w


def simulate(rhs, lag_steps, phi):
    """Euler integration on the fine grid; returns x at the 16 sample times."""
    n_fine = round((T_END - HIST_T0) / SIM_DT)
    xs = [0.0] * (n_fine + 1)
    for j in range(n_fine + 1):
        s = HIST_T0 + j * SIM_DT
        if j <= ZERO_IDX:
            xs[j] = phi_at(phi, min(s, 0.0))
        else:
            xs[j] = xs[j - 1] + SIM_DT * rhs(xs[j - 1], xs[j - 1 - lag_steps])
    step = round(SAMPLE_DT / SIM_DT)
    return [xs[ZERO_IDX + k * step] for k in range(N_SAMPLES)]


def truth_rhs(a, b):
    return lambda x, xl: -a * x + b * xl


def delay_rhs(c1, c2):
    return lambda x, xl: c1 * x + c2 * xl


def base_rhs(c1, c3=0.0):
    return lambda x, xl: c1 * x + c3 * x * x * x


class DelayOracle:
    """Measures the world with a fixed noise stream. Budget is a hard cap, as in Oracle."""

    def __init__(self, a, b, tau, sigma=SIGMA, seed=0, budget=BUDGET):
        self._truth = truth_rhs(a, b)
        self._lag = round(tau / SIM_DT)
        self._sigma = sigma
        self._rng = random.Random(seed)
        self._budget = budget
        self._calls = 0

    @property
    def calls(self):
        return self._calls

    def experiment(self, phi):
        if self._calls >= self._budget:
            raise BudgetExceeded(f"experiment budget {self._budget} exhausted")
        self._calls += 1
        clean = simulate(self._truth, self._lag, phi)
        return [v + self._rng.gauss(0.0, self._sigma) for v in clean]


def random_phi(rng):
    return [rng.uniform(-1.5, 1.5) for _ in range(N_KNOTS)]


def _rows(experiments):
    """Derivative estimates and lagged regressors, one row per (experiment, interior sample)."""
    rows = []
    for phi, s in experiments:
        for k in range(1, N_SAMPLES - 1):
            t_k = k * SAMPLE_DT
            dhat = (s[k + 1] - s[k - 1]) / (2 * SAMPLE_DT)
            lags = {}
            for tau in TAUS:
                if t_k - tau <= 1e-9:
                    lags[tau] = phi_at(phi, t_k - tau)
                else:
                    lags[tau] = s[k - round(tau / SAMPLE_DT)]
            rows.append((dhat, s[k], lags))
    return rows


def _fit_cols(rows, tau=None, cubic=False):
    y = [r[0] for r in rows]
    x = [r[1] for r in rows]
    cols = [x]
    if tau is not None:
        cols.append([r[2][tau] for r in rows])
    elif cubic:
        cols.append([v**3 for v in x])
    coefs, rss = fit.lstsq(cols, y)
    bic = len(y) * math.log(max(rss / len(y), 1e-12)) + len(cols) * math.log(len(y))
    return {
        "coefs": coefs,
        "rss": rss,
        "bic": bic,
        "rmse": math.sqrt(rss / len(y)),
        "tau": tau,
        "cubic": cubic,
    }


def best_base(rows):
    lin = _fit_cols(rows)
    cub = _fit_cols(rows, cubic=True)
    return lin if lin["bic"] <= cub["bic"] else cub


def delay_fits(rows):
    fits = [_fit_cols(rows, tau=tau) for tau in TAUS]
    return sorted(fits, key=lambda f: f["bic"])


def _base_rhs_of(model):
    c1 = model["coefs"][0]
    c3 = model["coefs"][1] if model["cubic"] else 0.0
    return base_rhs(c1, c3)


def _delay_rhs_of(model):
    return delay_rhs(model["coefs"][0], model["coefs"][1])


def _delay_predictor(model):
    """Trajectory predictor for one delay candidate: history -> predicted samples."""
    rhs = _delay_rhs_of(model)
    lag = round(model["tau"] / SIM_DT)
    return lambda phi: simulate(rhs, lag, phi)


def decide(experiments, expansion_allowed, cert_rng):
    """Outcome: 'memoryless' | 'delay:<tau>' | 'NON_IDENTIFIABLE' | 'UNEXPLAINED'."""
    rows = _rows(experiments)
    tol = deriv_tol(len(rows))
    base = best_base(rows)
    if base["rmse"] <= tol:
        return "memoryless", base
    if not expansion_allowed:
        return "UNEXPLAINED", base
    fits = delay_fits(rows)
    best = fits[0]
    if best["rmse"] > tol:
        return "UNEXPLAINED", best
    top2 = fits[:2]
    pool = [random_phi(cert_rng) for _ in range(POOL)]
    cert = identifiability_certificate(
        [_delay_predictor(m) for m in top2],
        pool,
        sigma=SIGMA,
        k=DIVERGENCE_K,
    )
    if cert["verdict"] != "IDENTIFIABLE":
        return "NON_IDENTIFIABLE", best
    return f"delay:{best['tau']}", best


def _disagreement(phi, candidates):
    trajs = [simulate(rhs, lag, phi) for rhs, lag in candidates]
    best = 0.0
    for i in range(len(trajs)):
        for j in range(i + 1, len(trajs)):
            best = max(best, max(abs(p - q) for p, q in zip(trajs[i], trajs[j])))
    return best


def run_condition(cond, oracle, rng, cert_rng):
    """Spend exactly BUDGET experiments under condition cond in {'A1', 'A2', 'A3'}."""
    experiments = []
    expanded_at = None
    if cond == "A1":
        for _ in range(BUDGET):
            phi = random_phi(rng)
            experiments.append((phi, oracle.experiment(phi)))
    else:
        for _ in range(min(N_INIT, BUDGET)):
            phi = random_phi(rng)
            experiments.append((phi, oracle.experiment(phi)))
        pool = [random_phi(rng) for _ in range(POOL)]
        while oracle.calls < BUDGET:
            if cond == "A3" and expanded_at is None and len(experiments) >= EXPANSION_MIN_N:
                rows0 = _rows(experiments)
                if best_base(rows0)["rmse"] > deriv_tol(len(rows0)):
                    expanded_at = len(experiments)
            rows = _rows(experiments)
            if expanded_at is not None:
                cand = [(_delay_rhs_of(m), round(m["tau"] / SIM_DT)) for m in delay_fits(rows)[:3]]
            else:
                cand = [
                    (_base_rhs_of(m), round(TAUS[0] / SIM_DT))
                    for m in (_fit_cols(rows), _fit_cols(rows, cubic=True))
                ]
            phi = max(pool, key=lambda u: _disagreement(u, cand))
            experiments.append((phi, oracle.experiment(phi)))
    expansion_allowed = cond == "A3"
    outcome, model = decide(experiments, expansion_allowed, cert_rng)
    return {"outcome": outcome, "model": model, "expanded_at": expanded_at, "n": len(experiments)}


def holdout_rmse(outcome, model, truth_rhs_fn, truth_lag, test_phis):
    """RMSE of the named model against the noise-free world on fresh histories.

    Returns None when the procedure named no model (UNEXPLAINED, NON_IDENTIFIABLE).
    """
    if outcome in ("UNEXPLAINED", "NON_IDENTIFIABLE"):
        return None
    if outcome == "memoryless":
        rhs, lag = _base_rhs_of(model), round(TAUS[0] / SIM_DT)
    else:
        rhs, lag = _delay_rhs_of(model), round(model["tau"] / SIM_DT)
    errs = []
    for phi in test_phis:
        t_true = simulate(truth_rhs_fn, truth_lag, phi)
        t_pred = simulate(rhs, lag, phi)
        errs += [(p - q) ** 2 for p, q in zip(t_pred, t_true)]
    return math.sqrt(sum(errs) / len(errs))
