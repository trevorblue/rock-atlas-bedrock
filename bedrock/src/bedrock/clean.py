"""Turn raw downloads into tidy tables in data/processed/.

Every loader returns a pandas DataFrame with a fixed schema, so swapping a
source (e.g. Rock Data Plus instead of the public files) only touches this file.
Rock overrides: if these files exist in data/rock/ they replace the public ones
  data/rock/prices.csv         date,code,name,close,prev,day_low,day_high,volume
  data/rock/foreign_flows.csv  period,net_flow_kes_m[,buys_kes_m,sells_kes_m]   (weekly or monthly)
Without a Rock price file, the Mendeley history is extended with OCR'd NSE daily price lists
(data/raw/nse/ocr/prices_ocr.csv, built by `python -m bedrock.nse_ocr`), and the NASI index is
extended over those days by rebuilding it from stock prices (see extend_nasi).
"""
from __future__ import annotations

import difflib
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .config import BLOCK_MULT, PROCESSED, RAW, ROCK

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _num(s: pd.Series) -> pd.Series:
    """'1,234.5' -> 1234.5 ; '-' / '' -> NaN ; '(12)' -> -12"""
    s = s.astype(str).str.strip().str.replace(",", "", regex=False)
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True).str.rstrip("%")
    return pd.to_numeric(s.replace({"-": np.nan, "": np.nan, "nan": np.nan}), errors="coerce")


