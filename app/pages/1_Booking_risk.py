import numpy as np
import pandas as pd
import streamlit as st

from common import load_meta, load_model

st.set_page_config(page_title="Booking risk", page_icon="🏨", layout="wide")
st.title("1 · Will this booking be lost late?")
st.caption("“Lost late” = cancelled within 7 days of arrival, or the guest never shows up. "
           "Only information the hotel has when the booking is made is used.")

model, meta = load_model(), load_meta()
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]

left, right = st.columns([1, 1])
with left:
    hotel = st.selectbox("Hotel", ["City Hotel", "Resort Hotel"])
    month = st.selectbox("Arrival month", MONTHS, index=6)
    lead_time = st.slider("Days booked in advance", 0, 400, 60)
    nights = st.slider("Nights", 1, 14, 3)
    adults = st.slider("Adults", 1, 4, 2)
    adr = st.slider("Room rate per night (EUR)", 20, 300, 100)
    deposit = st.selectbox("Deposit", ["No Deposit", "Non Refund", "Refundable"])
with right:
    segment = st.selectbox("Market segment", ["Online TA", "Offline TA/TO", "Direct", "Groups",
                                              "Corporate", "Complementary", "Aviation"])
    channel = st.selectbox("Distribution channel", ["TA/TO", "Direct", "Corporate", "GDS"])
    customer = st.selectbox("Customer type", ["Transient", "Transient-Party", "Contract", "Group"])
    requests = st.slider("Special requests", 0, 5, 0)
    prev_cancel = st.slider("Guest's previous cancellations", 0, 10, 0)
    repeated = st.checkbox("Returning guest")

row = pd.DataFrame([dict(
    lead_time=lead_time, nights=nights, adults=adults, previous_cancellations=prev_cancel,
    previous_bookings_not_canceled=1 if repeated else 0, total_of_special_requests=requests,
    adr=adr, days_in_waiting_list=0,
    is_repeated_guest=int(repeated), hotel=hotel, deposit_type=deposit, market_segment=segment,
    distribution_channel=channel, customer_type=customer, meal="BB", reserved_room_type="A",
    arrival_date_month=month)])
p = float(model.predict_proba(row)[0, 1])
base = meta["base_late_rate"]

st.divider()
a, b = st.columns([1, 2])
a.metric("Probability of being lost late", f"{p*100:.1f}%", f"{p/base:.1f}× the 2017 average ({base*100:.1f}%)",
         delta_color="inverse")

# Which inputs push this booking's risk up or down (logistic regression contributions)?
prep, clf = model.named_steps["prep"], model.named_steps["clf"]
x = prep.transform(row)
x = x.toarray()[0] if hasattr(x, "toarray") else np.asarray(x)[0]
contrib = pd.Series(x * clf.coef_[0], index=prep.get_feature_names_out())
contrib = contrib[contrib != 0]
contrib.index = contrib.index.str.replace("num__", "").str.replace("cat__", "")
top = contrib.reindex(contrib.abs().sort_values(ascending=False).index).head(5)
with b:
    st.markdown("**What drives this estimate** (log-odds contribution)")
    st.bar_chart(top.rename("contribution"), horizontal=True)
st.caption("The model was trained on 2015–2016 and over-predicts for 2017 (8.8% predicted vs 6.0% real), "
           "so read this as a ranking of risk rather than an exact probability.")
