"""Extend NSE daily prices beyond the Mendeley data using the NSE's own daily price lists.

The NSE publishes one PDF per trading day at
    https://www.nse.co.ke/wp-content/uploads/DD-MMM-YY.pdf      e.g. 13-NOV-26.pdf
The PDFs are scanned images, so they are read with OCR (RapidOCR), then each row is
matched to a ticker by company name and checked for internal consistency
(low <= VWAP <= high, sensible change vs previous price).

    python -m bedrock.nse_ocr --start 2026-06-22 --end 2026-11-13 --workers 4   # download + OCR
Output: data/raw/nse/ocr/prices_ocr.csv  (same columns as clean.load_prices_raw)
"""
from __future__ import annotations

import argparse
import os
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .config import RAW, USER_AGENT

PDF_DIR = RAW / "nse" / "pricelist_pdf"
OCR_DIR = RAW / "nse" / "ocr"
URL = "https://www.nse.co.ke/wp-content/uploads/{}.pdf"


def pdf_name(d: pd.Timestamp) -> str:
    return d.strftime("%d-%b-%y").upper()


def download(start: str, end: str, pause: float = 1.0) -> list[Path]:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    got = []
    for d in pd.bdate_range(start, end):
        dest = PDF_DIR / f"{pdf_name(d)}.pdf"
        if dest.exists() and dest.stat().st_size > 10_000:
            got.append(dest)
            continue
        for attempt in range(3):
            try:
                r = s.get(URL.format(pdf_name(d)), timeout=90)
                if r.status_code == 200 and r.content[:4] == b"%PDF":
                    dest.write_bytes(r.content)
                    got.append(dest)
                    print(f"  got  {dest.name}")
                else:
                    print(f"  none {dest.name} (HTTP {r.status_code})")   # holiday or not posted
                break
            except requests.RequestException as e:
                if attempt == 2:
                    print(f"  FAIL {dest.name}: {e}")
                time.sleep(3)
        time.sleep(pause)
    return got


# ------------------------------------------------------------------ OCR + parsing
_ENGINE = None
_THREADS = None          # onnx threads per process; None = all cores (best for a single process)


def _engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR
        kw = {"use_cls": False}                      # text is never rotated: skip the angle classifier
        if _THREADS:
            kw["intra_op_num_threads"] = _THREADS
        _ENGINE = RapidOCR(**kw)
    return _ENGINE


def _init_worker(threads: int) -> None:
    global _THREADS
    _THREADS = threads


def ocr_pdf(path: Path, dpi: int = 200) -> list[tuple[int, float, float, float, float, str]]:
    """Return OCR boxes as (page, x0, x1, y_center, height, text)."""
    import pypdfium2 as pdfium
    out = []
    pdf = pdfium.PdfDocument(str(path))
    for pi in range(len(pdf)):
        img = np.array(pdf[pi].render(scale=dpi / 72).to_pil())
        res, _ = _engine()(img)
        for box, txt, conf in res or []:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            out.append((pi, min(xs), max(xs), (min(ys) + max(ys)) / 2, max(ys) - min(ys), txt.strip()))
    return out


def _to_num(t: str) -> float:
    t = t.replace(",", "").replace(" ", "")
    try:
        return float(t)
    except ValueError:
        return np.nan


