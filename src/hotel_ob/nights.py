"""Go from bookings to room-nights: what was on the books each night, and what was lost."""
import pandas as pd


def to_room_nights(df: pd.DataFrame, p_col: str = "p", end=None) -> pd.DataFrame:
    """One row per (hotel, night), using bookings still active 7 days before arrival.
    booked = rooms on the books, lost = rooms freed by late cancels / no-shows,
    shows = rooms actually occupied, p_pred = mean predicted late probability."""
    a = df[df.active & (df.nights > 0)].reset_index(drop=True)
    rn = a.loc[a.index.repeat(a.nights)].copy()
    rn["night"] = rn.arrival + pd.to_timedelta(rn.groupby(level=0).cumcount(), unit="D")
    rn = rn[rn.night <= (end if end is not None else df.arrival.max())]
    g = rn.groupby(["hotel", "night"])
    nights = pd.DataFrame({"booked": g.size(), "lost": g.late.sum()})
    if p_col in rn:
        nights["p_pred"] = g[p_col].mean()
    shown = rn[rn.late == 0].groupby(["hotel", "night"]).adr.agg(["size", "mean"])
    nights = nights.join(shown.rename(columns={"size": "shows", "mean": "adr"}))
    nights["shows"] = nights.shows.fillna(0).astype(int)
    nights = nights.reset_index()
    nights["p_actual"] = nights.lost / nights.booked
    return nights


def estimate_capacity(nights: pd.DataFrame) -> pd.Series:
    """The data has no room count. Assume capacity = the most rooms ever occupied in one night."""
    return nights.groupby("hotel").shows.max().astype(int)
