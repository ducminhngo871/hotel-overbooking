"""Overbooking decision (newsvendor) and backtest."""
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.stats import betabinom, binom

from . import config


def loss_pmf(n: int, p: float, rho: float = 0.0) -> np.ndarray:
    """P(k of n bookings are lost late), k = 0..n.
    rho = 0: every booking decides on its own (binomial).
    rho > 0: cancellations come in clumps (beta-binomial); the variance is
    n p (1-p) [1 + (n-1) rho] instead of n p (1-p)."""
    k = np.arange(n + 1)
    if rho <= 0:
        return binom.pmf(k, n, p)
    a, b = p * (1 - rho) / rho, (1 - p) * (1 - rho) / rho
    return betabinom.pmf(k, n, a, b)


def expected_curve(C: int, p: float, w: float, xmax: int = config.MAX_OVERBOOK,
                   rho: float = 0.0) -> pd.DataFrame:
    """For each overbooking level x: expected extra rooms filled, expected guests walked,
    probability of walking anyone, and net gain measured in room-rate units."""
    rows = []
    for x in range(xmax + 1):
        n = C + x
        k = np.arange(n + 1)                 # k = bookings lost late
        pm = loss_pmf(n, p, rho)
        shows = n - k
        filled = (np.minimum(C, shows) - C * (1 - p)) @ pm
        walked = np.maximum(0, shows - C) @ pm
        rows.append(dict(x=x, extra_filled=filled, walked=walked,
                         p_any_walk=pm[shows > C].sum(), net_gain=filled - w * walked))
    return pd.DataFrame(rows)


@lru_cache(maxsize=200_000)
def _best_x(C: int, p: float, w: float, xmax: int, max_walk_prob: float, rho: float) -> int:
    curve = expected_curve(C, p, w, xmax, rho)
    allowed = curve[curve.p_any_walk <= max_walk_prob + 1e-12]   # x = 0 is always allowed
    best = int(allowed.net_gain.idxmax())
    return best if curve.net_gain.iloc[best] > 0 else 0


def best_overbook(C: int, p, w: float = config.WALK_MULTIPLE, xmax: int = config.MAX_OVERBOOK,
                  max_walk_prob: float = 1.0, rho: float = 0.0) -> int:
    """Rooms to sell above capacity C when each booking is lost late with probability p
    and walking a guest costs w times the room rate. Without a limit this is the newsvendor
    rule P(late losses <= x) ~= 1 / (1 + w). `max_walk_prob` adds a service-level limit:
    the chance of walking at least one guest that night must stay at or below it.
    `rho` > 0 allows for clumped cancellations (see `loss_pmf`)."""
    if p is None or not np.isfinite(p) or p <= 0:
        return 0
    return _best_x(int(C), round(float(p), 3), float(w), int(xmax), round(float(max_walk_prob), 4),
                   round(float(rho), 4))


def realized(C: int, x, p_actual, adr, w: float):
    """What actually happens each night if we sold C + x rooms and the share of bookings lost late
    was the one really observed that night (assumes the hotel could sell the extra rooms).
    Returns (gain in EUR versus selling exactly C rooms, guests walked)."""
    x, p_actual, adr = np.asarray(x), np.asarray(p_actual, float), np.asarray(adr, float)
    shows_x = np.round((C + x) * (1 - p_actual))
    shows_0 = np.round(C * (1 - p_actual))
    walked = np.maximum(0, shows_x - C)
    gain = (np.minimum(C, shows_x) - shows_0) * adr - walked * w * adr
    return gain, walked