def parse_boxes(boxes, page_width: float) -> pd.DataFrame:
    """Rebuild table rows from OCR boxes.

    Layout (left to right): 52wk high | 52wk low + NAME | ISIN | status | HIGH | LOW | VWAP | PREVIOUS | VOLUME.
    The five right-hand numeric columns are found by clustering the right edges of numeric boxes.
    """
    rows = []
    df = pd.DataFrame(boxes, columns=["page", "x0", "x1", "y", "h", "text"])
    for pg, b in df.groupby("page"):
        isin = b[b["text"].str.match(r"^[A-Z]{2}[A-Z0-9]{9,11}$")]
        if isin.empty:
            continue
        isin_x = isin["x1"].median()
        # numeric boxes right of the ISIN/status columns
        num = b[(b["x0"] > isin_x + 0.04 * page_width) & b["text"].str.replace(",", "").str.match(r"^-?\d*\.?\d+$")]
        edges = np.sort(num["x1"].values)
        if len(edges) < 5:
            continue
        gaps = np.where(np.diff(edges) > 0.02 * page_width)[0]
        groups = np.split(edges, gaps + 1)
        centers = [g.mean() for g in groups if len(g) >= 3]
        if len(centers) != 5:
            # keep the five largest groups, in x order
            big = sorted(groups, key=len, reverse=True)[:5]
            centers = sorted(g.mean() for g in big)
        names = ["high", "low", "vwap", "prev", "volume"]
        # rows anchored on ISIN boxes; row pitch = typical gap between ISINs
        ys = np.sort(isin["y"].values)
        pitch = np.median(np.diff(ys)) if len(ys) > 2 else b["h"].median() * 1.5
        for _, r in isin.iterrows():
            row = b[(b["y"] - r["y"]).abs() < 0.45 * pitch].copy()
            row["dy"] = (row["y"] - r["y"]).abs()
            rec = {"page": pg, "y": r["y"], "isin": r["text"]}
            left = row[row["x1"] < r["x0"]].sort_values("x0")
            left_txt = " ".join(left["text"])
            m = re.match(r"^\s*([\d,]+\.\d+)\s+([\d,]+\.\d+)\s*(.*)$", left_txt)
            if m:
                rec["high_52w"], rec["low_52w"], rec["name_raw"] = _to_num(m.group(1)), _to_num(m.group(2)), m.group(3)
            else:
                rec["name_raw"] = re.sub(r"^[\d,.\s]+", "", left_txt)
            best: dict[str, tuple[float, float]] = {}
            for _, c in row[row["x0"] > isin_x + 0.04 * page_width].iterrows():
                if not re.match(r"^-?[\d,]*\.?\d+$", c["text"].replace(" ", "")):
                    continue
                k = names[int(np.argmin([abs(c["x1"] - ce) for ce in centers]))]
                if k not in best or c["dy"] < best[k][0]:          # nearest box wins
                    best[k] = (c["dy"], _to_num(c["text"]))
            rec.update({k: v for k, (_, v) in best.items()})
            status = row[(row["x0"] > r["x1"]) & (row["x0"] < isin_x + 0.04 * page_width)]
            rec["status"] = " ".join(status["text"]) if len(status) else ""
            rows.append(rec)
    return pd.DataFrame(rows)


def attach_codes(df: pd.DataFrame, sectors: pd.DataFrame) -> pd.DataFrame:
    """Match OCR'd company names to NSE tickers (fuzzy, via clean.match_codes)."""
    from .clean import match_codes
    tmp = df.rename(columns={"name_raw": "cma_name"})
    tmp["cma_name"] = tmp["cma_name"].fillna("").str.replace(r"(s[mn]?e|ser|sr|er)$", "", regex=True)
    out = match_codes(tmp, sectors)
    return out.rename(columns={"cma_name": "name_raw"})


def day_from_name(path: Path) -> pd.Timestamp:
    return pd.to_datetime(path.stem, format="%d-%b-%y")


def process_pdf(path: Path, sectors: pd.DataFrame, dpi: int = 200) -> pd.DataFrame:
    """OCR one daily price list -> rows in the standard price schema (cached per day)."""
    cache = OCR_DIR / "days" / f"{path.stem}.csv"
    if cache.exists():
        return pd.read_csv(cache, parse_dates=["date"])
    boxes = ocr_pdf(path, dpi)
    df = attach_codes(parse_boxes(boxes, 8.5 * dpi), sectors)
    df = df[df["code"].notna() & (df["match_score"] >= 0.6)].drop_duplicates("code")
    for c in ["high", "low", "vwap", "prev", "volume"]:
        if c not in df:
            df[c] = np.nan
    df["volume"] = df["volume"].fillna(0)
    traded = df["volume"] > 0
    df["close"] = np.where(traded, df["vwap"], df["prev"])            # no trade -> price carries over
    est = traded & df["vwap"].isna()
    df.loc[est, "close"] = (df.loc[est, "high"] + df.loc[est, "low"]) / 2
    df["close_estimated"] = est
    df["day_low"] = np.where(traded, df["low"], df["close"])
    df["day_high"] = np.where(traded, df["high"], df["close"])
    df["date"] = day_from_name(path)
    sec = sectors.drop_duplicates("code").set_index("code")["sector_name"]
    df["name"] = df["code"].map(sec).fillna(df["name_raw"])
    out = df[["date", "code", "name", "close", "prev", "day_low", "day_high", "volume", "close_estimated",
              "isin", "status", "match_score"]]
    cache.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(cache, index=False)
    return out


