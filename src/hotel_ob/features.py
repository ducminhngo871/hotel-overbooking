"""Turn bookings into model inputs."""
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import config


def make_X(df: pd.DataFrame, num=None, cat=None) -> pd.DataFrame:
    num = num or config.NUM_FEATURES
    cat = cat or config.CAT_FEATURES
    X = df[num + cat].copy()
    for c in cat:
        X[c] = X[c].astype(str)
    return X


def preprocessor(num=None, cat=None, scale=True, dense=False) -> ColumnTransformer:
    num = num or config.NUM_FEATURES
    cat = cat or config.CAT_FEATURES
    num_step = StandardScaler() if scale else "passthrough"
    return ColumnTransformer([
        ("num", num_step, num),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=20,
                              sparse_output=not dense), cat),
    ])
