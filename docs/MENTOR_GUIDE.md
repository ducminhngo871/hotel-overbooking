# Mentor guide

This repository is the **reference solution** to the 14-week project in `docs/project_brief_vi.md`
("How many rooms should a hotel overbook?"). Use it as an answer key, a source of checkpoints, and a map of
where the traps are. Do not hand it to the student on day one: the learning is in building it.

## How the pieces fit

```
data/raw/hotels.csv  --data.py (clean + label)-->  data/processed/bookings.parquet
                                   |
          model.py (logistic, gradient boosting, AUC, calibration)  --> models/
          nights.py (bookings -> one row per hotel and night)        --> data/processed/room_nights.parquet
          policy.py (newsvendor decision, six rules, backtest)       --> results/, report/figures/
                                   |
                         app/data/  -->  streamlit run app/streamlit_app.py
```

`scripts/run_pipeline.py` runs all of it (about 15 seconds). `scripts/run_all.sh` adds the download, the notebooks and
the checks (about 2 minutes).

| Folder | What is in it | Student writes it in |
| --- | --- | --- |
| `src/hotel_ob/data.py` | cleaning rules, late-loss label, time split | weeks 2-3 |
| `src/hotel_ob/features.py` | model inputs (booking-time only) | week 5 |
| `src/hotel_ob/model.py` | logistic, gradient boosting, AUC, calibration, coefficients | weeks 5-7 |
| `src/hotel_ob/nights.py` | room-nights, capacity estimate | week 8 |
| `src/hotel_ob/policy.py` | newsvendor rule, clumping, service level, backtest | weeks 8-9 |
| `notebooks/` | three walk-throughs with "Your turn" questions | weeks 2-9 |
| `app/` | the 4-page Streamlit app | weeks 10-12 |
| `tests/` | 46 automatic checks | week 12 |
| `report/report.md` | the research report | weeks 13-14 |

## Week by week

| Week | Student does | Look at | Checkpoint question to ask |
| --- | --- | --- | --- |
| 1 | VS Code, Python, Git, first repo | `README.md`, `.gitignore` | Why does the raw data stay out of GitHub, but `app/data/` goes in? |
| 2 | Load, clean, save Parquet | `data.clean`, notebook 01 | How many rows did each rule remove, and why is each one impossible? |
| 3 | Charts: when do guests cancel? | notebook 01 | 37% of bookings were cancelled. Why is that the wrong number for overbooking? |
| 4 | Define "lost late"; drift over time | `data.add_labels`, figure 03 | What happens to the label if the window is 3 days instead of 7? |
| 5 | Features, time split, logistic | `features.py`, notebook 02 | Which columns does the hotel only know after the booking? How did you check? |
| 6 | Gradient boosting | `model.build("gb")` | Gradient boosting has a higher AUC. Does that make it the better choice for the decision? |
| 7 | AUC, calibration, coefficients | notebook 02, `results/` | The model predicts 8.8% for 2017; reality is 6.0%. Which matters more here, AUC or calibration? |
| 8 | Newsvendor rule, room-nights | `policy.expected_curve`, notebook 03 | Why should the hotel stop at the 25th percentile of late losses when w = 3? |
| 9 | Backtest six rules; validation | `policy.backtest`, notebook 03 | You had the clumping idea after seeing 2017. What must you do before you may claim it works? |
| 10-12 | Streamlit app, tests, deploy | `app/`, `tests/` | Could a hotel manager with no coding background use page 2 unaided? |
| 13-14 | Report, README, hotel interview | `report/report.md` | Does every finding carry one concrete number? Did a real hotel confirm or contradict w = 3? |

Weeks 8 and 9 are the heaviest. If the student is behind, the brief allows stretching to 16 weeks.

## The traps (the best teaching material in the project)

1. **"Cancelled" is not "lost money".** 37% of bookings were cancelled, but the median cancellation came 56 days
   before arrival. Only late cancellations and no-shows leave a room empty. The label in `data.add_labels` uses the
   `reservation_status_date` only to *build* the label; it must never become an input.
