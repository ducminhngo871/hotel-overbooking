"""Shared loaders for the Streamlit app."""
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR.parent / "src"))
DATA = APP_DIR / "data"

from hotel_ob.policy import POLICIES as POLICY_ORDER  # noqa: E402

POLICY_COLORS = dict(zip(POLICY_ORDER, ["#a0aec0", "#dd6b20", "#c53030", "#2f855a", "#2b6cb0", "#6b46c1"]))


@st.cache_resource
def load_model():
    return joblib.load(DATA / "late_cancel_logit.joblib")


@st.cache_data
def load_meta():
    return json.loads((DATA / "meta.json").read_text())


@st.cache_data
def load_nights():
    return pd.read_parquet(DATA / "room_nights.parquet")


@st.cache_data
def load_backtest():
    return pd.read_csv(DATA / "policy_backtest.csv"), pd.read_parquet(DATA / "policy_detail.parquet")


@st.cache_data
def load_service_level():
    return pd.read_csv(DATA / "service_level_tradeoff.csv")


@st.cache_data
def load_explore():
    monthly = pd.read_csv(DATA / "late_rate_by_month.csv", parse_dates=["month"])
    return monthly, pd.read_csv(DATA / "explore.csv")
