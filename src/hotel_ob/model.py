"""Train and evaluate cancellation models."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline

from . import config
from .features import make_X, preprocessor


def build(kind: str = "logit", num=None, cat=None) -> Pipeline:
    if kind == "logit":
        return Pipeline([("prep", preprocessor(num, cat)),
                         ("clf", LogisticRegression(max_iter=2000))])
    if kind == "gb":
        return Pipeline([("prep", preprocessor(num, cat, scale=False, dense=True)),
                         ("clf", HistGradientBoostingClassifier(random_state=0))])
    raise ValueError(kind)


def fit_eval(df, target, train_mask, test_mask, kind="logit", num=None, cat=None):
    num = num or config.NUM_FEATURES
    cat = cat or config.CAT_FEATURES
    X = make_X(df, num, cat)
    model = build(kind, num, cat).fit(X[train_mask], df.loc[train_mask, target])
    p = model.predict_proba(X[test_mask])[:, 1]
    return model, roc_auc_score(df.loc[test_mask, target], p), p


def calibration_table(y, p, bins: int = 10) -> pd.DataFrame:
    d = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p)})
    d["bin"] = pd.qcut(d.p, bins, labels=False, duplicates="drop")
    return (d.groupby("bin")
             .agg(predicted=("p", "mean"), actual=("y", "mean"), n=("y", "size"))
             .reset_index())


def top_coefficients(model: Pipeline, k: int = 10) -> pd.DataFrame:
    names = model.named_steps["prep"].get_feature_names_out()
    coefs = model.named_steps["clf"].coef_[0]
    out = pd.DataFrame({"feature": names, "coef": coefs})
    out["feature"] = out.feature.str.replace("num__", "").str.replace("cat__", "")
    out["odds_multiplier"] = np.exp(out.coef)
    order = out.coef.abs().sort_values(ascending=False).index
    return out.reindex(order).head(k).reset_index(drop=True)
