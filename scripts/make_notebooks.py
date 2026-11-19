"""Builds the three walk-through notebooks in notebooks/.

Run after scripts/run_pipeline.py, then execute them:
    python scripts/make_notebooks.py
    python -m nbconvert --to notebook --execute --inplace notebooks/*.ipynb
"""
from pathlib import Path

import nbformat as nbf

OUT = Path(__file__).resolve().parents[1] / "notebooks"
SETUP = """import sys
sys.path.insert(0, "../src")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from hotel_ob import config, data, model, nights, policy
from hotel_ob.features import make_X
pd.options.display.float_format = "{:,.3f}".format
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False})"""


def md(s):
    return nbf.v4.new_markdown_cell(s.strip())


def code(s):
    return nbf.v4.new_code_cell(s.strip())


def save(name, cells):
    nb = nbf.v4.new_notebook()
    nb.cells = cells
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    OUT.mkdir(exist_ok=True)
    nbf.write(nb, OUT / name)


# ----------------------------------------------------------------------------------------------
save("01_explore_data.ipynb", [
    md("""# 1. Exploring the bookings (weeks 2-4)
**Question:** when do guests cancel, and which cancellations actually cost the hotel money?

For each chart, write one sentence of your own *before* reading the comment under it."""),
    code(SETUP),
    md("## The clean table\n`scripts/run_pipeline.py` already removed 182 impossible rows and added the label. Look at the columns: which ones does the hotel know **when the guest books**, and which are filled in later?"),
    code("df = pd.read_parquet(config.PROCESSED_DIR / 'bookings.parquet')\nprint(df.shape)\ndf.head(3).T"),
    code("df.groupby('hotel').agg(bookings=('is_canceled', 'size'), cancel_rate=('is_canceled', 'mean'))"),
    md("""## 37% cancelled. Should the hotel panic?
A cancellation two months before arrival is not a problem: the room can be sold again. Look at *when* guests cancel."""),
    code("""c = df[df.reservation_status == 'Canceled']
days = c.days_before_cancel.clip(upper=365)
ax = days.plot.hist(bins=np.r_[0, np.arange(8, 367, 7)], color='#a0aec0', figsize=(7, 3.2))
ax.set(xlabel='Days between cancellation and arrival', ylabel='Cancellations', title='When do guests cancel?')
plt.show()
print(f"median: {c.days_before_cancel.median():.0f} days before arrival;",
      f"within 7 days: {(c.days_before_cancel <= 7).mean():.1%} of cancellations")"""),
    md("""Only about one cancellation in eight comes in the last week. So the label that matters for overbooking is

> **lost late** = cancelled within 7 days of arrival, *or* a no-show,

measured on bookings that are still on the books 7 days before arrival (`active`), which is when the hotel decides how many rooms to overbook."""),
    code("df[df.active].groupby('hotel').late.mean().rename('share lost late')"),
    md("## Late losses changed over time"),
    code("""m = (df[df.active].assign(month=df.arrival.dt.to_period('M').dt.to_timestamp())
       .groupby(['month', 'hotel']).late.mean().unstack())
ax = (m * 100).plot(marker='o', ms=3, figsize=(8, 3.4), title='% of active bookings lost late')
ax.axvline(pd.Timestamp(config.TEST_START), color='black', ls='--', lw=1)
plt.show()
df[df.active].groupby(['hotel', df.arrival.dt.year]).late.mean().unstack()"""),
    md("""At the City Hotel the late-loss rate roughly **halved** between 2015 and 2017. Anything trained on the past will expect too many late losses in 2017. Keep this chart in mind: it explains the biggest result of the project (notebook 03)."""),
    md("## A strange category: non-refundable deposits"),
    code("""nr = df[df.deposit_type == 'Non Refund']
print(f"{len(nr):,} non-refundable bookings, {nr.is_canceled.mean():.1%} cancelled, only {(nr.is_canceled == 0).sum()} stayed")
print("median lead time:", nr.lead_time.median(), "days (all bookings:", df.lead_time.median(), ")")
nr.market_segment.value_counts().head()"""),
    md("""A non-refundable deposit should make people *less* likely to cancel. Here almost all of them cancelled, mostly groups and travel agents booking about six months ahead. These may be blocks of rooms held by agents, or a recording quirk. We keep the column (it is known at booking time) but treat its effect with suspicion."""),
    md("### Your turn\n1. Which market segment has the highest *late*-loss rate (not cancellation rate)? Is it the same as the highest cancellation rate?\n2. Do bookings with special requests get lost late less often? Why might that be?\n3. Find one column that you think the hotel only fills in *after* the booking. How could you check?"),
])

