# 🏨 How many rooms should a hotel overbook?

A data project on **119,390 real bookings** from two hotels in Portugal (2015-2017): every night, how many rooms should
a hotel sell above its capacity, and how much money does that earn compared with not overbooking? It predicts which
bookings will be lost at the last minute, turns those predictions into a nightly overbooking decision, and tests six
decision rules on eight months the models never saw. Everything ends in an interactive web app.

* **Report:** [`report/report.md`](report/report.md) (English, every finding has a number)
* **Live web app:** https://hotel-overbooking-ducngo.streamlit.app/ (or run locally: `streamlit run app/streamlit_app.py`)
* **2-minute video:** _<link>_
* **Mentors:** [`docs/MENTOR_GUIDE.md`](docs/MENTOR_GUIDE.md) maps the 14 weeks to the code and lists the traps
* **Original brief (Vietnamese):** [`docs/project_brief_vi.md`](docs/project_brief_vi.md)
* **Related project:** [Does LendingClub charge fair interest?](https://github.com/ducminhngo871/lendingclub-fair-rates)

## Headline results (City Hotel, Jan-Aug 2017, rules learned on 2015-2016 only, walking a guest costs 3x the room rate)

| Question | Answer |
| --- | --- |
| Do most cancellations cost money? | No. Only **11.9%** come in the last 7 days; 9.4% of active bookings are lost late |
| Can a model predict late losses? | Somewhat: AUC **0.65** (logistic) to **0.69** (gradient boosting) |
| Model trained on 2015-16, never updated? | **−€336k**: late losses halved (12.0% → 6.4%), so it overbooked far too much |
| Simple rule: last four weeks' late-loss rate? | **+€135k** (+2.3% of room revenue), walks guests on 109 of 243 nights |
| Same rule, allowing for clumped cancellations? | **+€183k** (+3.1%), walks guests on only **24** nights |
| Does that hold on another period? | Jul-Dec 2016: 10% *less* revenue than the simple rule, but walks on 10 nights instead of 60. Safer, not a free lunch |

AUC measures how well a score separates bookings that are lost late from those that are not (0.5 = coin flip).
"Walking" a guest means sending them to another hotel because every room is full. See the report for assumptions and limits.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
bash scripts/run_all.sh            # download (17 MB, no account), analyse, notebooks, tests (about 2 minutes)
streamlit run app/streamlit_app.py
```

The repository already contains the trained model (`models/`), result tables (`results/`), figures (`report/figures/`)
and the small files the app reads (`app/data/`), so **you can run the app and tests without downloading anything**.

## What is where

```
src/hotel_ob/        config.py  data.py (cleaning, label)  features.py  model.py  nights.py (room-nights)  policy.py (decision + backtest)
scripts/             download_data.py  run_pipeline.py  make_notebooks.py  run_all.sh
app/                 streamlit_app.py + pages/ (4 pages) + common.py + data/
notebooks/           01 explore, 02 predict late losses, 03 overbooking decisions
models/              trained logistic regression + meta.json
results/             tables (.csv) and key_facts.json used in the report
report/ docs/        research report + figures, mentor guide, original brief
tests/               46 automatic checks, including opening every app page
```

## The four app pages

1. **Booking risk:** enter a booking; see how likely it is to be lost late and what drives that.
2. **Tonight's decision:** pick a night in 2017, a walking cost and a safety limit; see how many rooms to overbook.
3. **Compare policies:** what each rule would have earned in 2017, and how many guests it walked.
4. **Explore the data:** cancellations by deposit, segment, channel and month.

## Method in five lines

1. Label what costs money: a booking is **lost late** if cancelled within 7 days of arrival or a no-show, among bookings still active 7 days out.
2. Predict it from 17 facts known at booking time. Never use `booking_changes`, `assigned_room_type`, `country` or `required_car_parking_spaces` (filled in later).
3. Split by time: learn from 2015-2016, judge on January-August 2017; check the late idea on July-December 2016 as well.
4. Decide with the newsvendor rule: overbook until P(late losses ≤ x) ≈ 1 / (1 + walking cost), with a binomial or a clumped (beta-binomial) distribution.
5. Replay each 2017 night with what really happened and count euros and walked guests.

## Checks

```bash
pytest -q          # 46 tests: cleaning, label, no leakage, room-nights, decision maths, no look-ahead, every app page
ruff check .
```

## Deploy the app (Streamlit Community Cloud)

1. Push this folder to GitHub (the `.gitignore` already keeps the raw data out).
2. On [share.streamlit.io](https://share.streamlit.io) choose the repository and set the main file to `app/streamlit_app.py`.
3. Paste the public link at the top of this README (done: see the live link above).

## Limits

The backtest assumes the hotel could always sell the extra rooms; only about half of the city hotel's 2017 nights were
fully booked, and counting only those nights cuts the gains by a third to a half. Room counts are estimated from the busiest night.
The data comes from two Portuguese hotels in 2015-2017. Educational project, not business advice.

Data: Antonio, N., de Almeida, A., & Nunes, L. (2019). Hotel booking demand datasets. *Data in Brief*, 22, 41-49
(via the [TidyTuesday](https://github.com/rfordatascience/tidytuesday/tree/master/data/2020/2020-02-11) copy).
