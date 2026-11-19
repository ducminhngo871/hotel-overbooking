"""Home page. Run with:  streamlit run app/streamlit_app.py"""
import streamlit as st

from common import load_backtest, load_meta

st.set_page_config(page_title="Hotel Overbooking", page_icon="🏨", layout="wide")

st.title("🏨 How many rooms should a hotel overbook?")
st.markdown(
    "Hotels lose money when guests cancel at the last minute or do not show up: the room stays "
    "empty. Selling a few more rooms than the hotel has (**overbooking**) fills those rooms, but if "
    "too many guests arrive, the hotel must send someone to another hotel (**walking a guest**), "
    "which is expensive and annoying."
)
st.markdown(
    "This project uses **119,000 real bookings** from two hotels in Portugal (2015–2017) to predict "
    "late cancellations, decide how many rooms to overbook each night, and test those decisions "
    "on 2017."
)

summary, _ = load_backtest()
meta = load_meta()
main = summary[summary.walk_multiple == meta["walk_multiple"]].set_index(["hotel", "policy"])
best = main.loc[("City Hotel", "Rolling rate + clumping")]
roll = main.loc[("City Hotel", "Rolling 28-night rate")]
naive = main.loc[("City Hotel", "Model, no update")]


def eur_k(v):
    return f"{'+' if v >= 0 else '−'}€{abs(v) / 1000:,.0f}k"


c1, c2, c3, c4 = st.columns(4)
c1.metric("Rolling rate + clumping", eur_k(best.gain_eur),
          f"{best.gain_pct_revenue:+.1f}% room revenue; walks on {best.nights_with_walk} nights")
c2.metric("Simple rolling rate", eur_k(roll.gain_eur),
          f"{roll.gain_pct_revenue:+.1f}% room revenue; walks on {roll.nights_with_walk} nights")
c3.metric("Model, never updated", eur_k(naive.gain_eur), f"{naive.gain_pct_revenue:+.1f}% room revenue")
c4.metric("Late-loss rate, 2017", f"{meta['base_late_rate']*100:.1f}%",
          "of bookings still on the books 7 days out", delta_color="off")
st.caption(f"City Hotel, January–August 2017, {best.nights} nights, walking a guest costs "
           f"{meta['walk_multiple']:g}× the room rate. Extra revenue is compared with not overbooking.")

st.info(
    "**Main findings.** (1) Late cancellations at the City Hotel fell from about 12% of bookings in 2015 to about "
    "6% in 2017. A model trained on 2015–2016 kept expecting many cancellations, overbooked too much and would "
    "have *lost* money. A simple rule that updates with the last four weeks made money. "
    "(2) Cancellations come in clumps, so a coin-flip model is too bold. Allowing for clumping cut the nights "
    "with a walked guest from 109 to 24."
)

st.subheader("Pages")
st.markdown(
    "1. **Booking risk** – enter a booking, see how likely it is to be lost late.\n"
    "2. **Tonight's decision** – pick a night and see how many rooms to overbook.\n"
    "3. **Compare policies** – what each rule would have earned in 2017, and how many guests it walked.\n"
    "4. **Explore the data** – cancellations by channel, deposit and month."
)
st.caption("Data: Antonio, de Almeida & Nunes (2019), Hotel booking demand datasets, Data in Brief 22. "
           "Room counts are estimated from the data; results are a simulation, not the hotels' real outcomes.")
