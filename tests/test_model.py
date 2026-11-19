"""Models learn a real signal; evaluation helpers are correct."""
import numpy as np
import pandas as pd
import pytest

from hotel_ob import config
from hotel_ob.model import build, calibration_table, fit_eval, top_coefficients


def _synthetic(n=3000, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.integers(0, 5, n) for c in config.NUM_FEATURES})
    for c in config.CAT_FEATURES:
        df[c] = rng.choice(["a", "b", "c"], n)
    df["lead_time"] = rng.integers(0, 300, n)
    p = 1 / (1 + np.exp(-(-3 + df.lead_time / 80)))      # risk rises with lead time
    df["late"] = (rng.random(n) < p).astype(int)
    train = pd.Series(np.arange(n) < 2000)
    return df, train, ~train


@pytest.mark.parametrize("kind", ["logit", "gb"])
def test_model_finds_the_signal(kind):
    df, tr, te = _synthetic()
    _, auc, p = fit_eval(df, "late", tr, te, kind)
    assert auc > 0.65 and len(p) == te.sum() and ((p >= 0) & (p <= 1)).all()


def test_unknown_model_kind():
    with pytest.raises(ValueError):
        build("magic")


def test_calibration_table():
    y = np.r_[np.zeros(50), np.ones(50)]
    p = np.r_[np.full(50, 0.1), np.full(50, 0.9)]
    cal = calibration_table(y, p, bins=2)
    assert cal.n.sum() == 100
    assert np.allclose(cal.predicted, [0.1, 0.9]) and np.allclose(cal.actual, [0, 1])


def test_top_coefficients_sorted_and_named():
    df, tr, te = _synthetic()
    m, _, _ = fit_eval(df, "late", tr, te, "logit")
    top = top_coefficients(m, 5)
    assert top.coef.abs().is_monotonic_decreasing
    assert top.feature.iloc[0] == "lead_time"
    assert not top.feature.str.contains("__").any()
