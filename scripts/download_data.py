"""Download the raw data (about 17 MB). No account or token needed."""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hotel_ob import config  # noqa: E402

if __name__ == "__main__":
    config.RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    if config.RAW_PATH.exists():
        print(f"Already have {config.RAW_PATH}")
    else:
        print(f"Downloading {config.DATA_URL} ...")
        urllib.request.urlretrieve(config.DATA_URL, config.RAW_PATH)
        print(f"Saved to {config.RAW_PATH}")
