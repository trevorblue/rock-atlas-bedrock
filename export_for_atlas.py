"""Export Bedrock's real NSE data and model results into static files the ROCK ATLAS front end reads.

    python export_for_atlas.py                      # uses ../BEDROCK and bedrock/app/snapshot
    python export_for_atlas.py --bedrock ../BEDROCK --years 3

Writes:
    public/data/nse_prices.csv    real NSE prices in ATLAS's own CSV column format, so his six TypeScript
                                  engines run on real data with no change to his code
    public/data/bedrock/*.json    every Bedrock model result, for the pages that show them

Nothing is computed here: the numbers come from Bedrock's pipeline (`python -m bedrock.pipeline`), which is
copied unchanged into bedrock/. NaN and infinity become null so the JSON is valid for a browser.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PUBLIC = HERE / "public" / "data"
OUT = PUBLIC / "bedrock"


# ------------------------------------------------------------------ helpers
def clean(obj):
    """NaN/Inf -> None, numpy -> python, Timestamp -> 'YYYY-MM-DD'. JSON in a browser accepts nothing else."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (pd.Timestamp,)):
        return str(obj.date())
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 6)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if obj is pd.NaT or obj is None:
        return None
    return obj


def rows(df: pd.DataFrame, cols: list[str] | None = None) -> list[dict]:
    d = df if cols is None else df[[c for c in cols if c in df.columns]]
    out = d.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d")
    return clean(out.to_dict("records"))


def write(name: str, payload) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(clean(payload), separators=(",", ":")), encoding="utf-8")
    print(f"  {p.relative_to(HERE)}  ({p.stat().st_size / 1024:,.0f} KB)")


