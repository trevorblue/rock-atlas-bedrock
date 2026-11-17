"""Download every public dataset Bedrock uses.

    python -m bedrock.download            # skip files already on disk
    python -m bedrock.download --force    # re-download everything

Sources
-------
NSE daily prices   Mendeley Data (Wanjawa), CC BY 4.0, 2013 - Jun 2026
Foreign flows      CMA Quarterly Statistical Bulletin (Table 37 monthly net flows; Table 31 ownership)
Kenya macro        Central Bank of Kenya (FX, CBR, T-bills, interbank, inflation, GDP, debt)
Global macro       FRED (Brent, US 10y, Fed funds, broad USD index, VIX)
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import requests

from .config import RAW, USER_AGENT

S = requests.Session()
S.headers["User-Agent"] = USER_AGENT
CBK = "https://www.centralbank.go.ke"


def _get(url: str, timeout: int = 120, retries: int = 3, **kw) -> requests.Response:
    last = None
    for i in range(retries):
        try:
            r = S.get(url, timeout=timeout, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException as e:  # noqa: PERF203
            last = e
            time.sleep(2 * (i + 1))
    raise last  # type: ignore[misc]


def _save(url: str, dest: Path, force: bool, timeout: int = 120) -> bool:
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"  have  {dest.relative_to(RAW)}")
        return True
    try:
        r = _get(url, timeout=timeout)
    except requests.RequestException as e:
        print(f"  FAIL  {dest.name}: {e}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    print(f"  got   {dest.relative_to(RAW)} ({len(r.content)/1e3:,.0f} kB)")
    return True


# ---------------------------------------------------------------- CBK
# (page to scan, keyword in the CSV link, local name). The numeric ids in CBK
# links change when files are refreshed, so we look the link up each time.
CBK_FILES = [
    ("/statistics/interest-rates/", "Central Bank Rates", "central_bank_rate.csv"),
    ("/statistics/interest-rates/", "Weighted Average Rates", "bank_weighted_rates.csv"),
    ("/statistics/exchange-rates/", "period average", "fx_monthly_avg.csv"),
    ("/statistics/exchange-rates/", "end period", "fx_monthly_end.csv"),
    ("/statistics/national-accounts-statistics/", "Quarterly GDP", "gdp_quarterly.csv"),
    ("/statistics/government-finance-statistics/", "Domestic Debt by Instrument", "domestic_debt.csv"),
    ("/statistics/government-finance-statistics/", "Public Debt", "public_debt.csv"),
]


def download_cbk(force: bool = False) -> None:
    print("CBK")
    out = RAW / "cbk"
    pages: dict[str, str] = {}
    for page, key, name in CBK_FILES:
        if page not in pages:
            try:
                pages[page] = _get(CBK + page).text
            except requests.RequestException as e:
                print(f"  FAIL  page {page}: {e}")
                pages[page] = ""
        links = re.findall(r'href="([^"]+\.csv)"', pages[page])
        hit = [l for l in links if key.lower() in l.lower()]
        if not hit:
            print(f"  MISS  no link for '{key}' on {page}")
            continue
        url = hit[0] if hit[0].startswith("http") else CBK + hit[0]
        _save(url.replace(" ", "%20"), out / name, force)

    # Inflation is an HTML table, not a CSV.
    dest = out / "inflation.csv"
    if dest.exists() and not force:
        print("  have  cbk/inflation.csv")
        return
    try:
        html = _get(CBK + "/inflation-rates/").text
        cells = re.findall(r"<td[^>]*>([^<]*)</td>", html)
        rows = [cells[i:i + 4] for i in range(0, len(cells) - 3, 4)]
        rows = [r for r in rows if r[0].strip().isdigit()]
        lines = ["year,month,inflation_annual_avg,inflation_12m"] + [",".join(c.strip() for c in r) for r in rows]
        dest.write_text("\n".join(lines))
        print(f"  got   cbk/inflation.csv ({len(rows)} months)")
    except requests.RequestException as e:
        print(f"  FAIL  inflation: {e}")


# ---------------------------------------------------------------- FRED
FRED_SERIES = {
    "DCOILBRENTEU": "Brent crude, USD/bbl",
    "DGS10": "US 10-year Treasury yield",
    "DFF": "US Fed funds rate",
    "DTWEXBGS": "Broad US dollar index",
    "VIXCLS": "VIX volatility index",
}


def download_fred(force: bool = False) -> None:
    print("FRED")
    for sid in FRED_SERIES:
        _save(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", RAW / "fred" / f"{sid}.csv", force)


# ---------------------------------------------------------------- NSE prices (Mendeley)
MENDELEY_SETS = {
    "73rb78pmzw": "NSE all stocks 2013-2020",
    "97hkwn5y3x": "NSE all stocks 2021",
    "jmcdmnyh2s": "NSE all stocks 2022",
    "ss5pfw8xnk": "NSE all stocks 2023-2024",
    "2b63rx67xt": "NSE all stocks 2025",
    "hvmhnp7f9r": "NSE all stocks 2026 (to June)",
}


def download_mendeley(force: bool = False) -> None:
    print("NSE daily prices (Mendeley Data, CC BY 4.0)")
    out = RAW / "nse" / "mendeley"
    hdr = {"Accept": "application/json"}
    for sid, label in MENDELEY_SETS.items():
        try:
            meta = _get(f"https://data.mendeley.com/public-api/datasets/{sid}", headers=hdr).json()
            ver = meta["version"]
            files = _get(
                f"https://data.mendeley.com/public-api/datasets/{sid}/files?folder_id=root&version={ver}", headers=hdr
            ).json()
        except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
            print(f"  FAIL  {label}: {e}")
            continue
        for f in files:
            if f["filename"].lower().endswith(".csv"):
                _save(f["content_details"]["download_url"], out / f["filename"], force, timeout=300)


# ---------------------------------------------------------------- CMA bulletins
CMA_PUBLICATIONS = "https://www.cma.or.ke/publications/"
CMA_KEEP = 3  # newest N quarterly bulletins; Table 37 in the newest one holds the full history


def download_cma(force: bool = False) -> None:
    print("CMA quarterly statistical bulletins")
    try:
        html = _get(CMA_PUBLICATIONS).text
    except requests.RequestException as e:
        print(f"  FAIL  publications page: {e}")
        return
    found = {}
    for url in set(re.findall(r'https?://[^"]+statistical-bulletin[^"]*\.pdf', html)):
        m = re.search(r"q([1-4])[-_.]?(20\d{2})", url.lower())
        if m:
            found[(int(m.group(2)), int(m.group(1)))] = url
    for (year, q) in sorted(found, reverse=True)[:CMA_KEEP]:
        _save(found[(year, q)], RAW / "cma" / f"cma_qsb_q{q}_{year}.pdf", force, timeout=240)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download files already on disk")
    a = ap.parse_args()
    download_mendeley(a.force)
    download_cma(a.force)
    download_cbk(a.force)
    download_fred(a.force)
    print("\nDone. Next: python -m bedrock.pipeline")


if __name__ == "__main__":
    main()
