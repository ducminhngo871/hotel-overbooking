"""Model inputs: only booking-time information, robust to new categories."""
import pandas as pd

from hotel_ob import config
from hotel_ob.features import make_X, preprocessor


def _df(n=30):
    rows = []
    for i in range(n):
        r = {c: i % 5 for c in config.NUM_FEATURES}
        r.update({c: f"v{i % 3}" for c in config.CAT_FEATURES})
        r.update({"booking_changes": 9, "is_canceled": 1, "reservation_status": "Canceled"})
        rows.append(r)
    return pd.DataFrame(rows)


def test_make_X_keeps_only_allowed_columns():
    X = make_X(_df())
    assert list(X.columns) == config.NUM_FEATURES + config.CAT_FEATURES
    assert "booking_changes" not in X and "is_canceled" not in X


def test_categories_become_strings():
    df = _df()
    df["arrival_date_month"] = 7          # a number must still be treated as a category
    X = make_X(df)
    assert X.arrival_date_month.map(type).eq(str).all()


def test_unknown_category_does_not_crash():
    X = make_X(_df())
    prep = preprocessor().fit(X)
    new = X.head(1).copy()
    new["market_segment"] = "Never seen before"
    assert prep.transform(new).shape[0] == 1


def test_no_input_is_in_the_leaky_list():
    assert not set(config.NUM_FEATURES + config.CAT_FEATURES) & set(config.LEAKY_FEATURES)
