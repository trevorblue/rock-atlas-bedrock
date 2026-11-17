"""Module B - Sell-off Alert: how likely is heavy foreign selling next period?

Target   heavy_next = next period's net foreign flow is in the worst SELLOFF_QUANTILE of
         flows seen so far (threshold re-estimated inside every training window).
Inputs   live model: this period's and the last 3 periods' net foreign flow (config.SELLOFF_FEATURES).
         Also built and compared out-of-sample (robustness.selloff_feature_sets): + KES/USD, CBR,
         T-bills, inflation, oil, US yields, dollar index, VIX; + NSE returns, trading activity,
         concentration. With ~140 monthly points the extra inputs made it worse (noise).
Models   climatology (base rate), logistic regression, shallow XGBoost.
Testing  walk-forward: train on everything known up to month t, predict t+1, roll on.
Output   probability, a HIGH RISK / NO CALL signal, and the top drivers. There is no LOW RISK:
         low readings were followed by heavy selling almost as often as normal (see config).

Frequency follows the flow data: monthly with CMA data; weekly if Rock supplies
data/rock/foreign_flows.csv with weekly periods (macro is then carried forward).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from .config import (HIGH_RISK_PROB, MIN_TRAIN_PERIODS, RANDOM_STATE, SELLOFF_FEATURES,
                     SELLOFF_QUANTILE)

FEATURE_LABELS = {
    "flow": "Net foreign flow this period",
    "flow_3": "Net foreign flow, last 3 periods",
    "usdkes_chg_1": "KES/USD change, 1 period",
    "usdkes_chg_3": "KES/USD change, 3 periods",
    "cbr": "Central Bank Rate",
    "cbr_chg_3": "CBR change, 3 periods",
    "tbill_91d_chg_3": "91-day T-bill change, 3 periods",
    "inflation_12m": "Inflation (12-month)",
    "brent_chg_1": "Oil price change",
    "us10y_chg_3": "US 10-year yield change",
    "dxy_chg_1": "US dollar index change",
    "vix": "VIX (global risk appetite)",
    "nasi_ret_1": "NSE All-Share return, 1 period",
    "nasi_ret_3": "NSE All-Share return, 3 periods",
    "value_chg_3": "Market turnover change",
    "top5_share": "Top-5 share of trading",
}


def infer_freq(periods: pd.Series) -> str:
    step = pd.Series(pd.to_datetime(periods)).sort_values().diff().median()
    return "W-FRI" if step <= pd.Timedelta(days=10) else "ME"


def build_dataset(flows: pd.DataFrame, macro: pd.DataFrame, stocks: pd.DataFrame,
                  indices: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    freq = infer_freq(flows["period"])
    f = flows[["period", "net_flow_kes_m"]].copy()
    f["period"] = pd.to_datetime(f["period"])
    f = f.set_index("period").sort_index()

    df = pd.DataFrame(index=f.index)
    df["flow"] = f["net_flow_kes_m"]
    df["flow_3"] = df["flow"].rolling(3).sum()

    # macro (monthly) aligned to the flow periods: last value known at period end
    m = macro.copy().sort_values("period")
    for c in ["usdkes", "brent", "dxy"]:
        m[f"{c}_m"] = m[c]
    m = m.set_index("period")
    mac = pd.merge_asof(df.reset_index()[["period"]], m.reset_index(), on="period", direction="backward").set_index("period")
    k = 3 if freq == "ME" else 13  # "3 periods" ~ a quarter
    df["usdkes_chg_1"] = np.log(mac["usdkes"]).diff()
    df["usdkes_chg_3"] = np.log(mac["usdkes"]).diff(k if freq == "ME" else 13)
    df["cbr"] = mac["cbr"]
    df["cbr_chg_3"] = mac["cbr"].diff(k)
    df["tbill_91d_chg_3"] = mac["tbill_91d"].diff(k)
    df["inflation_12m"] = mac["inflation_12m"]
    df["brent_chg_1"] = np.log(mac["brent"]).diff()
    df["us10y_chg_3"] = mac["us10y"].diff(k)
    df["dxy_chg_1"] = np.log(mac["dxy"]).diff()
    df["vix"] = mac["vix"]

    # market features from daily NSE data, aggregated to the flow frequency
    nasi = indices[indices["code"] == "^NASI"].set_index("date")["close"].resample(freq).last()
    val = stocks.set_index("date")["value_kes_adj"].resample(freq).sum()
    tops = stocks.groupby([pd.Grouper(key="date", freq=freq), "code"])["value_kes_adj"].sum()
    top5 = tops.groupby(level=0).apply(lambda s: s.nlargest(5).sum() / s.sum() if s.sum() > 0 else np.nan)
    mk = pd.DataFrame({"nasi": nasi, "value": val.replace(0, np.nan), "top5_share": top5})
    mk["nasi_ret_1"] = np.log(mk["nasi"]).diff()
    mk["nasi_ret_3"] = np.log(mk["nasi"]).diff(k)
    mk["value_chg_3"] = np.log(mk["value"].rolling(k).mean()).diff(k)
    df = df.join(mk[["nasi_ret_1", "nasi_ret_3", "value_chg_3", "top5_share"]], how="left")

    df["flow_next"] = df["flow"].shift(-1)
    return df, freq


def _models():
    return {
        "logistic": make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=2000)),
        "xgboost": XGBClassifier(n_estimators=150, max_depth=2, learning_rate=0.05, subsample=0.8,
                                 colsample_bytree=0.8, min_child_weight=3, reg_lambda=2.0,
                                 random_state=RANDOM_STATE, eval_metric="logloss", verbosity=0),
    }


def walk_forward(df: pd.DataFrame, features: list[str], min_train: int = MIN_TRAIN_PERIODS) -> pd.DataFrame:
    """One-step-ahead predictions. Row t uses only flows up to t to set the threshold and train."""
    data = df.dropna(subset=features + ["flow"]).copy()
    rows = []
    idx = data.index
    for i in range(min_train, len(idx)):
        t = idx[i]
        if pd.isna(data.loc[t, "flow_next"]):
            break
        train = data.iloc[:i]                                  # rows s < t: their flow_next <= flow_t is known
        thr = train["flow"].quantile(SELLOFF_QUANTILE)
        y_tr = (train["flow_next"] <= thr).astype(int)
        y_true = int(data.loc[t, "flow_next"] <= thr)
        rec = {"period": t, "target_period": t + (idx[1] - idx[0]) if False else None,
               "threshold": thr, "actual": y_true, "flow_next": data.loc[t, "flow_next"],
               "climatology": y_tr.mean()}
        if y_tr.nunique() == 2:
            for name, mdl in _models().items():
                mdl.fit(train[features], y_tr)
                rec[name] = float(mdl.predict_proba(data.loc[[t], features])[0, 1])
        rows.append(rec)
    out = pd.DataFrame(rows).drop(columns="target_period")
    return out


def evaluate(wf: pd.DataFrame) -> pd.DataFrame:
    res = []
    clim = brier_score_loss(wf["actual"], wf["climatology"])
    for m in ["climatology", "logistic", "xgboost"]:
        if m not in wf:
            continue
        p = wf[m]
        b = brier_score_loss(wf["actual"], p)
        auc = roc_auc_score(wf["actual"], p) if wf["actual"].nunique() == 2 else np.nan
        hi = p >= HIGH_RISK_PROB
        res.append({"model": m, "brier": b, "brier_skill_vs_base": 1 - b / clim, "auc": auc,
                    "n_high_risk_calls": int(hi.sum()),
                    "hit_rate_high_risk": float(wf.loc[hi, "actual"].mean()) if hi.any() else np.nan,
                    "base_rate": float(wf["actual"].mean()), "n_periods": len(wf)})
    return pd.DataFrame(res)


def signal(p: float) -> str:
    """HIGH RISK or NO CALL. Low readings are not an all-clear (they hit about the normal rate)."""
    return "HIGH RISK" if p >= HIGH_RISK_PROB else "NO CALL"


def live_prediction(df: pd.DataFrame, features: list[str], model_name: str) -> dict:
    """Train on all labelled history and score the latest period. Features missing in the
    latest period (e.g. stock data not yet updated) are dropped from the live model."""
    latest_t = df["flow"].last_valid_index()
    latest = df.loc[[latest_t]]
    live_feats = [c for c in features if pd.notna(latest[c].iloc[0])]
    dropped = [c for c in features if c not in live_feats]
    train = df.dropna(subset=live_feats + ["flow", "flow_next"])
    thr = train["flow"].quantile(SELLOFF_QUANTILE)
    y = (train["flow_next"] <= thr).astype(int)
    mdl = _models()[model_name]
    mdl.fit(train[live_feats], y)
    p = float(mdl.predict_proba(latest[live_feats])[0, 1])
    drivers = explain(mdl, model_name, train[live_feats], latest[live_feats])
    return {"period": latest_t, "probability": p, "signal": signal(p), "threshold_kes_m": float(thr),
            "base_rate": float(y.mean()), "model": model_name, "features_used": live_feats,
            "features_dropped": dropped, "drivers": drivers, "n_train": len(train)}


def explain(mdl, model_name: str, X_train: pd.DataFrame, x: pd.DataFrame) -> pd.DataFrame:
    """Per-feature contribution to the latest prediction (log-odds units)."""
    if model_name == "xgboost":
        import xgboost as xgb
        contrib = mdl.get_booster().predict(xgb.DMatrix(x), pred_contribs=True)[0][:-1]
    else:
        scaler, lr = mdl.named_steps["standardscaler"], mdl.named_steps["logisticregression"]
        contrib = (scaler.transform(x)[0]) * lr.coef_[0]
    out = pd.DataFrame({"feature": x.columns, "value": x.iloc[0].values, "contribution": contrib})
    out["label"] = out["feature"].map(FEATURE_LABELS).fillna(out["feature"])
    out["direction"] = np.where(out["contribution"] > 0, "raises risk", "lowers risk")
    return out.reindex(out["contribution"].abs().sort_values(ascending=False).index).reset_index(drop=True)


def run(flows, macro, stocks, indices, features: list[str] | None = None) -> dict:
    df, freq = build_dataset(flows, macro, stocks, indices)
    features = [c for c in (features or SELLOFF_FEATURES) if c in df]
    wf = walk_forward(df, features)
    ev = evaluate(wf)
    best = ev[ev["model"] != "climatology"].sort_values("brier").iloc[0]["model"]
    live = live_prediction(df, features, best)
    return {"dataset": df, "freq": freq, "walk_forward": wf, "evaluation": ev, "best_model": best, "live": live}
