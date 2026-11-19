#!/usr/bin/env bash
# Run the whole project, start to finish (about 1 minute after the 17 MB download).
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"

$PY scripts/download_data.py                  # 0. get the data (no account needed)
$PY scripts/run_pipeline.py                   # 1-6. clean, explore, model, room-nights, backtest, app data
$PY scripts/make_notebooks.py                 # 7. rebuild the walk-through notebooks ...
$PY -m nbconvert --to notebook --execute --inplace notebooks/*.ipynb   # ... and run them
$PY -m pytest -q                              # 8. checks
$PY -m ruff check .
echo "All done. Start the app with:  streamlit run app/streamlit_app.py"
