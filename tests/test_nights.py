"""From bookings to room-nights."""
import pandas as pd

from hotel_ob.nights import estimate_capacity, to_room_nights


def _bookings():
    d = pd.Timestamp("2017-03-01")
    return pd.DataFrame({
        "hotel": ["H"] * 4,
        "arrival": [d, d, d + pd.Timedelta(days=1), d],
        "nights": [3, 1, 1, 2],
        "active": [True, True, True, False],     # last one cancelled early: not on the books
        "late": [0, 1, 0, 0],
        "adr": [100.0, 50.0, 80.0, 999.0],
        "p": [0.1, 0.3, 0.2, 0.9],
    })


def test_multi_night_booking_counts_on_each_night():
    n = to_room_nights(_bookings(), end=pd.Timestamp("2017-03-03")).set_index("night")
    assert n.booked.tolist() == [2, 2, 1]        # Mar 1: A+B, Mar 2: A+C, Mar 3: A
    assert n.lost.tolist() == [1, 0, 0]
    assert n.shows.tolist() == [1, 2, 1]


def test_early_cancellations_are_ignored():
    n = to_room_nights(_bookings())
    assert (n.adr < 999).all()


def test_rates_and_predictions():
    n = to_room_nights(_bookings()).set_index("night")
    assert n.p_actual.iloc[0] == 0.5
    assert abs(n.p_pred.iloc[0] - 0.2) < 1e-9
    assert n.adr.iloc[0] == 100.0                 # only guests who showed set the room rate


def test_stays_stop_at_the_last_arrival_date():
    """Nights after the last arrival in the data are incomplete (later arrivals are missing), so drop them."""
    n = to_room_nights(_bookings())
    assert n.night.max() == pd.Timestamp("2017-03-02")


def test_capacity_is_busiest_night():
    assert estimate_capacity(to_room_nights(_bookings()))["H"] == 2
