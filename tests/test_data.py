"""Cleaning rules and the time split."""
import pandas as pd

from hotel_ob.data import clean, time_split


def _raw(**over):
    row = dict(hotel="City Hotel", arrival_date_year=2016, arrival_date_month="March",
               arrival_date_day_of_month=5, reservation_status_date="2016-03-07",
               stays_in_weekend_nights=1, stays_in_week_nights=2, adults=2, children=0.0, babies=0, adr=90.0,
               reservation_status="Check-Out", is_canceled=0)
    row.update(over)
    return row


def test_clean_drops_impossible_rows_and_logs_them():
    raw = pd.DataFrame([_raw(), _raw(adults=0), _raw(adr=-5.0), _raw(adr=5400.0), _raw(adults=0, adr=-1.0)])
    df, log = clean(raw)
    assert len(df) == 1
    assert log["rows before"] == 5 and log["rows after"] == 1
    assert log["zero guests"] == 2 and log["negative ADR"] == 2 and log["ADR >= 1000 EUR"] == 1


def test_children_missing_is_not_a_guest():
    """children is NaN for a few rows; a booking with 0 adults and NaN children has no guests."""
    df, _ = clean(pd.DataFrame([_raw(adults=0, children=float("nan"))]))
    assert df.empty


def test_babies_only_still_counts_as_guests():
    df, _ = clean(pd.DataFrame([_raw(adults=0, children=0.0, babies=1)]))
    assert len(df) == 1


def test_dates_and_nights():
    df, _ = clean(pd.DataFrame([_raw()]))
    assert df.arrival.iloc[0] == pd.Timestamp("2016-03-05")
    assert df.status_date.iloc[0] == pd.Timestamp("2016-03-07")
    assert df.nights.iloc[0] == 3


def test_time_split_is_strict():
    df = pd.DataFrame({"arrival": pd.to_datetime(["2016-12-31", "2017-01-01", "2017-06-01"])})
    train, test = time_split(df, "2017-01-01")
    assert train.tolist() == [True, False, False]
    assert (train ^ test).all()
