"""Robustness checks: do the headline findings survive different assumptions and chance?

1. Depth sensitivity   headline "% of shares needing > 20 days to exit" across position size,
                       participation rate and lookback window; and across the block-deal cap.
2. Sell-off model      binomial test: are HIGH RISK calls followed by heavy selling more often
                       than the base rate? Calibration table: predicted vs actual frequency.
                       Same test with the HIGH RISK line moved (35-50%), and the recent record.
3. Speculation         cluster bootstrap (resampling whole stocks, so one noisy stock cannot
                       drive the result) of the 20-day return gap after watch-listed small-cap
                       up-spikes vs other small-cap up-moves.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from . import depth
from .config import HIGH_RISK_PROB, RANDOM_STATE


# ------------------------------------------------------------------ 1. depth
def depth_sensitivity(stocks, shareholding, sectors,
                      positions=(1e6, 10e6, 50e6), participations=(0.10, 0.20, 0.30),
                      lookbacks=(60, 120, 250), threshold_days=20) -> pd.DataFrame:
    rows = []
    for lb in lookbacks:
        snap = depth.depth_snapshot(stocks, shareholding, sectors, lookback=lb)
        eq = snap[snap["instrument"] == "Equity"]
        for pos in positions:
            for part in participations:
                days = pos / (part * eq["adv_kes"].replace(0, np.nan))
                days = days.fillna(np.inf)
                rows.append({"lookback_days": lb, "position_kes": pos, "participation": part,
                             f"pct_over_{threshold_days}d": float((days > threshold_days).mean()),
                             "pct_over_5d": float((days > 5).mean()), "n_stocks": len(eq)})
    return pd.DataFrame(rows)


def block_cap_sensitivity(stocks, shareholding, sectors, mults=(5, 10, 20, 50, None)) -> pd.DataFrame:
    """Headline depth numbers when block deals are capped at mult x the median traded day (None = no cap)."""
    s = stocks.sort_values(["code", "date"])
    med = (s["value_kes"].where(s["traded"]).groupby(s["code"])
           .transform(lambda v: v.rolling(120, min_periods=10).median()))
    rows = []
    for m in mults:
        s2 = s.copy()
        if m is None:
            s2["value_kes_adj"] = s2["value_kes"]
        else:
            cap = m * med
            s2["value_kes_adj"] = np.where(cap.notna() & (s2["value_kes"] > cap), cap, s2["value_kes"])
        h = depth.headline(depth.depth_snapshot(s2, shareholding, sectors))
        rows.append({"block_cap": "no cap" if m is None else f"{m}x median day", "pct_over_20d": h["pct_over_20d"],
                     "pct_over_5d": h["pct_over_5d"], "top5_share_of_value": h["top5_share_of_value"],
                     "n_stocks": h["n_stocks"]})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 2. sell-off model
def selloff_significance(wf: pd.DataFrame, model: str) -> dict:
    calls = wf[wf[model] >= HIGH_RISK_PROB]
    k, n = int(calls["actual"].sum()), len(calls)
    base = float(wf["actual"].mean())
    p = binomtest(k, n, base, alternative="greater").pvalue if n else np.nan
    return {"model": model, "high_risk_calls": n, "hits": k, "hit_rate": k / n if n else np.nan,
            "base_rate": base, "p_value_vs_base": float(p)}


def selloff_thresholds(wf: pd.DataFrame, model: str, lines=(0.35, 0.40, 0.45, 0.50),
                       recent: int = 15) -> pd.DataFrame:
    """Hit rate if the HIGH RISK line were drawn elsewhere, plus the record over the last `recent` months."""
    a, base = wf["actual"].astype(bool), float(wf["actual"].mean())
    rows = []
    for name, sub_, ln in [(f"all {len(wf)} months", wf, l) for l in lines] + [(f"last {recent} months", wf.tail(recent),
                                                                                HIGH_RISK_PROB)]:
        m = sub_[model] >= ln
        k, n = int(a.loc[sub_.index][m].sum()), int(m.sum())
        rows.append({"months": name, "high_risk_line": ln, "calls": n, "hits": k, "hit_rate": k / n if n else np.nan,
                     "heavy_months": int(a.loc[sub_.index].sum()),
                     "p_value_vs_base": float(binomtest(k, n, base, alternative="greater").pvalue) if n else np.nan})
    return pd.DataFrame(rows)


def calibration(wf: pd.DataFrame, model: str, bins=(0, 0.15, 0.3, 0.45, 1.0)) -> pd.DataFrame:
    b = pd.cut(wf[model], bins=list(bins), include_lowest=True)
    out = wf.groupby(b, observed=True).agg(n=("actual", "size"), predicted=(model, "mean"), actual=("actual", "mean"))
    return out.reset_index().rename(columns={model: "bin"}).assign(bin=lambda d: d.iloc[:, 0].astype(str))


FEATURE_SETS = {
    "flows only (live model)": ["flow", "flow_3"],
    "flows + macro": ["flow", "flow_3", "usdkes_chg_1", "usdkes_chg_3", "cbr", "cbr_chg_3", "tbill_91d_chg_3",
                      "inflation_12m", "brent_chg_1", "us10y_chg_3", "dxy_chg_1", "vix"],
}


def selloff_feature_sets(dataset: pd.DataFrame) -> pd.DataFrame:
    """Out-of-sample comparison of input sets x models, plus a no-model rule ("HIGH RISK whenever this month
    was itself heavy selling"). Every row is reported, not just the best, so readers can judge selection."""
    from . import selloff
    sets = dict(FEATURE_SETS)
    sets["flows + macro + market"] = sets["flows + macro"] + ["nasi_ret_1", "nasi_ret_3", "value_chg_3", "top5_share"]
    rows = []
    for name, feats in sets.items():
        feats = [f for f in feats if f in dataset]
        wf = selloff.walk_forward(dataset, feats)
        ev = selloff.evaluate(wf).set_index("model")
        for m in ("logistic", "xgboost"):
            sig = selloff_significance(wf, m)
            rows.append({"inputs": name, "model": m, "months_tested": len(wf), "auc": ev.loc[m, "auc"],
                         "brier_skill_vs_base": ev.loc[m, "brier_skill_vs_base"], **{k: sig[k] for k in
                         ("high_risk_calls", "hits", "hit_rate", "base_rate", "p_value_vs_base")}})
        if name.startswith("flows only"):
            d = dataset.loc[dataset.index.isin(wf["period"])]
            rule = (d["flow"].values <= wf["threshold"].values)
            k, n, base = int(wf.loc[rule, "actual"].sum()), int(rule.sum()), float(wf["actual"].mean())
            rows.append({"inputs": "no model: this month was heavy selling", "model": "rule", "months_tested": len(wf),
                         "auc": np.nan, "brier_skill_vs_base": np.nan, "high_risk_calls": n, "hits": k,
                         "hit_rate": k / n if n else np.nan, "base_rate": base,
                         "p_value_vs_base": binomtest(k, n, base, alternative="greater").pvalue if n else np.nan})
    out = pd.DataFrame(rows)
    n_tries = int((out["model"] != "rule").sum())
    out["p_adjusted_bonferroni"] = (out["p_value_vs_base"] * n_tries).clip(upper=1.0)
    return out


# ------------------------------------------------------------------ 3. speculation
def speculation_bootstrap(scored: pd.DataFrame, size_by_code: pd.Series, n_boot: int = 2000,
                          horizon: str = "fwd_20d") -> pd.DataFrame:
    """Gap in average forward return after big up-moves (> 5%): watch-listed minus the rest,
    separately for small and large stocks, with a 95% cluster-bootstrap interval (resampling stocks)."""
    med = size_by_code.median()
    groups = {"small": set(size_by_code[size_by_code < med].index),
              "large": set(size_by_code[size_by_code >= med].index)}
    rows = []
    for name, codes_in in groups.items():
        d = scored[(scored["ret"] > 0.05) & scored[horizon].notna() & scored["code"].isin(codes_in)]
        # per-stock sums and counts, so a bootstrap draw is just a weighted sum (fast)
        agg = d.groupby(["code", "watch"])[horizon].agg(["sum", "count"]).unstack("watch", fill_value=0)
        ws, wn = agg[("sum", True)].values, agg[("count", True)].values
        os_, on = agg[("sum", False)].values, agg[("count", False)].values
        rng = np.random.default_rng(RANDOM_STATE)
        draws = rng.integers(0, len(agg), size=(n_boot, len(agg)))
        counts = np.apply_along_axis(np.bincount, 1, draws, minlength=len(agg))   # times each stock is drawn
        with np.errstate(invalid="ignore", divide="ignore"):
            sims = counts @ ws / (counts @ wn) - counts @ os_ / (counts @ on)
        sims = sims[np.isfinite(sims)]
        w, o = d.loc[d["watch"], horizon], d.loc[~d["watch"], horizon]
        lo, hi = np.percentile(sims, [2.5, 97.5])
        rows.append({"size": name, "horizon": horizon, "n_watch": len(w), "n_other": len(o), "n_stocks": len(agg),
                     "watch_mean": w.mean(), "other_mean": o.mean(), "gap": w.mean() - o.mean(),
                     "ci_low": lo, "ci_high": hi, "ci_excludes_zero": bool(lo > 0 or hi < 0)})
    return pd.DataFrame(rows)


def run_all(stocks, shareholding, sectors, wf, best_model, scored, dataset=None) -> dict:
    size = stocks.groupby("code")["value_kes_adj"].mean()
    return {
        "depth_sensitivity": depth_sensitivity(stocks, shareholding, sectors),
        "block_cap": block_cap_sensitivity(stocks, shareholding, sectors),
        "selloff_significance": pd.DataFrame([selloff_significance(wf, m) for m in ("logistic", "xgboost")]),
        "selloff_calibration": calibration(wf, best_model),
        "selloff_thresholds": selloff_thresholds(wf, best_model),
        **({"selloff_feature_sets": selloff_feature_sets(dataset)} if dataset is not None else {}),
        "speculation_bootstrap": pd.concat([speculation_bootstrap(scored, size, horizon=h)
                                            for h in ("fwd_5d", "fwd_20d")], ignore_index=True),
    }
