"""Run the whole analysis: clean -> explore -> model -> room-nights -> backtest -> figures -> app data.

Usage:  python scripts/download_data.py && python scripts/run_pipeline.py
"""
import json
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hotel_ob import config, data, model, policy  # noqa: E402
from hotel_ob import nights as nights_mod
from hotel_ob.features import make_X  # noqa: E402

for d in [config.PROCESSED_DIR, config.RESULTS_DIR, config.FIG_DIR, config.MODEL_DIR, config.APP_DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "font.size": 10})
BLUE, ORANGE, GREY, RED, GREEN, PURPLE = "#2b6cb0", "#dd6b20", "#a0aec0", "#c53030", "#2f855a", "#6b46c1"
facts = {}


def save(fig, name):
    fig.tight_layout()
    fig.savefig(config.FIG_DIR / name, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 1. clean
raw = data.load_raw()
df, clean_log = data.clean(raw)
df = data.add_labels(df)
df.to_parquet(config.PROCESSED_DIR / "bookings.parquet")
facts["cleaning"] = clean_log
print("cleaning:", clean_log)

# ---------------------------------------------------------------- 2. explore
cancel = df[df.reservation_status == "Canceled"]
facts["explore"] = {
    "bookings": len(df),
    "cancel_rate_all": round(df.is_canceled.mean(), 4),
    "cancel_rate_by_hotel": df.groupby("hotel").is_canceled.mean().round(4).to_dict(),
    "status_counts": df.reservation_status.value_counts().to_dict(),
    "median_days_cancel_before_arrival": float(cancel.days_before_cancel.median()),
    "share_cancels_within_7d": round((cancel.days_before_cancel <= 7).mean(), 4),
    "late_rate_active_by_hotel": df[df.active].groupby("hotel").late.mean().round(4).to_dict(),
    "nonrefund_cancel_rate": round(df[df.deposit_type == "Non Refund"].is_canceled.mean(), 4),
    "nonrefund_n": int((df.deposit_type == "Non Refund").sum()),
    "nonrefund_median_lead": float(df[df.deposit_type == "Non Refund"].lead_time.median()),
    "all_median_lead": float(df.lead_time.median()),
}

fig, ax = plt.subplots(figsize=(7, 3.6))
days = cancel.days_before_cancel[cancel.days_before_cancel <= 364]
bins = np.r_[0, np.arange(8, 366, 7)]          # first bar = days 0-7 exactly
ax.hist(days, bins=bins, color=GREY, edgecolor="white")
ax.hist(days[days <= 7], bins=bins, color=RED, edgecolor="white", label="Within 7 days (late)")
ax.set(title="Most cancellations happen weeks before arrival",
       xlabel="Days between cancellation and arrival (cancellations within one year)", ylabel="Cancellations")
ax.legend(frameon=False)
save(fig, "01_cancel_timing.png")

fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
dep = df.groupby("deposit_type").is_canceled.mean().sort_values()
axes[0].barh(dep.index, dep.values * 100, color=[BLUE, BLUE, RED])
axes[0].set(title="Cancellation rate by deposit type", xlabel="% cancelled")
seg = df.groupby("market_segment").is_canceled.mean().sort_values()
seg = seg[seg.index != "Undefined"]
axes[1].barh(seg.index, seg.values * 100, color=BLUE)
axes[1].set(title="Cancellation rate by market segment", xlabel="% cancelled")
save(fig, "02_cancel_by_deposit_segment.png")

monthly = (df[df.active].assign(month=lambda d: d.arrival.dt.to_period("M").dt.to_timestamp())
           .groupby(["month", "hotel"]).late.mean().unstack())
monthly.to_csv(config.RESULTS_DIR / "late_rate_by_month.csv")
yearly = df[df.active].groupby(["hotel", df.arrival.dt.year]).late.mean()
facts["late_rate_by_year"] = {h: {int(y): round(float(v), 4) for y, v in yearly[h].items()}
                              for h in yearly.index.get_level_values(0).unique()}
fig, ax = plt.subplots(figsize=(8, 3.6))
for h, c in [("City Hotel", BLUE), ("Resort Hotel", ORANGE)]:
    ax.plot(monthly.index, monthly[h] * 100, marker="o", ms=3, color=c, label=h)
ax.axvline(pd.Timestamp(config.TEST_START), color="black", ls="--", lw=1)
ax.text(pd.Timestamp(config.TEST_START), ax.get_ylim()[1] * 0.95, "  test period", va="top")
ax.set(title="Late cancellations became rarer over time", ylabel="% of bookings lost late")
ax.legend(frameon=False)
save(fig, "03_late_rate_by_month.png")

# ---------------------------------------------------------------- 3. models
train, test = data.time_split(df)
_, auc_clean, _ = model.fit_eval(df, "is_canceled", train, test)
_, auc_leak, _ = model.fit_eval(df, "is_canceled", train, test,
                                cat=config.CAT_FEATURES + config.LEAKY_FEATURES)
rng = np.random.default_rng(0)
rand = pd.Series(rng.random(len(df)) < 0.75, index=df.index)
_, auc_random, _ = model.fit_eval(df, "is_canceled", rand, ~rand)

tr, te = train & df.active, test & df.active
late_lr, auc_late_lr, p_te = model.fit_eval(df, "late", tr, te, "logit")
_, auc_late_gb, _ = model.fit_eval(df, "late", tr, te, "gb")
df["p"] = late_lr.predict_proba(make_X(df))[:, 1]
joblib.dump(late_lr, config.MODEL_DIR / "late_cancel_logit.joblib")

facts["models"] = {
    "auc_is_canceled_clean_timesplit": round(auc_clean, 3),
    "auc_is_canceled_with_leaky_columns": round(auc_leak, 3),
    "auc_is_canceled_random_split": round(auc_random, 3),
    "auc_late_logit": round(auc_late_lr, 3),
    "auc_late_gradient_boosting": round(auc_late_gb, 3),
    "late_rate_train": round(float(df.loc[tr, "late"].mean()), 4),
    "late_rate_test": round(float(df.loc[te, "late"].mean()), 4),
    "mean_pred_test": round(float(p_te.mean()), 4),
}
print("models:", facts["models"])

fig, ax = plt.subplots(figsize=(7, 2.8))
labels = ["Honest model\n(time split)", "Random split\n(peeks at future)", "With leaky columns"]
vals = [auc_clean, auc_random, auc_leak]
ax.barh(labels, vals, color=[GREEN, ORANGE, RED])
for i, v in enumerate(vals):
    ax.text(v + 0.003, i, f"{v:.3f}", va="center")
ax.set(xlim=(0.75, 0.9), title="Two ways to fool yourself: leakage and random splits",
       xlabel="AUC on 2017 bookings (predicting any cancellation)")
save(fig, "04_leakage_auc.png")

cal = model.calibration_table(df.loc[te, "late"], p_te)
cal.to_csv(config.RESULTS_DIR / "calibration_2017.csv", index=False)
fig, ax = plt.subplots(figsize=(4.6, 4.2))
ax.plot([0, 0.3], [0, 0.3], color=GREY, ls="--", label="Perfect calibration")
ax.plot(cal.predicted, cal.actual, marker="o", color=BLUE, label="Model on 2017")
ax.set(xlim=(0, 0.3), ylim=(0, 0.3), xlabel="Predicted late-loss probability",
       ylabel="Actual late-loss rate", title="The model over-predicts in 2017")
ax.legend(frameon=False)
save(fig, "05_calibration.png")

coefs = model.top_coefficients(late_lr, 10)
coefs.to_csv(config.RESULTS_DIR / "top_coefficients.csv", index=False)

# ---------------------------------------------------------------- 4. room-nights
nights = nights_mod.to_room_nights(df, "p")
cap = nights_mod.estimate_capacity(nights)
nights["C"] = nights.hotel.map(cap)
nights.to_parquet(config.PROCESSED_DIR / "room_nights.parquet")
facts["capacity_estimate"] = cap.to_dict()
facts["share_nights_booked_above_capacity"] = (nights.booked > nights.C).groupby(nights.hotel).mean().round(3).to_dict()
facts["share_nights_near_full"] = (nights.booked >= 0.95 * nights.C).groupby(nights.hotel).mean().round(3).to_dict()

# ---------------------------------------------------------------- 5. backtest
summaries, details = [], []
for w in config.WALK_GRID:
    s, d = policy.backtest(nights, cap, w)
    summaries.append(s)
    details.append(d)
summary = pd.concat(summaries, ignore_index=True)
detail = pd.concat(details, ignore_index=True)
summary.to_csv(config.RESULTS_DIR / "policy_backtest.csv", index=False)
main = summary[summary.walk_multiple == config.WALK_MULTIPLE]
print(main[["hotel", "policy", "avg_overbook", "gain_eur", "gain_pct_revenue", "nights_with_walk"]].round(1).to_string(index=False))

POL_ORDER = policy.POLICIES
POL_COL = dict(zip(POL_ORDER, [GREY, ORANGE, RED, GREEN, BLUE, PURPLE]))

fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
for ax, h in zip(axes, ["City Hotel", "Resort Hotel"]):
    m = main[main.hotel == h].set_index("policy").loc[POL_ORDER]
    vals = m.gain_eur / 1000
    ax.barh(m.index, vals, color=[POL_COL[p] for p in m.index])
    ax.axvline(0, color="black", lw=0.8)
    span = max(vals.max(), 0) - min(vals.min(), 0)
    for i, v in enumerate(vals):
        if v < -0.25 * span:   # long negative bar: write the label inside it
            ax.text(v / 2, i, f"{v:+,.0f}k", va="center", ha="center", color="white", fontweight="bold")
        elif v < 0:
            ax.text(v, i, f"{v:+,.0f}k ", va="center", ha="right")
        else:
            ax.text(v, i, f" {v:+,.0f}k", va="center", ha="left")
    ax.set_xlim(min(vals.min(), 0) * 1.1 - (0 if vals.min() < -0.25 * span else 0.15 * span), max(vals.max(), 0) * 1.25 + 5)
    ax.set_title(h)
axes[0].invert_yaxis()
fig.supxlabel("Extra revenue vs no overbooking, Jan-Aug 2017 (EUR thousands)", fontsize=10)
fig.suptitle(f"Backtest of overbooking policies (walking a guest costs {config.WALK_MULTIPLE:g}x the room rate)",
             fontweight="bold")
save(fig, "06_policy_backtest.png")

city = detail[(detail.hotel == "City Hotel") & (detail.walk_multiple == config.WALK_MULTIPLE)]
fig, ax = plt.subplots(figsize=(8, 3.6))
for p in POL_ORDER[1:]:
    c = city[city.policy == p].sort_values("night")
    ax.plot(c.night, c.gain_eur.cumsum() / 1000, color=POL_COL[p], label=p)
ax.axhline(0, color="black", lw=0.8)
ax.set(title="City Hotel: cumulative gain through 2017", ylabel="EUR thousands")
ax.legend(frameon=False, fontsize=8)
save(fig, "07_city_cumulative.png")

sens = summary[(summary.hotel == "City Hotel") & summary.policy.isin(POL_ORDER[1:])]
fig, ax = plt.subplots(figsize=(7, 3.6))
for p in POL_ORDER[1:]:
    s = sens[sens.policy == p]
    ax.plot(s.walk_multiple, s.gain_eur / 1000, marker="o", color=POL_COL[p], label=p)
ax.axhline(0, color="black", lw=0.8)
ax.set(title="City Hotel: how much depends on the cost of walking a guest?",
       xlabel="Cost of walking one guest (multiple of room rate)", ylabel="EUR thousands")
ax.legend(frameon=False, fontsize=8)
save(fig, "08_sensitivity_walk_cost.png")

# ---------------------------------------------------------------- 5b. validation period
# "Rolling rate + clumping" was added after seeing the 2017 results, so check it on a period it never saw:
# learn from Jul 2015 - Jun 2016, test on Jul - Dec 2016. Model-based policies are left out here because the
# model was trained on all of 2015-16 (it has seen these nights).
RATE_POLICIES = ["No overbooking", "Fixed rule (2015-16)", "Rolling 28-night rate", "Rolling rate + clumping"]
val = policy.backtest(nights, cap, config.WALK_MULTIPLE, test_start=config.VALID_START, test_end=config.TEST_START)[0]
val = val[val.policy.isin(RATE_POLICIES)].replace({"Fixed rule (2015-16)": "Fixed rule (Jul 15-Jun 16)"})
val.to_csv(config.RESULTS_DIR / "policy_validation_2016H2.csv", index=False)
print("validation, Jul-Dec 2016:")
print(val[["hotel", "policy", "avg_overbook", "gain_eur", "nights_with_walk", "guests_walked"]].round(1).to_string(index=False))
facts["validation_2016H2_w3"] = {f"{r.hotel} | {r.policy}": {"gain_eur": round(r.gain_eur), "nights_with_walk": r.nights_with_walk}
                                 for r in val.itertuples()}
facts["clumping_rho_2017"] = main.groupby("hotel").rho.first().round(4).to_dict()

# ---------------------------------------------------------------- 5c. service-level limit
# Real hotels avoid walking guests too often. Cap the chance of walking anyone on a night.
sl_rows = []
for s_max in config.WALK_PROB_GRID:
    s_sum, _ = policy.backtest(nights, cap, config.WALK_MULTIPLE, max_walk_prob=s_max)
    sl_rows.append(s_sum[s_sum.policy.isin(["Rolling 28-night rate", "Rolling rate + clumping"])])
sl = pd.concat(sl_rows, ignore_index=True)
sl.to_csv(config.RESULTS_DIR / "service_level_tradeoff.csv", index=False)
print("service level (rolling rule):")
print(sl[["hotel", "policy", "max_walk_prob", "avg_overbook", "gain_eur", "nights_with_walk"]].round(2).to_string(index=False))

fig, ax = plt.subplots(figsize=(7, 3.8))
for h, c in [("City Hotel", BLUE), ("Resort Hotel", ORANGE)]:
    t = sl[(sl.hotel == h) & (sl.policy == "Rolling 28-night rate")].sort_values("max_walk_prob")
    share = t.nights_with_walk / t.nights * 100
    ax.plot(share, t.gain_eur / 1000, marker="o", color=c, label=h)
    t = t.assign(share=share)
    for (sh, g), grp in t.groupby(["share", "gain_eur"]):     # several caps can give the same result
        lab = "no limit" if grp.max_walk_prob.max() >= 1 else f"{grp.max_walk_prob.min():.0%}"
        if len(grp) > 1 and lab == "no limit":
            lab = f">={grp.max_walk_prob.min():.0%} / no limit"
        ax.annotate(lab, (sh, g / 1000), textcoords="offset points", xytext=(4, -10), fontsize=7, color=c)
    cl = main[(main.hotel == h) & (main.policy == "Rolling rate + clumping")].iloc[0]
    ax.scatter(cl.nights_with_walk / cl.nights * 100, cl.gain_eur / 1000, marker="*", s=180, color=c,
               edgecolor="black", zorder=5, label=f"{h}: rolling + clumping (no limit)")
ax.axhline(0, color="black", lw=0.8)
ax.set(title="In 2017, walking fewer guests also earned more",
       xlabel="% of nights on which at least one guest is walked (Jan-Aug 2017)",
       ylabel="Extra revenue, EUR thousands")
ax.legend(frameon=False, fontsize=7, loc="center right", title="Lines: rolling rule with a cap on P(walk anyone)", title_fontsize=7)
save(fig, "09_service_level_tradeoff.png")

facts["backtest_w3"] = {f"{r.hotel} | {r.policy}": {"gain_eur": round(r.gain_eur), "gain_pct": round(r.gain_pct_revenue, 2),
                                                    "avg_overbook": round(r.avg_overbook, 1),
                                                    "nights_with_walk": r.nights_with_walk, "guests_walked": r.guests_walked,
                                                    "gain_eur_full_nights_only": round(r.gain_eur_full_nights)}
                        for r in main.itertuples()}

# ---------------------------------------------------------------- 6. app data
app_nights = policy.add_policy_inputs(nights)
app_nights.to_parquet(config.APP_DATA_DIR / "room_nights.parquet")
summary.to_csv(config.APP_DATA_DIR / "policy_backtest.csv", index=False)
sl.to_csv(config.APP_DATA_DIR / "service_level_tradeoff.csv", index=False)
detail.to_parquet(config.APP_DATA_DIR / "policy_detail.parquet")
monthly.to_csv(config.APP_DATA_DIR / "late_rate_by_month.csv")
joblib.dump(late_lr, config.APP_DATA_DIR / "late_cancel_logit.joblib")
explore = (df.groupby(["hotel", "deposit_type", "market_segment", "distribution_channel"])
             .agg(bookings=("is_canceled", "size"), cancel_rate=("is_canceled", "mean"),
                  late_rate=("late", "mean")).reset_index())
explore.to_csv(config.APP_DATA_DIR / "explore.csv", index=False)
meta = {"capacity": cap.to_dict(), "base_late_rate": facts["models"]["late_rate_test"],
        "test_start": config.TEST_START, "walk_multiple": config.WALK_MULTIPLE,
        "clumping_rho": facts["clumping_rho_2017"]}
json.dump(meta, open(config.APP_DATA_DIR / "meta.json", "w"), indent=2)
json.dump(meta, open(config.MODEL_DIR / "meta.json", "w"), indent=2)

json.dump(facts, open(config.RESULTS_DIR / "key_facts.json", "w"), indent=2, default=str)
print("Done. Figures in report/figures, tables in results/.")