def official_close(px: pd.DataFrame, max_gap: float = 0.15) -> pd.DataFrame:
    """Replace each day's close with the NSE's official one: the 'previous' price printed in the next
    trading day's list. It can differ from the day's VWAP (small trades do not set the price).
    Only used when the next list is the very next trading day and the two differ by < max_gap
    (a bigger gap is more likely an OCR misread than a real difference)."""
    px = px.drop_duplicates(["date", "code"]).sort_values(["code", "date"]).reset_index(drop=True)
    cal = pd.Series(sorted(px["date"].unique()))
    nxt = dict(zip(cal[:-1], cal[1:]))
    px["_next"] = px["date"].map(nxt)
    n = px[["date", "code", "prev"]].rename(columns={"date": "_next", "prev": "_next_prev"})
    px = px.merge(n, on=["_next", "code"], how="left")
    # the next list must be the next trading day (at most 4 calendar days later, e.g. over a holiday weekend)
    ok_gap = (px["_next"] - px["date"]).dt.days <= 4
    use = ok_gap & px["_next_prev"].notna() & ((px["_next_prev"] / px["close"] - 1).abs() < max_gap)
    px["close_source"] = np.where(use, "next day's previous", np.where(px["volume"] > 0, "VWAP", "carried"))
    px.loc[use, "close"] = px.loc[use, "_next_prev"]
    # repair OCR misreads (usually a lost decimal point): every price appears on two consecutive lists
    jump = lambda a, b: (a / b - 1).abs() > 0.30                                    # noqa: E731
    fix_c = ok_gap & px["_next_prev"].notna() & jump(px["close"], px["prev"]) & ~jump(px["_next_prev"], px["prev"])
    px.loc[fix_c, "close"] = px.loc[fix_c, "_next_prev"]
    y_close = px.groupby("code")["close"].shift(1)
    y_date = px.groupby("code")["date"].shift(1)
    consecutive = (px["date"] - y_date).dt.days <= 4
    fix_p = consecutive & y_close.notna() & jump(px["prev"], y_close) & ~jump(px["close"], y_close)
    px.loc[fix_p, "prev"] = y_close[fix_p]
    px["repaired"] = np.select([fix_c & fix_p, fix_c, fix_p], ["close+prev", "close", "prev"], "")
    # a misread high/low cannot sit far from the close
    px.loc[px["day_high"] > px["close"] * 1.3, "day_high"] = px["close"]
    px.loc[px["day_low"] < px["close"] / 1.3, "day_low"] = px["close"]
    px["day_low"] = np.minimum(px["day_low"], px["close"])
    px["day_high"] = np.maximum(px["day_high"], px["close"])
    return px.drop(columns=["_next", "_next_prev"])


def quality_checks(px: pd.DataFrame) -> pd.DataFrame:
    """Flag rows that fail sanity checks. Returns px with a 'qc_fail' reason column ('' = OK)."""
    px = px.sort_values(["code", "date"]).copy()
    reason = pd.Series("", index=px.index)
    traded = px["volume"] > 0
    bad_range = traded & ((px["close"] < px["day_low"] * 0.999) | (px["close"] > px["day_high"] * 1.001))
    reason[bad_range] += "close outside low-high;"
    jump = (px["close"] / px["prev"] - 1).abs() > 0.30
    reason[jump] += "move >30% vs prev;"
    # previous price should equal yesterday's close in our own series
    y_close = px.groupby("code")["close"].shift(1)
    chain = y_close.notna() & ~np.isclose(px["prev"], y_close, rtol=2e-3)
    reason[chain] += "prev != yesterday close;"
    px["qc_fail"] = reason
    return px


def run(start: str, end: str, dpi: int = 200, workers: int = 4) -> pd.DataFrame:
    """Download, OCR (in parallel, resuming from the per-day cache) and quality-check."""
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from .config import PROCESSED
    sectors = pd.read_parquet(PROCESSED / "sectors.parquet")
    files = sorted(download(start, end), key=day_from_name)
    todo = [f for f in files if not (OCR_DIR / "days" / f"{f.stem}.csv").exists()]
    print(f"{len(files)} price lists, {len(files) - len(todo)} already done, {len(todo)} to OCR "
          f"with {workers} workers", flush=True)
    t0 = time.time()
    if todo:
        threads = max(1, (os.cpu_count() or 4) // workers)
        with ProcessPoolExecutor(workers, initializer=_init_worker, initargs=(threads,)) as ex:
            futs = {ex.submit(process_pdf, f, sectors, dpi): f for f in todo}
            for i, fu in enumerate(as_completed(futs), 1):
                f = futs[fu]
                try:
                    n = len(fu.result())
                    print(f"  [{i}/{len(todo)}] {f.stem}: {n} rows ({time.time() - t0:.0f}s elapsed)", flush=True)
                except Exception as e:                       # one bad PDF should not stop the run
                    print(f"  [{i}/{len(todo)}] {f.stem}: FAILED {e}", flush=True)
    parts = [process_pdf(f, sectors, dpi) for f in files if (OCR_DIR / "days" / f"{f.stem}.csv").exists()]
    px = quality_checks(official_close(pd.concat(parts, ignore_index=True)))
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    px.to_csv(OCR_DIR / "prices_ocr.csv", index=False)
    n_bad = (px["qc_fail"] != "").sum()
    print(f"Saved {len(px):,} rows, {px['date'].nunique()} days, {px['code'].nunique()} stocks; "
          f"{n_bad} rows fail a check ({n_bad / len(px):.1%})")
    return px


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-06-22")
    ap.add_argument("--end", default=pd.Timestamp.today().strftime("%Y-%m-%d"))
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    run(a.start, a.end, a.dpi, a.workers)


if __name__ == "__main__":
    main()