def _month(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str[:3].str.lower().map(MONTHS)


# =============================================================== equities
PRICE_COLS = {
    "date": "date", "code": "code", "name": "name", "12m low": "low_12m", "12m high": "high_12m",
    "day low": "day_low", "day high": "day_high", "day price": "close", "previous": "prev",
    "change": "change", "change%": "change_pct", "volume": "volume",
    "adjust": "adjusted", "adjusted price": "adjusted",
}


def load_prices_raw() -> pd.DataFrame:
    rock = ROCK / "prices.csv"
    if rock.exists():
        df = pd.read_csv(rock, parse_dates=["date"])
        print(f"prices: using Rock file {rock}")
    else:
        files = sorted((RAW / "nse" / "mendeley").glob("NSE_data_all_stocks_*.csv"))
        if not files:
            raise FileNotFoundError("No NSE price files. Run: python -m bedrock.download")
        parts = []
        for f in files:
            d = pd.read_csv(f, encoding="utf-8-sig", dtype=str)
            d.columns = [PRICE_COLS.get(c.strip().lower(), c.strip().lower()) for c in d.columns]
            parts.append(d)
        df = pd.concat(parts, ignore_index=True)
        dt = pd.to_datetime(df["date"], format="%d-%b-%y", errors="coerce")
        miss = dt.isna()
        if miss.any():
            dt[miss] = pd.to_datetime(df.loc[miss, "date"], dayfirst=True, errors="coerce")
        df["date"] = dt
        for c in ["low_12m", "high_12m", "day_low", "day_high", "close", "prev", "volume"]:
            df[c] = _num(df[c])
        df = _append_ocr(df)
    df["code"] = df["code"].str.strip()
    df = df.dropna(subset=["date", "code", "close"]).drop_duplicates(["date", "code"], keep="last")
    return df.sort_values(["code", "date"]).reset_index(drop=True)


OCR_DROP = ("close outside low-high", "move >30% vs prev")   # QC failures that make a row unusable


def _append_ocr(df: pd.DataFrame) -> pd.DataFrame:
    """Add OCR'd NSE daily price-list rows for dates after the last Mendeley date."""
    f = RAW / "nse" / "ocr" / "prices_ocr.csv"
    if not f.exists():
        return df
    ocr = pd.read_csv(f, parse_dates=["date"], keep_default_na=False, na_values=[""])
    ocr = ocr[ocr["date"] > df["date"].max()]
    bad = ocr["qc_fail"].fillna("").str.contains("|".join(map(re.escape, OCR_DROP)))
    ocr = ocr[~bad]
    print(f"prices: + {len(ocr):,} OCR rows ({ocr['date'].min():%d %b} -> {ocr['date'].max():%d %b %Y}), "
          f"{int(bad.sum())} dropped by quality checks")
    return pd.concat([df, ocr[["date", "code", "name", "close", "prev", "day_low", "day_high", "volume"]]],
                     ignore_index=True)


def extend_nasi(stocks: pd.DataFrame, indices: pd.DataFrame, shareholding: pd.DataFrame) -> pd.DataFrame:
    """Extend ^NASI past its last date with a rebuilt all-share index: daily stock returns weighted by
    market cap (previous price x shares in issue). On 2024-26 data this tracks the real NASI with a daily
    correlation of 0.97. Rows added this way are named 'NASI (rebuilt)'."""
    nasi = indices[indices["code"] == "^NASI"]
    if nasi.empty or not len(shareholding):
        return indices
    last = nasi["date"].max()
    shares = shareholding.dropna(subset=["code"]).drop_duplicates("code").set_index("code")["shares_issued"]
    d = stocks[stocks["date"] > last].copy()
    if d.empty:
        return indices
    d["w"] = d["prev"] * d["code"].map(shares)
    d = d.dropna(subset=["w", "ret"])
    ret = (d["w"] * d["ret"]).groupby(d["date"]).sum() / d.groupby("date")["w"].sum()
    close = nasi.loc[nasi["date"] == last, "close"].iloc[0] * (1 + ret).cumprod()
    ext = pd.DataFrame({"date": ret.index, "code": "^NASI", "name": "NASI (rebuilt)",
                        "close": close.values, "prev": close.shift(1).fillna(close.iloc[0] / (1 + ret.iloc[0])).values,
                        "ret": ret.values})
    return pd.concat([indices, ext], ignore_index=True)


def split_prices(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (stocks, indices). Index rows have codes starting with '^'."""
    is_idx = df["code"].str.startswith("^")
    idx = df.loc[is_idx, ["date", "code", "name", "close", "prev"]].copy()
    idx["ret"] = idx["close"] / idx["prev"] - 1

    st = df.loc[~is_idx].copy()
    st["volume"] = st["volume"].fillna(0.0)
    st["traded"] = st["volume"] > 0
    st["ret"] = np.where(st["prev"] > 0, st["close"] / st["prev"] - 1, np.nan)
    st.loc[st["ret"].abs() > 0.5, "ret"] = np.nan          # corporate actions / data errors
    st["value_kes"] = st["volume"] * st["close"]           # no VWAP in the public data
    st = st.sort_values(["code", "date"])
    # Block deals (takeovers, listing allotments, stake sales) are not liquidity an ordinary seller can use.
    # For liquidity measures a day counts for at most BLOCK_MULT x the stock's median traded day (last 120 rows).
    med = (st["value_kes"].where(st["traded"]).groupby(st["code"])
           .transform(lambda s: s.rolling(120, min_periods=10).median()))
    cap = BLOCK_MULT * med
    st["block"] = cap.notna() & (st["value_kes"] > cap)
    st["value_kes_adj"] = np.where(st["block"], cap, st["value_kes"])
    keep = ["date", "code", "name", "close", "prev", "day_low", "day_high", "volume", "value_kes", "value_kes_adj",
            "block", "ret", "traded"]
    return st[keep].reset_index(drop=True), idx.reset_index(drop=True)


def load_sectors() -> pd.DataFrame:
    files = sorted((RAW / "nse" / "mendeley").glob("NSE_data_stock_market_sectors_*.csv"))
    parts = []
    for f in files:  # later files win
        d = pd.read_csv(f, encoding="utf-8-sig", dtype=str)
        d.columns = ["sector", "code", "name"][: len(d.columns)]
        parts.append(d)
    if not parts:
        return pd.DataFrame(columns=["code", "sector", "sector_name"])
    s = pd.concat(parts).dropna(subset=["code"])
    s["code"] = s["code"].str.strip()
    s = s.drop_duplicates("code", keep="last")
    return s.rename(columns={"name": "sector_name"})[["code", "sector", "sector_name"]]


# =============================================================== CMA bulletin tables
def _cma_pdfs() -> list[Path]:
    files = sorted((RAW / "cma").glob("cma_qsb_*.pdf"))

    def key(p: Path):
        m = re.search(r"q(\d)_(\d{4})", p.name)
        return (int(m.group(2)), int(m.group(1))) if m else (0, 0)
    return sorted(files, key=key, reverse=True)  # newest first


def _pdf_pages(path: Path) -> list[str]:
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return [(p.extract_text() or "") for p in pdf.pages]


def parse_cma_net_flows(pages: list[str]) -> pd.DataFrame:
    """Table 'Foreign Investor Net Cash Flow Activity' -> monthly net flows (KES m)."""
    for t in pages:
        if "Net Cash Flow Activity" not in t:
            continue
        lines = t.splitlines()
        years = None
        rows = []
        for ln in lines:
            if ln.strip().startswith("Month/Year"):
                years = [int(y) for y in re.findall(r"\b(20\d{2})\b", ln)]
                continue
            m = re.match(r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(.*)$", ln.strip())
            if years and m:
                vals = re.findall(r"\(?-?[\d,]+\)?|-", m.group(2))
                for y, v in zip(years, vals):
                    rows.append((y, MONTHS[m.group(1)[:3].lower()], v))
        if rows:
            d = pd.DataFrame(rows, columns=["year", "month", "v"])
            d["net_flow_kes_m"] = _num(d["v"])
            d["period"] = pd.to_datetime(dict(year=d.year, month=d.month, day=1)) + pd.offsets.MonthEnd(0)
            return d.dropna(subset=["net_flow_kes_m"])[["period", "net_flow_kes_m"]]
    return pd.DataFrame(columns=["period", "net_flow_kes_m"])


def parse_cma_participation(pages: list[str]) -> pd.DataFrame:
    """Table 'Trends in Foreign Equity Investor Participation' -> monthly buys/sells/turnover."""
    out = []
    for t in pages:
        if "Foreign Equity Investor Participation" not in t or "Purchases" not in t:
            continue
        q_year = None
        for ln in t.splitlines():
            yq = re.search(r"Q\d\.(\d{4})", ln)
            if yq:
                q_year = int(yq.group(1))
            m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)%", ln)
            if m and q_year:
                out.append((q_year, MONTHS[m.group(1)[:3].lower()], *m.groups()[1:]))
    if not out:
        return pd.DataFrame(columns=["period", "buys_kes_m", "sells_kes_m", "turnover_kes_m", "foreign_share"])
    d = pd.DataFrame(out, columns=["year", "month", "buys_kes_m", "sells_kes_m", "turnover_kes_m", "foreign_share"])
    for c in ["buys_kes_m", "sells_kes_m", "turnover_kes_m", "foreign_share"]:
        d[c] = _num(d[c])
    d["foreign_share"] /= 100
    d["period"] = pd.to_datetime(dict(year=d.year, month=d.month, day=1)) + pd.offsets.MonthEnd(0)
    return d.drop(columns=["year", "month"]).drop_duplicates("period")


_MONTHWORD = r"(?:[A-Z][a-z]{2}-\d{2,4}|January|February|March|April|May|June|July|August|September|October|November|December)"
SH_RE = re.compile(
    rf"^(?P<name>.+?)\s+(?P<asof>{_MONTHWORD})\s+(?P<total>[\d,]+)\s+(?P<foreign>[\d,]+)\s+(?P<fpct>[\d.]+)%"
    r"(?:\s+(?P<li>[\d,]+)\s+(?P<lipct>[\d.]+)%)?(?:\s+(?P<lc>[\d,]+)\s+(?P<lcpct>[\d.]+)%)?"
)


def parse_cma_shareholding(pages: list[str]) -> pd.DataFrame:
    """Table 'Shareholding per listed company' -> shares in issue and foreign %.

    Long company names wrap onto two lines in the PDF, so an unmatched line is
    joined with the next one before matching.
    """
    lines, on = [], False
    for t in pages:
        if "Shareholding per listed company" in t and "..." not in t:
            on = True
        if not on:
            continue
        lines += [ln.strip() for ln in t.splitlines() if ln.strip()]
        if "Investor Participation" in t:
            break
    rows, i = [], 0
    while i < len(lines):
        m = SH_RE.match(lines[i])
        if not m and i + 1 < len(lines) and not SH_RE.match(lines[i + 1]) and not lines[i].isupper():
            m = SH_RE.match(lines[i] + " " + lines[i + 1])
            if m:
                i += 1
        if m:
            rows.append(m.groupdict())
        i += 1
    if not rows:
        return pd.DataFrame()
    d = pd.DataFrame(rows)
    for c in ["total", "foreign", "li", "lc"]:
        d[c] = _num(d[c])
    for c in ["fpct", "lipct", "lcpct"]:
        d[c] = _num(d[c]) / 100
    d = d.rename(columns={"total": "shares_issued", "foreign": "shares_foreign", "fpct": "foreign_pct",
                          "li": "shares_local_ind", "lipct": "local_ind_pct", "lc": "shares_local_inst",
                          "lcpct": "local_inst_pct", "name": "cma_name"})
    return d.drop_duplicates("cma_name")


def _norm(name: str) -> str:
    n = name.lower()
    n = re.sub(r"\bord\.?\s*[\d.]+.*$", "", n)                      # drop "Ord 0.50 ..." tail
    n = re.sub(r"\b(plc|ltd|limited|holdings?|group|company|co|the|sme|kenya|k|of)\b", " ", n)
    return re.sub(r"[^a-z0-9]+", " ", n).strip()


# Names the fuzzy matcher cannot resolve (checked by hand). Lowercase substring -> ticker.
NAME_ALIASES = {
    "kengen": "KEGN", "trific": "TRFC", "alp industrial": "ALP", "family bank": "FMLY", "totalenergies": "TOTL",
    "4% pref": "KPLC-P4", "7% pref": "KPLC-P7", "kenya power & lighting co": "KPLC",
}


def match_codes(cma: pd.DataFrame, sectors: pd.DataFrame) -> pd.DataFrame:
    """Attach NSE ticker codes to CMA company names: hand aliases first, then fuzzy matching."""
    ref = {_norm(n): c for c, n in zip(sectors["code"], sectors["sector_name"]) if isinstance(n, str)}
    keys = list(ref)
    codes, scores = [], []
    for n in cma["cma_name"]:
        alias = next((c for k, c in NAME_ALIASES.items() if k in n.lower()), None)
        if alias:
            codes.append(alias)
            scores.append(1.0)
            continue
        hit = difflib.get_close_matches(_norm(n), keys, n=1, cutoff=0.6)
        codes.append(ref[hit[0]] if hit else None)
        scores.append(difflib.SequenceMatcher(None, _norm(n), hit[0]).ratio() if hit else 0.0)
    out = cma.copy()
    out["code"], out["match_score"] = codes, scores
    return out


def load_cma(sectors: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(monthly net foreign flows, monthly participation, shareholding) from the newest bulletins."""
    flows, part, share = [], [], None
    for pdf in _cma_pdfs():
        try:
            pages = _pdf_pages(pdf)
        except Exception as e:  # corrupt / partial download
            print(f"  skip {pdf.name}: {e}")
            continue
        flows.append(parse_cma_net_flows(pages))
        part.append(parse_cma_participation(pages))
        if share is None:
            s = parse_cma_shareholding(pages)
            if len(s):
                share = match_codes(s, sectors)
                share["source"] = pdf.name
    flows = [x for x in flows if len(x)]
    part = [x for x in part if len(x)]
    f = pd.concat(flows).drop_duplicates("period", keep="first").sort_values("period") if flows else pd.DataFrame()
    p = pd.concat(part).drop_duplicates("period", keep="first").sort_values("period") if part else pd.DataFrame()
    return f.reset_index(drop=True), p.reset_index(drop=True), (share if share is not None else pd.DataFrame())


def load_foreign_flows(cma_flows: pd.DataFrame) -> pd.DataFrame:
    rock = ROCK / "foreign_flows.csv"
    if rock.exists():
        print(f"foreign flows: using Rock file {rock}")
        d = pd.read_csv(rock, parse_dates=["period"])
        return d.sort_values("period").reset_index(drop=True)
    return cma_flows


# =============================================================== macro
def _cbk_rates() -> pd.DataFrame:
    d = pd.read_csv(RAW / "cbk" / "central_bank_rate.csv", skiprows=1, dtype=str)
    d.columns = [c.strip() for c in d.columns]
    d["YEAR"] = pd.to_numeric(d["YEAR"], errors="coerce").ffill()
    d["m"] = _month(d["MONTH"])
    d = d.dropna(subset=["YEAR", "m"])
    out = pd.DataFrame({"period": pd.to_datetime(dict(year=d.YEAR.astype(int), month=d.m.astype(int), day=1))
                        + pd.offsets.MonthEnd(0)})
    for src, dst in [("Central Bank Rate", "cbr"), ("91-Day Tbill", "tbill_91d"), ("182-days Tbill", "tbill_182d"),
                     ("364-days Tbill", "tbill_364d"), ("Interbank Rate", "interbank")]:
        out[dst] = _num(d[src]).values
    return out


def _cbk_fx() -> pd.DataFrame:
    d = pd.read_csv(RAW / "cbk" / "fx_monthly_avg.csv", skiprows=1)
    d = d.dropna(subset=["Year", "Month"])
    d = d[pd.to_numeric(d["Year"], errors="coerce").notna()]
    return pd.DataFrame({
        "period": pd.to_datetime(dict(year=d.Year.astype(int), month=d.Month.astype(int), day=1)) + pd.offsets.MonthEnd(0),
        "usdkes": _num(d["United States dollar"]).values,
    })


def _cbk_inflation() -> pd.DataFrame:
    p = RAW / "cbk" / "inflation.csv"
    if not p.exists():
        return pd.DataFrame(columns=["period", "inflation_12m"])
    d = pd.read_csv(p)
    d["m"] = _month(d["month"])
    d["period"] = pd.to_datetime(dict(year=d.year, month=d.m, day=1)) + pd.offsets.MonthEnd(0)
    return d[["period", "inflation_12m"]].drop_duplicates("period")


def _fred_monthly() -> pd.DataFrame:
    names = {"DCOILBRENTEU": "brent", "DGS10": "us10y", "DFF": "fedfunds", "DTWEXBGS": "dxy", "VIXCLS": "vix"}
    out = None
    for sid, col in names.items():
        p = RAW / "fred" / f"{sid}.csv"
        if not p.exists():
            continue
        d = pd.read_csv(p)
        d.columns = ["date", col]
        d["date"] = pd.to_datetime(d["date"])
        d[col] = pd.to_numeric(d[col], errors="coerce")
        m = d.set_index("date")[col].resample("ME").mean().rename_axis("period").reset_index()
        out = m if out is None else out.merge(m, on="period", how="outer")
    return out if out is not None else pd.DataFrame(columns=["period"])


def load_macro_monthly() -> pd.DataFrame:
    m = _cbk_rates().merge(_cbk_fx(), on="period", how="outer")
    m = m.merge(_cbk_inflation(), on="period", how="outer").merge(_fred_monthly(), on="period", how="outer")
    return m[m["period"] >= "2005-01-01"].sort_values("period").reset_index(drop=True)


# =============================================================== run
def build_all() -> dict[str, pd.DataFrame]:
    print("Cleaning raw data ...")
    raw = load_prices_raw()
    stocks, indices = split_prices(raw)
    sectors = load_sectors()
    cma_flows, participation, shareholding = load_cma(sectors)
    indices = extend_nasi(stocks, indices, shareholding)
    flows = load_foreign_flows(cma_flows)
    macro = load_macro_monthly()
    out = dict(stocks=stocks, indices=indices, sectors=sectors, foreign_flows=flows,
               participation=participation, shareholding=shareholding, macro=macro)
    for k, v in out.items():
        v.to_parquet(PROCESSED / f"{k}.parquet", index=False)
        span = ""
        for c in ("date", "period"):
            if c in v and len(v):
                span = f"  {v[c].min():%Y-%m} -> {v[c].max():%Y-%m}"
        print(f"  {k:<14} {len(v):>9,} rows{span}")
    if len(shareholding):
        un = shareholding["code"].isna().sum()
        print(f"  shareholding: {len(shareholding) - un} companies matched to tickers, {un} unmatched")
    return out


if __name__ == "__main__":
    build_all()