# ----------------------------------------------------------------------------------------------
save("02_predict_late_losses.ipynb", [
    md("""# 2. Predicting which bookings will be lost late (weeks 5-7)
We build the model step by step, and on the way fall into (and climb out of) the two classic traps: **leakage** and **random splits**."""),
    code(SETUP),
    code("df = pd.read_parquet(config.PROCESSED_DIR / 'bookings.parquet')\ntrain, test = data.time_split(df)\nprint(f'train: {train.sum():,} bookings before {config.TEST_START}, test: {test.sum():,} from then on')"),
    md("## Trap 1: leaky columns\nFirst predict *any* cancellation, once with only booking-time columns and once with four extra columns that the hotel only knows later."),
    code("""_, auc_clean, _ = model.fit_eval(df, 'is_canceled', train, test)
_, auc_leak, _ = model.fit_eval(df, 'is_canceled', train, test, cat=config.CAT_FEATURES + config.LEAKY_FEATURES)
print(f'honest AUC {auc_clean:.3f}   with leaky columns {auc_leak:.3f}')"""),
    code("""park = df[df.required_car_parking_spaces > 0]
print(f'{len(park):,} bookings asked for parking; cancelled: {park.is_canceled.sum()}, no-shows: {(park.reservation_status == "No-Show").sum()}')"""),
    md("Not one booking with a parking space was cancelled. That only makes sense if parking is recorded **on arrival**. Using it to predict cancellations is accidental cheating: the 0.06 jump in AUC is fake."),
    md("## Trap 2: a random split\nMixing 2015, 2016 and 2017 in both training and test lets the model learn from the future."),
    code("""rng = np.random.default_rng(0)
rand = pd.Series(rng.random(len(df)) < 0.75, index=df.index)
_, auc_random, _ = model.fit_eval(df, 'is_canceled', rand, ~rand)
print(f'time split {auc_clean:.3f}   random split {auc_random:.3f}')"""),
    md("## The real target: lost late\nOnly bookings still active 7 days out; train on 2015-16, test on 2017."),
    code("""tr, te = train & df.active, test & df.active
lr, auc_lr, p_lr = model.fit_eval(df, 'late', tr, te, 'logit')
gb, auc_gb, p_gb = model.fit_eval(df, 'late', tr, te, 'gb')
print(f'logistic AUC {auc_lr:.3f}   gradient boosting AUC {auc_gb:.3f}')
print(f'average prediction for 2017: {p_lr.mean():.1%}   what really happened: {df.loc[te, "late"].mean():.1%}')"""),
    md("Predicting *late* losses is much harder than predicting any cancellation. And the model expects far more late losses than 2017 delivered. A calibration plot shows it bin by bin:"),
    code("""cal = model.calibration_table(df.loc[te, 'late'], p_lr)
ax = cal.plot(x='predicted', y='actual', marker='o', figsize=(4.2, 4), legend=False, title='Calibration on 2017')
ax.plot([0, .3], [0, .3], ls='--', color='grey'); ax.set(xlim=(0, .3), ylim=(0, .3), ylabel='actual late-loss rate')
plt.show()
cal"""),
    md("## What drives the risk?\nEach coefficient multiplies the odds of being lost late. Numbers are scaled, so compare signs and sizes, not units."),
    code("model.top_coefficients(lr, 10)"),
    md("### Your turn\n1. Train the logistic model with `LATE_WINDOW_DAYS = 3` instead of 7 (use `data.add_labels(df, window=3)`). Does AUC go up or down? Why?\n2. Gradient boosting has a higher AUC. Would you use it in the overbooking rule? Hint: is AUC what the hotel cares about?\n3. Remove `deposit_type` from the inputs. How much does AUC fall?"),
])

