# Bedrock

**What really holds up the NSE rally?**

The Nairobi Securities Exchange is at record highs, but the market is shallow. A few stocks carry nearly all the trading, many barely trade, and foreign investors keep selling. Bedrock measures how deep the market really is. It warns when heavy foreign selling is likely, ranks each stock's risk of a crash next month, flags price moves that look like speculation, and stress-tests what happens when foreigners sell.

> **Headline (data to 16 Nov 2026):** 67% of listed shares would take more than 20 trading days to exit a KES 10m position, and five stocks make up 74% of value traded. Foreigners were net sellers in 73% of months since 2019 (KES 127bn out), and the early-warning model reads HIGH RISK for October 2026. Stock by stock, the 10% ranked riskiest each month crashed (fell 15%+) twice as often as average in out-of-sample tests.

## The dashboard

**Live:** link added once deployed on Streamlit Community Cloud. Locally: `streamlit run app/streamlit_app.py`.

| Screen | What you see |
|---|---|
| Overview | The five answers on one page, with the depth and foreign-flow history |
| Market depth | Every NSE stock ranked by how easy it is to sell, in tiers (Deep / Moderate / Thin / Frozen), with "days to exit a KES 10m position" |
| Sell-off alert | Chance of heavy foreign selling next period, the top reasons, a HIGH RISK / NO CALL signal (no 'low risk' all-clear), and an honest out-of-sample test |
| Crash risk | Each stock's risk of falling 15%+ in the next month (XGBoost, 14 inputs), its risk group and how often that group crashed in testing, against a simple volatility rule |
| Opportunities | Opportunity Radar: stocks scored on momentum, stability and resilience, but only after the "can you get out?" exit check; plus the stocks that look good on paper but can't be sold |
| Stock report | One page per stock: can you get out, opportunity score, crash risk, speculation flags, stress test, each with its evidence, how sure we are and what would change the view |
| Fundamentals (demo) | **Synthetic demo data for fictional companies**, showing how a value-and-quality screen would work once real company financials are added. Not real; used nowhere else |
| Market-ready | The data, product and model upgrades that would make Bedrock production-grade |
| Speculation | Stock-days where price and volume broke from the stock's own normal and the market did not move with it |
| Stress test | Choose a scenario (e.g. foreigners sell KES 2bn in 5 days) and see which stocks absorb it, which strain, and which are trapped |

## Quick start

```bash
git clone <your-repo-url> bedrock && cd bedrock
python -m venv .venv && .venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
pip install -e .
python -m bedrock.download      # ~40 MB of public data, about 2 minutes
python -m bedrock.pipeline      # cleans data, runs all models, about 1 minute
streamlit run app/streamlit_app.py
```

Optional steps:

```bash
pip install -r requirements-ocr.txt
python -m bedrock.nse_ocr       # extend prices past June 2026 from the NSE's scanned daily price lists (~1 hour)
python -m bedrock.pipeline      # rerun: picks up the OCR prices automatically
python -m bedrock.figures       # charts for the note -> reports/figures/
python -m bedrock.note_pdf      # research note -> reports/bedrock_note.pdf (needs playwright + Chrome/Edge)
python -m bedrock.publish       # copy outputs to app/snapshot/ for Streamlit Cloud (refuses if built from Rock data)
pytest -q                       # unit tests (also run by GitHub Actions)
```

