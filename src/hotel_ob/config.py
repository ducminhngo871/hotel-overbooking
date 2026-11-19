"""Project-wide settings. Change values here, not inside the code."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_URL = ("https://raw.githubusercontent.com/rfordatascience/tidytuesday/"
            "master/data/2020/2020-02-11/hotels.csv")
RAW_PATH = ROOT / "data" / "raw" / "hotels.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "report" / "figures"
MODEL_DIR = ROOT / "models"
APP_DATA_DIR = ROOT / "app" / "data"

LATE_WINDOW_DAYS = 7          # a cancellation within this many days of arrival = "late"
TEST_START = "2017-01-01"     # train on arrivals before, test on arrivals from this date
VALID_START = "2016-07-01"    # extra check: learn before this date, test Jul-Dec 2016
ROLLING_NIGHTS = 28           # look-back for the rolling late-cancellation rate
WALK_MULTIPLE = 3.0           # cost of walking a guest, as a multiple of the room rate (ADR)
WALK_GRID = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
MAX_OVERBOOK = 40
WALK_PROB_GRID = [0.05, 0.10, 0.20, 0.30, 0.50, 1.0]   # service-level limits to try

# Information a hotel has at the moment a booking is made.
NUM_FEATURES = ["lead_time", "nights", "adults", "previous_cancellations",
                "previous_bookings_not_canceled", "total_of_special_requests",
                "adr", "days_in_waiting_list", "is_repeated_guest"]
CAT_FEATURES = ["hotel", "deposit_type", "market_segment", "distribution_channel",
                "customer_type", "meal", "reserved_room_type", "arrival_date_month"]

# Columns that are updated after booking (until check-in or cancellation). Never use as inputs.
# required_car_parking_spaces: all 7,409 bookings with parking > 0 checked out (0 cancels, 0 no-shows),
# so it is almost certainly recorded on arrival.
LEAKY_FEATURES = ["booking_changes", "assigned_room_type", "country", "required_car_parking_spaces"]
