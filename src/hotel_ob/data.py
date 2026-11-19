"""Load, clean and label the hotel booking data."""
import pandas as pd

from . import config

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def load_raw(path=config.RAW_PATH) -> pd.DataFrame:
    return pd.read_csv(path, na_values=["NULL"])


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Add dates and nights, drop impossible rows. Returns the clean frame and a log of what was dropped."""
    df = raw.copy()
    month_num = df.arrival_date_month.map({m: i + 1 for i, m in enumerate(MONTHS)})
    df["arrival"] = pd.to_datetime(dict(year=df.arrival_date_year, month=month_num,
                                        day=df.arrival_date_day_of_month))
    df["status_date"] = pd.to_datetime(df.reservation_status_date)
    df["nights"] = df.stays_in_weekend_nights + df.stays_in_week_nights
    guests = df.adults + df.children.fillna(0) + df.babies

    rules = {
        "zero guests": guests == 0,
        "negative ADR": df.adr < 0,
        "ADR >= 1000 EUR": df.adr >= 1000,
    }
    log = {name: int(mask.sum()) for name, mask in rules.items()}
    drop = pd.concat(rules.values(), axis=1).any(axis=1)
    log["rows before"] = len(df)
    df = df[~drop].copy()
    log["rows after"] = len(df)
    return df, log


def add_labels(df: pd.DataFrame, window: int = config.LATE_WINDOW_DAYS) -> pd.DataFrame:
    """late = cancelled within `window` days of arrival, or no-show.
    active = still on the books `window` days before arrival.
    reservation_status / status_date are used ONLY here, to build the label."""
    out = df.copy()
    out["days_before_cancel"] = (out.arrival - out.status_date).dt.days
    cancelled = out.reservation_status == "Canceled"
    early = cancelled & (out.days_before_cancel > window)
    out["late"] = ((cancelled & ~early) | (out.reservation_status == "No-Show")).astype(int)
    out["active"] = ~early
    return out


def time_split(df: pd.DataFrame, test_start: str = config.TEST_START):
    train = df.arrival < test_start
    return train, ~train
