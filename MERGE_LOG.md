# Merge log — what was actually done

Companion to [MERGE_PLAN.md](MERGE_PLAN.md), which was written before any code changed. Work done 17 November 2026.

**Neither original project was modified.** This folder is a fresh clone of `ObiwanKenobee/rock-atlas`; Bedrock was
copied in from `c:\Users\Admin\OneDrive\Desktop\BEDROCK`, which is unchanged and still pushed to
`github.com/trevorblue/bedrock`.

---

## 1. What was added

| Added | What it is |
|---|---|
| `bedrock/` | Bedrock's complete Python engine, copied in: 19 modules, 16 tests, the research note, figures and build log |
| `export_for_atlas.py` | Turns Bedrock's pipeline results into static files the React app reads |
| `public/data/nse_prices.csv` | 44,961 real NSE price rows (64 stocks, 16 Nov 2023 → 16 Nov 2026) in **Atlas's own CSV column format** |
| `public/data/bedrock/*.json` | 13 result files: depth, flows, sell-off, crash, GARCH, speculation, radar, demo data, provenance |
| `src/bedrock/` | Types, the data loader, formatting helpers, and a faithful TypeScript port of the stress model |
| `src/components/bedrock/` | The Bedrock pages and the blocks that sit inside Atlas's own workspaces |
| `src/AppMerged.tsx` | The merged shell: grouped sidebar, real-data loading, every page wired up |
| `vercel.json` | Static deployment config, so the build serves correctly on Vercel |

## 2. What was kept, untouched

- All eight ROCK ATLAS workspaces (`src/components/workspaces/`) — **not one line changed**.
- All six TypeScript engines (`src/engines/`) — not one line changed. They now run on real data instead of synthetic.
- `src/App.tsx`, the original MVP shell, is kept beside the merged one as the record of the partner's work.
- His synthetic corpus, 10-point validation suite, provenance cards, weight sliders, portfolio lab, backtester,
  research brief generator, AI narrative, 9-step guided demo and dark theme: all present and working.
- His seven engine tests still pass unchanged (`npm test` → 7/7).

## 3. The merged navigation

**Group A — Real NSE data** (15 pages). His eight workspaces keep their names and numbers, each gaining a Bedrock
block; Bedrock's seven pages follow as 09–15.

| # | Page | Atlas content | Bedrock block added |
|---|---|---|---|
| 01 | Command Centre | breadth, sectors, index, movement monitor | five headline findings across the engine |
| 02 | Opportunity Radar | 5-factor score, sliders, evidence, invalidation | the exit check and its tested record |
| 03 | Security Explorer | price, SMAs, volume, drawdown, fundamentals | the stock report: five signals with evidence and confidence |
| 04 | Risk Laboratory | Sharpe, VaR, drawdowns, correlations, portfolio, stress scenarios | days to exit, and the foreign-selling stress test |
| 05 | Predictive Models | Ridge forecast, baselines, backtest with costs | the three tested Bedrock models and their records |
| 06 | Resilience Index | KMRI, sliders, cohort test, rank stability | the out-of-sample test of whether resilience repeats |
| 07 | Research Studio | 22-section brief, markdown export, AI narrative | — (runs on real data) |
| 08 | Data Governance | provenance card, 10-point suite, status ledger | Bedrock's real sources and OCR quality |
| 09–15 | Market Depth · Sell-off Alert · Crash Risk · Speculation Watch · Stress Test · Market-Ready · Guide | — | new pages |

**Group B — Demo** (12 pages). His eight workspaces cloned exactly, running on his synthetic corpus, plus Bedrock's
four demo pages. Every one carries a banner saying the figures are invented.

The demo clones are the **same components** as the real pages. Only the dataset differs, so nothing is duplicated in
code and his original behaviour is preserved exactly.

## 4. How real data reaches his engines

`export_for_atlas.py` writes Bedrock's real prices in the exact column format his parser already accepts
(`date,ticker,name,sector,high,low,close,volume,turnover`). On load, the app feeds that file through **his own**
`parseCsvDataset`, so all six of his engines compute on real NSE data with no change to his code.

Two columns are genuinely unavailable in public data and his app already handles both:
- `open` is not published, so his parser falls back to the close.
- `foreign_turnover` per stock does not exist publicly, so his KMRI drops the participation dimension by itself.

Bedrock's model results are read separately from JSON, because they come from Python models (XGBoost, Isolation
Forest, GARCH) that cannot run in a browser.

The stress test was ported to TypeScript line for line (`src/bedrock/stressModel.ts`) so the scenario stays
interactive; the Python version remains the source of truth and produces identical numbers.

## 5. Conflicts, and how each was settled

| Conflict | Settlement |
|---|---|
| His opportunity score weights fundamentals and valuation at 45%, and no real NSE company financials exist | Kept exactly as built. On real data his engine marks those dimensions unavailable and applies a neutral 50, which it states on screen. Bedrock's exit check and tested score sit below. The full five-factor experience lives on in **Opportunity Radar (demo)** |
| His KMRI cohort test is scored inside the same window it measures | Both shown. His test runs on real data; Bedrock's out-of-sample test sits beneath it and reports that resilience did **not** reliably repeat (+0.2%, t = 0.3 over 54 falling months) |
| His Ridge model trailed a naive baseline on synthetic data | Now runs on real data, with Bedrock's tested models shown beside it for comparison. The synthetic result stays on **Predictive Models (demo)** |
| Demo data mixed with real company names | Demo pages are a separate sidebar group with an amber banner; Bedrock's demo pages use fictional names only ("Demo Company A") |
| Product name | ROCK ATLAS is the product; the sidebar and footer credit "Intelligence engine: Bedrock" |

## 6. Problems found in the MVP, and what was done

1. **`npm install` failed on a fresh machine.** `esbuild@^0.25.0` conflicted with the peer range Vite 8 requires
   (`^0.27 || ^0.28`), so install aborted with `ERESOLVE`. This would also have broken any Vercel build. Bumped to
   `^0.28.0`; install now completes cleanly (264 packages, 0 vulnerabilities).
2. **`/api/*` returns 404 on the deployed site.** The Express server is not running there, so saving datasets and
   reports, and the AI brief, do not work in production. The deterministic brief needs no server and still works.
   Added `vercel.json` for a correct static build. Restoring the API needs serverless functions: not done here.
3. **`package.json` was still named `react-example`.** Renamed to `rock-atlas`.
4. **His status ledger row "Phase 02: Data Acquisition — Blocked / Pending Data"** is still accurate, since it
   refers to Rock Data Plus files specifically, not to NSE data in general. Left as he wrote it.

## 7. Checks run

| Check | Result |
|---|---|
| `npm run lint` (TypeScript, strict) | passes, no errors |
| `npm test` (his engine tests) | 7 / 7 pass |
| `npm run build` | succeeds, 1,690 modules, 485 KB JS (137 KB gzipped) |
| Bedrock's Python tests | 16 / 16 pass in the original project |
| Every page opened in a browser | 27 pages render; no uncaught errors |
| Numbers cross-checked against Bedrock's Streamlit app | identical (67% depth, HIGH RISK, 16 trapped, −4.0%, 10.9% crash rate) |

## 8. Not done

- No push to either GitHub repository. This folder is local, with the partner's repo attached only as a remote
  named `atlas-upstream` so his later work can be pulled in.
- The API features (saved datasets, saved reports, AI brief) are not converted to serverless functions.
- His predictive backtest has not been re-tuned for real data; it is reported as it comes out.
- No Rock Data Plus files are used anywhere: everything is public data plus Bedrock's OCR of NSE price lists.