2. **Leaky columns.** `booking_changes` keeps counting until check-in, `assigned_room_type` is set at check-in, and
   `required_car_parking_spaces` is almost certainly recorded on arrival: all 7,409 bookings with parking checked in.
   With them, AUC jumps from 0.805 to 0.865. `tests/test_features.py` enforces the exclusion.
3. **Random split.** Mixing years gives AUC 0.830 instead of 0.805. A hotel only ever knows the past.
4. **Drift.** City-hotel late losses fell from 12.0% (2015) to 6.4% (2017). A good-looking model trained on the past
   loses €336k. Ask the student to plot predicted vs actual by month *before* running the backtest; they will see it coming.
5. **Look-ahead in the rolling rate.** The decision is made 7 days before the night, so the rolling rate may only use
   nights that ended at least 8 days earlier (`policy.rolling_rate`, lag = 8). Using `shift(1)` instead is a quiet
   cheat. `tests/test_policy.py::test_rolling_rate_never_looks_ahead` catches it.
6. **Capacity is estimated from the same data.** The data has no room count, so C = busiest night. Consequence: any
   check that caps sales at real bookings can never walk a guest. The reference solution fell into this (report,
   Section 6, mistake 6). Good students will spot the circularity themselves.
7. **Coin-flip cancellations.** The binomial model assumes bookings cancel independently. Real nights vary 4.7-6.3 times
   more. Ignoring it makes the rule overbook too boldly. The beta-binomial fix has a single parameter, learned on
   2015-16 (`policy.estimate_clumping`).
8. **Tuning on the test set.** The clumping rule was found by looking at 2017. The honest response is the
   July-December 2016 validation in `results/policy_validation_2016H2.csv`, where it earns *less* but walks far fewer
   guests. The student should report both, not just the flattering one.
9. **Non-refundable deposits that everyone cancels.** 99.4% of 14,586 "Non Refund" bookings were cancelled. It is
   known at booking time, so it stays as an input, but its huge coefficient is not a causal finding.

## Setup notes

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
bash scripts/run_all.sh
```

* No Kaggle account is needed: the data (17 MB) comes from the TidyTuesday GitHub copy.
* Python 3.10 or newer. Any ordinary laptop works: the data is 17 MB.
* To rebuild the notebooks: `python scripts/make_notebooks.py`, then
  `python -m nbconvert --to notebook --execute --inplace notebooks/*.ipynb`.

## Mapping to the completion checklist

| Checklist item | Where it is satisfied |
| --- | --- |
| Label = late cancellations and no-shows, not all cancellations | `data.add_labels`, `tests/test_label.py` |
| No look-ahead columns in the model | `config.LEAKY_FEATURES`, `tests/test_features.py` |
| Time-based split | `data.time_split`, `config.TEST_START` |
| Every chart has a title, units and a sentence | `report/figures/`, `report/report.md` |
| Overbooking decision explained with the newsvendor rule | `policy.expected_curve`, app page 2 |
| At least four rules compared in euros and walked guests | `results/policy_backtest.csv`, app page 3 |
| Sensitivity to the walking cost | `results/policy_backtest.csv` (w = 1 to 5), figure 08 |
| 4 pages, public link | `app/`; deploy `app/streamlit_app.py` on Streamlit Community Cloud |
| Automatic tests, app runs | `tests/` (includes opening every page) |
| English report with "mistakes" section | `report/report.md`, Section 6 |
| Conversation with a real hotel | `report/report.md`, Section 8 (left for the student) |

## Honest limits to tell the student

* The backtest assumes every extra room could be sold. Counting only nights that were already fully booked cuts the
  gains by a third to a half. The direction of the findings does not change.
* Results come from two Portuguese hotels in 2015-2017, one of which (the city hotel) changed a lot over that time.
* The clumping rule is safer in both test periods but earns more in only one of them. Do not let the student oversell it.
