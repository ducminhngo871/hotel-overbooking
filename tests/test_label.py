"""The label must follow the definition, and leaky columns must never be model inputs."""
import pandas as pd

from hotel_ob import config
from hotel_ob.data import add_labels


def _bookings():
    arrival = pd.Timestamp("2017-03-10")
    return pd.DataFrame({
        "arrival": [arrival] * 4,
        "status_date": [arrival - pd.Timedelta(days=30),   # early cancel
                        arrival - pd.Timedelta(days=3),    # late cancel
                        arrival,                           # no-show
                        arrival + pd.Timedelta(days=2)],   # stayed, checked out
        "reservation_status": ["Canceled", "Canceled", "No-Show", "Check-Out"],
    })


def test_late_label_definition():
    out = add_labels(_bookings(), window=7)
    assert out.late.tolist() == [0, 1, 1, 0]
    assert out.active.tolist() == [False, True, True, True]


def test_window_changes_label():
    out = add_labels(_bookings(), window=2)
    assert out.late.tolist() == [0, 0, 1, 0]


def test_no_leaky_inputs():
    inputs = set(config.NUM_FEATURES + config.CAT_FEATURES)
    forbidden = set(config.LEAKY_FEATURES) | {"reservation_status", "reservation_status_date",
                                               "status_date", "is_canceled", "late"}
    assert not inputs & forbidden
