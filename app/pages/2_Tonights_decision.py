import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import load_meta, load_nights
from hotel_ob.policy import best_overbook, expected_curve, realized

st.set_page_config(page_title="Tonight's decision", page_icon="🏨", layout="wide")
st.title("2 · How many rooms should we overbook tonight?")
st.caption("The decision is made 7 days before the night, using only what was known then.")

nights, meta = load_nights(), load_meta()
c1, c2, c3 = st.columns(3)
hotel = c1.selectbox("Hotel", ["City Hotel", "Resort Hotel"])
n = nights[(nights.hotel == hotel) & (nights.night >= meta["test_start"])].sort_values("night")
night = c2.date_input("Night (2017)", value=pd.Timestamp("2017-08-15").date(),
                      min_value=n.night.min().date(), max_value=n.night.max().date())
w = c3.slider("Cost of walking one guest (× room rate)", 1.0, 5.0, 3.0, 0.5)
c4, c5 = st.columns([2, 1])
method = c4.radio("How to estimate tonight's late-loss rate",
                  ["Rolling rate + clumping", "Rolling 28-night rate", "Model + rolling update",
                   "Model, no update"], horizontal=True,
                  help="Clumping: allow for cancellations arriving in groups, which makes bad nights worse "
                       "than a coin-flip model expects.")
cap_pct = c5.select_slider("Max chance of walking anyone", options=[5, 10, 20, 30, 50, 100], value=100,
                           format_func=lambda v: "no limit" if v == 100 else f"{v}%")

r = n[n.night == pd.Timestamp(night)].iloc[0]
C = int(r.C)
p = {"Rolling 28-night rate": r.p_roll, "Rolling rate + clumping": r.p_roll,
     "Model + rolling update": r.p_adj, "Model, no update": r.p_pred}[method]
rho = meta["clumping_rho"][hotel] if method == "Rolling rate + clumping" else 0.0
x_best = best_overbook(C, p, w, max_walk_prob=cap_pct / 100, rho=rho)
curve = expected_curve(C, p, w, rho=rho)
curve["net_gain_eur"] = curve.net_gain * r.adr

m1, m2, m3, m4 = st.columns(4)
m1.metric("Rooms (estimated)", C)
m2.metric("Expected late-loss rate", f"{p*100:.1f}%")
m3.metric("Overbook by", f"{x_best} rooms")
m4.metric("Chance of walking anyone", f"{curve.p_any_walk[x_best]*100:.0f}%")

colors = ["#2f855a" if i == x_best else ("#e2e8f0" if curve.p_any_walk[i] > cap_pct / 100 else "#a0aec0")
          for i in curve.x]
fig = go.Figure()
fig.add_bar(x=curve.x, y=curve.net_gain_eur, marker_color=colors,
            customdata=curve.p_any_walk * 100,
            hovertemplate="Overbook %{x}: %{y:,.0f} EUR expected<br>P(walk anyone) %{customdata:.0f}%<extra></extra>")
fig.update_layout(title="Expected extra revenue for each overbooking level (green = chosen; pale = above your limit)",
                  xaxis_title="Rooms sold above capacity", yaxis_title="EUR (expected)",
                  height=360, margin=dict(t=50, b=40))
st.plotly_chart(fig, width="stretch")

st.markdown(
    f"**Rule of thumb:** without a limit, overbook until the chance of having fewer late losses than "
    f"overbooked rooms reaches 1 / (1 + {w:g}) = **{1/(1+w)*100:.0f}%**. The more it costs to walk a guest, "
    "the more careful the hotel should be. Allowing for clumped cancellations makes the hotel more careful still."
)

gain, walked = realized(C, [x_best], [r.p_actual], [r.adr], w)
with st.expander("What actually happened that night?"):
    st.write(f"Rooms lost late: **{r.lost}** of {r.booked} on the books "
             f"({r.p_actual*100:.1f}%). Average room rate €{r.adr:.0f}.")
    st.write(f"Overbooking by {x_best} would have earned **€{gain[0]:,.0f}** compared with not "
             f"overbooking, walking **{int(walked[0])}** guest(s).")
st.caption("Simulation assumes the hotel could always sell the extra rooms. "
           "The rolling rate only uses nights that finished at least 8 days earlier.")
