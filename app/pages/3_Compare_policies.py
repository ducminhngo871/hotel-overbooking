import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import POLICY_COLORS, POLICY_ORDER, load_backtest, load_service_level

st.set_page_config(page_title="Compare policies", page_icon="🏨", layout="wide")
st.title("3 · Which overbooking rule earns the most?")
st.caption("Backtest on January–August 2017. Every rule only uses information available at the time.")

summary, detail = load_backtest()
w = st.select_slider("Cost of walking one guest (× room rate)",
                     options=sorted(summary.walk_multiple.unique()), value=3.0)
s = summary[summary.walk_multiple == w].copy()
s["gain_k"] = s.gain_eur / 1000

fig = px.bar(s, x="gain_k", y="policy", color="policy", facet_col="hotel", orientation="h",
             category_orders={"policy": POLICY_ORDER}, color_discrete_map=POLICY_COLORS,
             labels={"gain_k": "Extra revenue vs no overbooking (EUR thousands)", "policy": ""},
             text=s.gain_k.map(lambda v: f"{v:+,.0f}k"))
fig.update_layout(showlegend=False, height=420, margin=dict(t=40))
fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
st.plotly_chart(fig, width="stretch")

hotel = st.radio("Cumulative gain for", ["City Hotel", "Resort Hotel"], horizontal=True)
d = detail[(detail.hotel == hotel) & (detail.walk_multiple == w) & (detail.policy != "No overbooking")]
d = d.sort_values("night").assign(cum_k=lambda x: x.groupby("policy").gain_eur.cumsum() / 1000)
fig2 = px.line(d, x="night", y="cum_k", color="policy", color_discrete_map=POLICY_COLORS,
               labels={"cum_k": "EUR thousands", "night": ""})
fig2.add_hline(y=0, line_color="black", line_width=1)
fig2.update_layout(height=360, legend_title_text="", margin=dict(t=20))
st.plotly_chart(fig2, width="stretch")

st.dataframe(
    s[["hotel", "policy", "avg_overbook", "gain_eur", "gain_pct_revenue", "nights_with_walk", "guests_walked"]]
    .rename(columns={"avg_overbook": "avg rooms overbooked", "gain_eur": "gain (EUR)",
                     "gain_pct_revenue": "gain (% revenue)", "nights_with_walk": "nights walking someone",
                     "guests_walked": "guests walked"})
    .style.format({"avg rooms overbooked": "{:.1f}", "gain (EUR)": "{:+,.0f}", "gain (% revenue)": "{:+.1f}%"}),
    hide_index=True, width="stretch")
st.markdown(
    "**Why does the model lose money at the City Hotel?** It learned from 2015–2016, when many more "
    "guests cancelled late. In 2017 guests cancelled less, so it overbooked too much and walked too "
    "many guests. Updating with recent data fixes most of the problem.\n\n"
    "**Why does 'clumping' help?** Cancellations do not happen one by one like coin flips: on bad nights "
    "whole groups cancel, on good nights almost nobody does. In 2015–16 nights varied several times more than "
    "the coin-flip model expects. Allowing for that makes the rule overbook less and walk far fewer guests."
)

st.subheader("Revenue vs walked guests")
st.caption("Each point is the rolling rule with a cap on the chance of walking anyone on a night "
           f"(walking cost {3.0:g}× room rate). Stars: rolling rule + clumping, no cap.")
sl = load_service_level()
fig3 = go.Figure()
for h, c in [("City Hotel", "#2b6cb0"), ("Resort Hotel", "#dd6b20")]:
    t = sl[(sl.hotel == h) & (sl.policy == "Rolling 28-night rate")].sort_values("max_walk_prob")
    fig3.add_scatter(x=t.nights_with_walk / t.nights * 100, y=t.gain_eur / 1000, mode="lines+markers",
                     name=f"{h}: rolling + cap", line_color=c,
                     text=[f"cap {v:.0%}" if v < 1 else "no cap" for v in t.max_walk_prob],
                     hovertemplate="%{text}<br>%{x:.0f}% of nights walk someone<br>%{y:,.0f}k EUR<extra></extra>")
    cl = sl[(sl.hotel == h) & (sl.policy == "Rolling rate + clumping") & (sl.max_walk_prob == 1.0)]
    fig3.add_scatter(x=cl.nights_with_walk / cl.nights * 100, y=cl.gain_eur / 1000, mode="markers",
                     marker=dict(symbol="star", size=16, color=c, line=dict(color="black", width=1)),
                     name=f"{h}: rolling + clumping")
fig3.update_layout(xaxis_title="% of nights with at least one walked guest", yaxis_title="EUR thousands",
                   height=380, margin=dict(t=20))
st.plotly_chart(fig3, width="stretch")
st.caption("Honest check: 'Rolling rate + clumping' was added after seeing these 2017 results. On Jul–Dec 2016, "
           "a period it never saw, it earned about 10% less than the plain rolling rule at the City Hotel but "
           "walked guests on 10 nights instead of 60. It is the *safer* rule, not a guaranteed richer one.")