**Deploy:** push to GitHub, then on [share.streamlit.io](https://share.streamlit.io) choose the repo and `app/streamlit_app.py`.
The deployed app reads the committed `app/snapshot/`.

**Research note:** [reports/bedrock_note.md](reports/bedrock_note.md).

To use **Rock Data Plus**, drop its CSV exports into `data/rock/` (see [data/rock/README.md](data/rock/README.md)) and rerun the pipeline.

## Data

| Data | Source | Coverage |
|---|---|---|
| Daily prices and volumes, all NSE stocks and indices | [Mendeley Data, Wanjawa (CC BY 4.0)](https://data.mendeley.com/datasets/hvmhnp7f9r/1), scraped from MyStocks | Jan 2013 to Jun 2026 |
| Daily prices and volumes, Jul 2026 onward | NSE daily price lists (scanned PDFs, read with OCR and checked row by row); NASI rebuilt from stock prices for these days | Jul to Nov 2026 |
| Hand-checked news for speculation flags | `data/manual/news_checks.csv` (committed) | flagged days |
| Net foreign flows (monthly) | CMA Quarterly Statistical Bulletin, Table 37 | Jan 2015 to Sep 2026 |
| Foreign buys and sells, participation | CMA bulletin | Jan 2023 to Sep 2026 |
| Shares in issue and foreign ownership per company | CMA bulletin, Table 31 | Aug 2026 |
| CBR, interbank, 91/182/364-day T-bills | Central Bank of Kenya | 1991 to 2026 |
| KES/USD (monthly average), inflation | Central Bank of Kenya | 2005 to Nov 2026 |
| Brent, US 10y, Fed funds, dollar index, VIX | FRED | daily, to Nov 2026 |

## Method in brief

- **Depth (A):** For each stock over the last 120 trading days, Bedrock measures average daily value traded, the share of days with no trades, Amihud illiquidity (price move per KES 1m traded) and turnover. Days to exit = KES 10m ÷ (20% × average daily value). Tiers use days-to-exit cut-offs, cross-checked with K-means.
- **Sell-off Alert (B):** A month counts as "heavy selling" if its net foreign flow is in the worst 25% of months. Three input sets × two models (logistic, shallow XGBoost) are compared with the plain base rate in a **walk-forward test** (retrained each month on past data only). All versions are reported. The live model is the winner, XGBoost on foreign flows alone: HIGH RISK calls hit 59% vs 26% normally (p = 0.004).
- **Speculation Watch (C):** An Isolation Forest runs on each stock-day's return, volume, market-relative return and price range, compared with the stock's previous 60 days. Flags are validated by what happens over the next 5 and 20 days.
- **Crash Risk (E):** One row per stock per month-end. Target: the stock falls 15% or more over the next 21 trading days. Inputs use only data known that day (returns, volatility, distance from 1-year high, liquidity, spikes, NASI, foreign flows). Walk-forward by year with purging, 2016–2026 (7,154 test stock-months). The riskiest 10% crashed 10.9% of the time vs 5.5% average; a "most volatile 10%" rule gets 9.2%, and the model's ranking is not clearly better than volatility alone. Both are reported.
- **Opportunity Radar (F):** Equal-weight score (fixed in advance) of momentum (12-1 months), low volatility and resilience (return vs the market in falling months, last 3 years). A stock counts only if a position can be sold within 20 trading days at 20% of daily trading. Tested monthly 2016–2026: top third beat bottom third by +0.7% a month (t = 1.3, not yet proven); without the exit check 42% (KES 1m) to 67% (KES 10m) of top picks could not be sold. Resilience did not reliably repeat in the next falling month (+0.2%, t = 0.3).
- **Stress Test:** A foreign sale is split by foreign-held value, with stakes above 50% treated as a parent's strategic holding. Days to absorb are computed at 20% of daily trading, and price impact uses the square-root law.

## Limitations

- Prices after June 2026 come from OCR of scanned NSE price lists. Rows that fail consistency checks are dropped, and NASI for those days is rebuilt from stock prices (daily correlation 0.97 with the real index).
- Monthly foreign flows give about 140 observations, so the sell-off model's edge is real but modest (AUC 0.64). Weekly flow data is the key upgrade.
- Block deals (e.g. NCBA's KES 100bn transfer on 3 Nov 2026) are capped at 10× a stock's median day for liquidity measures.
- There is no official list of manipulated stocks, so speculation flags are leads to check against news, not verdicts.
- The stress test's price impact is a rule-of-thumb estimate, not a forecast.

## Repo layout

See [PLAN.md](PLAN.md).