# ------------------------------------------------------------------ export
def export(bedrock: Path, snapshot: Path, years: int) -> None:
    rd = lambda n: pd.read_parquet(snapshot / f"{n}.parquet")       # noqa: E731
    js = lambda n: json.loads((snapshot / f"{n}.json").read_text())  # noqa: E731
    opt = lambda n: rd(n) if (snapshot / f"{n}.parquet").exists() else pd.DataFrame()  # noqa: E731

    head = js("headline")
    print("Bedrock results ->", OUT.relative_to(HERE))

    # ---- meta: where every number comes from, and the settings behind it
    write("meta", {
        "asOf": head["data_as_of"],
        "usesRockData": head.get("uses_rock_data", False),
        "engine": "Bedrock",
        "sources": [
            "NSE daily prices 2013-2026 (Mendeley Data, Wanjawa, CC BY 4.0)",
            "NSE daily price lists, read by OCR, for July-November 2026 (99% of volumes and 96% of closes match on the overlap)",
            "CMA Quarterly Statistical Bulletins (monthly net foreign flows, per-company ownership)",
            "Central Bank of Kenya and FRED (macro)",
        ],
        "settings": {"positionKes": 10_000_000, "participation": 0.20, "lookbackDays": 120,
                     "blockDealCapMultiple": 10, "tierBounds": [2, 20, 250], "highRiskProb": 0.45,
                     "impactK": 1.0, "strategicCutoff": 0.50, "crashDrop": -0.15, "crashHorizonDays": 21,
                     "exitDays": 20},
    })

    # ---- 1. market depth
    snap = rd("depth_snapshot")
    write("headline", head)
    write("depth_snapshot", rows(snap, ["code", "name", "sector", "instrument", "tier", "days_to_exit", "adv_kes",
                                        "median_value_kes", "zero_trade_share", "amihud", "turnover_annual",
                                        "market_cap_kes", "foreign_pct", "volatility", "price", "as_of"]))
    write("depth_history", rows(rd("depth_history")))
    write("concentration", rows(rd("concentration")))
    write("robustness_depth", {"sensitivity": rows(rd("robustness_depth_sensitivity")),
                               "blockCap": rows(opt("robustness_block_cap"))})

    # ---- 2. sell-off alert
    write("selloff", {
        "live": js("selloff_live"),
        "walkForward": rows(rd("selloff_walk_forward")),
        "evaluation": rows(rd("selloff_evaluation")),
        "significance": rows(rd("robustness_selloff_significance")),
        "featureSets": rows(opt("robustness_selloff_feature_sets")),
        "calibration": rows(rd("robustness_selloff_calibration")),
        "thresholds": rows(opt("robustness_selloff_thresholds")),
        "drivers": rows(rd("selloff_drivers")),
    })
    write("flows", rows(rd("selloff_dataset")[["period", "flow", "flow_3"]].dropna(subset=["flow"])))

    # ---- 3. crash risk + GARCH
    write("crash", {
        "summary": js("crash_summary"),
        "live": rows(rd("crash_live")),
        "deciles": rows(rd("crash_deciles")),
        "compare": rows(rd("crash_compare")),
        "byYear": rows(rd("crash_by_year")),
        "robust": rows(rd("crash_robust")),
        "importance": rows(rd("crash_importance")),
        "garch": js("garch_eval") if (snapshot / "garch_eval.json").exists() else None,
    })

    # ---- 4. speculation watch
    flags = rd("speculation_flags")
    flags = flags[flags["watch"]].copy()
    recent = flags[flags["date"] >= flags["date"].max() - pd.Timedelta(days=365)]
    write("speculation", {
        "recentFlags": rows(recent.sort_values("date", ascending=False),
                            ["date", "code", "name", "close", "ret", "ex_ret", "value_kes", "z_ret", "z_value",
                             "anomaly_score", "direction", "fwd_5d", "fwd_20d", "news"]),
        "totalFlags": int(len(flags)),
        "validation": rows(rd("speculation_validation")),
        "bootstrap": rows(rd("robustness_speculation_bootstrap")),
        "newsChecked": int((flags["news"].fillna("") != "").sum()),
        "noNews": int((flags["news"].fillna("") == "no news found").sum()),
    })

    # ---- 5. opportunity radar + resilience
    write("radar", {
        "summary": js("radar_summary"),
        "live": rows(rd("radar_live")),
        "monthly": rows(rd("radar_monthly")),
        "resilienceMonthly": rows(rd("radar_resilience_monthly")),
    })

    # ---- 6. Bedrock's own demo datasets (synthetic, kept behind the demo label)
    write("demo", {
        "fundamentals": rows(opt("demo_fundamentals")),
        "opportunities": rows(opt("demo_opportunities")),
        "foreignFlows": rows(opt("demo_foreign_flows")),
        "selloffFlows": rows(opt("demo_selloff_flows")),
        "selloffWalkForward": rows(opt("demo_selloff_walk_forward")),
        "selloffLive": js("demo_selloff_live") if (snapshot / "demo_selloff_live.json").exists() else None,
    })

    # ---- 7. real prices in ATLAS's CSV format, so his engines run on real data unchanged
    px_path = bedrock / "data" / "processed" / "stocks.parquet"
    if not px_path.exists():
        print(f"! {px_path} not found: skipping the price CSV (run Bedrock's pipeline first)")
        return
    px = pd.read_parquet(px_path)
    sec = pd.read_parquet(bedrock / "data" / "processed" / "sectors.parquet")
    sec = sec.dropna(subset=["code"]).drop_duplicates("code").set_index("code")["sector"]
    eq = set(snap.loc[snap["instrument"] == "Equity", "code"])
    cutoff = px["date"].max() - pd.DateOffset(years=years)
    d = px[(px["date"] >= cutoff) & px["code"].isin(eq)].copy()
    out = pd.DataFrame({
        "date": d["date"].dt.strftime("%Y-%m-%d"),
        "ticker": d["code"],
        "name": d["name"].str.replace(r"\s+", " ", regex=True).str.replace(",", " ", regex=False).str.strip(),
        "sector": d["code"].map(sec).fillna("Unclassified").str.replace(",", " ", regex=False),
        "high": d["day_high"].round(2),
        "low": d["day_low"].round(2),
        "close": d["close"].round(2),
        "volume": d["volume"].fillna(0).round(0).astype("int64"),
        "turnover": d["value_kes"].fillna(0).round(0).astype("int64"),
    }).dropna(subset=["close"]).sort_values(["date", "ticker"])
    PUBLIC.mkdir(parents=True, exist_ok=True)
    csv_path = PUBLIC / "nse_prices.csv"
    out.to_csv(csv_path, index=False)
    print(f"  {csv_path.relative_to(HERE)}  ({csv_path.stat().st_size / 1e6:,.1f} MB, {len(out):,} rows, "
          f"{out['ticker'].nunique()} stocks, {out['date'].min()} to {out['date'].max()})")

    write("prices_meta", {"rows": int(len(out)), "stocks": int(out["ticker"].nunique()),
                          "start": str(out["date"].min()), "end": str(out["date"].max()),
                          "note": "Real NSE prices. 'open' is not published in the source, so Atlas's parser uses "
                                  "the close for it. Foreign turnover per stock is not available in public data."})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bedrock", default=str(HERE.parent / "BEDROCK"), help="the original Bedrock project folder")
    ap.add_argument("--snapshot", default=str(HERE / "bedrock" / "app" / "snapshot"), help="Bedrock's published results")
    ap.add_argument("--years", type=int, default=3, help="years of daily prices to put in the CSV")
    a = ap.parse_args()
    export(Path(a.bedrock), Path(a.snapshot), a.years)
    print("Done.")