# ----------------------------------------------------------------------------------------------
save("03_overbooking_decisions.ipynb", [
    md("""# 3. From predictions to decisions: how many rooms to overbook (weeks 8-9)
A model is only useful if it leads to a better decision, measured in **euros** and **walked guests**."""),
    code(SETUP),
    md("""## The newsvendor rule
Sell C + x rooms. Each booking is lost late with probability p. An empty room costs one room rate; a walked guest costs w room rates. The expected gain for each x:"""),
    code("""curve = policy.expected_curve(C=226, p=0.07, w=3)
ax = curve.plot.bar(x='x', y='net_gain', figsize=(8, 3), legend=False, color='#a0aec0',
                    title='Expected gain (in room rates) for each overbooking level, C=226, p=7%, w=3')
plt.show()
x = policy.best_overbook(226, 0.07, 3)
print('best x =', x, '| chance of walking anyone at that x:', f"{curve.p_any_walk[x]:.0%}")"""),
    md("**Try it:** change `w` to 1 and to 5. What happens to the best x, and why?"),
    md("## Room-nights and capacity\nThe data does not say how many rooms each hotel has. We use the busiest night ever (most guests in house)."),
    code("""n = pd.read_parquet(config.PROCESSED_DIR / 'room_nights.parquet')
cap = n.groupby('hotel').C.first()
print(cap)
n.head()"""),
    md("## Six rules, one test period\nEvery rule decides 7 days before the night, using only information available then."),
    code("""summary, detail = policy.backtest(n, cap, w=config.WALK_MULTIPLE)
summary[['hotel', 'policy', 'avg_overbook', 'gain_eur', 'gain_pct_revenue', 'nights_with_walk', 'guests_walked']]"""),
    md("""At the City Hotel the model that was never updated **loses** money. Look back at notebook 01: late losses halved, but the model still expects the 2015-16 level. The rolling rule, which only looks at the last four weeks, keeps up.

## Cancellations come in clumps
The newsvendor rule above assumes each booking cancels on its own, like a coin flip. Check that on 2015-16 nights: if it were true, the standardised error below would have variance 1."""),
    code("""t = policy.add_policy_inputs(n)
t = t[t.night < config.TEST_START].dropna(subset=['p_roll'])
z = (t.lost - t.booked * t.p_roll) / np.sqrt(t.booked * t.p_roll * (1 - t.p_roll))
print(t.groupby('hotel').apply(lambda g: z[g.index].var(), include_groups=False).rename('variance (1 = coin flips)'))"""),
    md("""Nights vary several times more than coin flips allow: groups cancel together, and bad weeks come in runs. The rule `Rolling rate + clumping` uses a beta-binomial distribution with the extra spread learned from 2015-16 (`policy.estimate_clumping`)."""),
    code("""pmf = pd.DataFrame({'coin flips': policy.loss_pmf(226, .07), 'clumped': policy.loss_pmf(226, .07, .029)})
pmf.loc[:45].plot(figsize=(7, 3), title='How many of 226 bookings are lost late? (p = 7%)'); plt.show()"""),
    md("""## Be honest about when you had the idea
The clumping rule was added *after* looking at the 2017 results. Judging it on the same months would be tuning on the test set. So test it on a period it never saw: learn from Jul 2015 - Jun 2016, test on Jul - Dec 2016."""),
    code("""val, _ = policy.backtest(n, cap, w=3, test_start=config.VALID_START, test_end=config.TEST_START)
val[val.policy.isin(['Rolling 28-night rate', 'Rolling rate + clumping', 'Fixed rule (2015-16)'])][
    ['hotel', 'policy', 'gain_eur', 'nights_with_walk', 'guests_walked']]"""),
    md("""In the validation period the clumping rule earns a bit less than the plain rolling rule, but walks guests on far fewer nights. It is the **safer** rule, not a magic money machine. (The model-based rules are left out here: the model was trained on these very nights.)"""),
    md("### Your turn\n1. Rerun the backtest with `w=1.5` and `w=5`. Which rule is best at each cost?\n2. Use `max_walk_prob=0.05` in `policy.backtest`. How much revenue does a 5% service-level limit cost the plain rolling rule?\n3. Change `config.ROLLING_NIGHTS` from 28 to 14 or 56 (pass `window=` to `policy.rolling_rate`). Is four weeks a good choice? Careful: which period are you allowed to pick it on?"),
])

print("Notebooks written to", OUT)