def rolling_rate(n: pd.DataFrame, col: str = "p_actual", window: int = config.ROLLING_NIGHTS,
                 lag: int = config.LATE_WINDOW_DAYS + 1) -> pd.Series:
    """Average of `col` over the previous `window` nights, using only nights already finished
    `lag` days before the night in question (the decision is made 7 days ahead).
    `n` must hold one row per consecutive night, sorted by night."""
    return n[col].shift(lag).rolling(window, min_periods=window // 2).mean()


def add_policy_inputs(nights: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, n in nights.groupby("hotel"):
        n = n.sort_values("night").copy()
        gaps = n.night.diff().dropna()
        assert (gaps == pd.Timedelta(days=1)).all(), "room-nights must be consecutive for the rolling rate"
        n["adr"] = n.adr.fillna(n.adr.mean())
        n["p_roll"] = rolling_rate(n, "p_actual")
        n["p_pred_roll"] = rolling_rate(n, "p_pred")
        n["p_adj"] = (n.p_pred * n.p_roll / n.p_pred_roll).clip(0, 0.5)
        out.append(n)
    return pd.concat(out, ignore_index=True)


def estimate_clumping(n: pd.DataFrame, p_col: str = "p_roll") -> float:
    """How much more nights vary than the binomial model says, turned into the beta-binomial rho.
    phi = variance of (lost - booked p) / sqrt(booked p (1-p)); phi = 1 means binomial.
    Use training nights only."""
    t = n.dropna(subset=[p_col])
    t = t[(t[p_col] > 0) & (t.booked > 1)]
    z = (t.lost - t.booked * t[p_col]) / np.sqrt(t.booked * t[p_col] * (1 - t[p_col]))
    phi = float(z.var())
    return max(0.0, (phi - 1) / (t.booked.mean() - 1))


POLICIES = ["No overbooking", "Fixed rule (2015-16)", "Model, no update",
            "Rolling 28-night rate", "Model + rolling update", "Rolling rate + clumping"]


def backtest(nights: pd.DataFrame, capacity: pd.Series, w: float,
             test_start: str = config.TEST_START, test_end: str | None = None,
             max_walk_prob: float = 1.0):
    """Compare overbooking policies on nights from test_start (to test_end, exclusive).
    Everything a policy learns comes from nights before test_start. Returns (summary, nightly detail)."""
    summary, detail = [], []
    for hotel, n in add_policy_inputs(nights).groupby("hotel"):
        C = int(capacity[hotel])
        train, test = n[n.night < test_start], n[n.night >= test_start]
        if test_end is not None:
            test = test[test.night < test_end]

        # Fixed rule: the single x that would have earned the most on the training nights.
        train_gain = [realized(C, x, train.p_actual, train.adr, w)[0].sum()
                      for x in range(config.MAX_OVERBOOK + 1)]
        x_fixed = int(np.argmax(train_gain))

        rho = estimate_clumping(train)          # learned on 2015-16 nights only

        def rule(ps, r=0.0):
            return np.array([best_overbook(C, p, w, max_walk_prob=max_walk_prob, rho=r) for p in ps])

        policies = {
            "No overbooking": np.zeros(len(test), int),
            "Fixed rule (2015-16)": np.full(len(test), x_fixed),
            "Model, no update": rule(test.p_pred),
            "Rolling 28-night rate": rule(test.p_roll),
            "Model + rolling update": rule(test.p_adj),
            "Rolling rate + clumping": rule(test.p_roll, rho),
        }
        base_revenue = (np.round(C * (1 - test.p_actual)) * test.adr).sum()
        for name, x in policies.items():
            gain, walked = realized(C, x, test.p_actual, test.adr, w)
            summary.append(dict(hotel=hotel, policy=name, walk_multiple=w, capacity=C,
                                max_walk_prob=max_walk_prob, rho=rho,
                                avg_overbook=float(np.mean(x)), gain_eur=float(gain.sum()),
                                gain_pct_revenue=float(gain.sum() / base_revenue * 100),
                                nights=len(test), nights_with_walk=int((walked > 0).sum()),
                                guests_walked=int(walked.sum()),
                                gain_eur_full_nights=float(gain[(test.booked >= C).values].sum())))
            detail.append(pd.DataFrame({"hotel": hotel, "night": test.night.values,
                                        "policy": name, "walk_multiple": w, "overbook": x,
                                        "gain_eur": gain, "walked": walked}))
    return pd.DataFrame(summary), pd.concat(detail, ignore_index=True)
