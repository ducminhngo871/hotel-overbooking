import plotly.express as px
import streamlit as st

from common import load_explore

st.set_page_config(page_title="Explore the data", page_icon="🏨", layout="wide")
st.title("4 · Explore the data")

monthly, explore = load_explore()
m = monthly.melt(id_vars="month", var_name="hotel", value_name="late_rate")
m["late_rate"] *= 100
fig = px.line(m, x="month", y="late_rate", color="hotel", markers=True,
              labels={"late_rate": "% of bookings lost late", "month": ""},
              color_discrete_map={"City Hotel": "#2b6cb0", "Resort Hotel": "#dd6b20"})
fig.add_vline(x="2017-01-01", line_dash="dash")
fig.update_layout(title="Late cancellations over time", height=360, legend_title_text="")
st.plotly_chart(fig, width="stretch")

by = st.selectbox("Break down by", ["deposit_type", "market_segment", "distribution_channel"],
                  format_func=lambda c: c.replace("_", " ").capitalize())
hotels = st.multiselect("Hotels", ["City Hotel", "Resort Hotel"], default=["City Hotel", "Resort Hotel"])
e = explore[explore.hotel.isin(hotels)]
g = (e.assign(cancels=e.cancel_rate * e.bookings, lates=e.late_rate * e.bookings)
       .groupby(by)[["bookings", "cancels", "lates"]].sum())
g["% cancelled (any time)"] = g.cancels / g.bookings * 100
g["% lost late"] = g.lates / g.bookings * 100
g = g[g.bookings >= 50].sort_values("% cancelled (any time)")
fig2 = px.bar(g.reset_index(), y=by, x=["% cancelled (any time)", "% lost late"], barmode="group",
              orientation="h", labels={"value": "%", by: "", "variable": ""})
fig2.update_layout(height=380)
st.plotly_chart(fig2, width="stretch")
st.caption("Look at 'Non Refund': almost every one of these bookings was cancelled, mostly by groups and "
           "travel agents booking months ahead. Is that what you would expect from a non-refundable deposit?")
