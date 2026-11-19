"""Every page must open without an error, and the main controls must move the answer the right way.
Needs the small files in app/data (committed; rebuilt by scripts/run_pipeline.py)."""
import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app"
PAGES = [APP / "streamlit_app.py", *sorted((APP / "pages").glob("*.py"))]

pytestmark = pytest.mark.skipif(not (APP / "data" / "meta.json").exists(), reason="run scripts/run_pipeline.py first")


def _run(path):
    return AppTest.from_file(str(path), default_timeout=120).run()


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_page_renders(page):
    at = _run(page)
    assert not at.exception, [e.value for e in at.exception]


def _metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def test_booking_risk_rises_with_previous_cancellations():
    at = _run(APP / "pages" / "1_Booking_risk.py")
    before = float(_metric(at, "Probability of being lost late").rstrip("%"))
    next(s for s in at.slider if s.label.startswith("Guest's previous cancellations")).set_value(3).run()
    after = float(_metric(at, "Probability of being lost late").rstrip("%"))
    assert after > before


def test_tonights_decision_is_more_careful_with_a_limit_or_clumping():
    at = _run(APP / "pages" / "2_Tonights_decision.py")
    at.radio[0].set_value("Rolling 28-night rate").run()
    plain = int(_metric(at, "Overbook by").split()[0])
    at.radio[0].set_value("Rolling rate + clumping").run()
    clumped = int(_metric(at, "Overbook by").split()[0])
    at.radio[0].set_value("Rolling 28-night rate").run()
    at.select_slider[0].set_value(5).run()
    limited = int(_metric(at, "Overbook by").split()[0])
    assert clumped <= plain and limited <= plain
    assert float(_metric(at, "Chance of walking anyone").rstrip("%")) <= 5


def test_app_data_is_consistent():
    meta = json.loads((APP / "data" / "meta.json").read_text())
    bt = pd.read_csv(APP / "data" / "policy_backtest.csv")
    assert set(meta["capacity"]) == {"City Hotel", "Resort Hotel"}
    assert bt.groupby(["hotel", "walk_multiple"]).size().eq(6).all()       # 6 policies everywhere
    assert (bt[bt.policy == "No overbooking"].gain_eur == 0).all()
