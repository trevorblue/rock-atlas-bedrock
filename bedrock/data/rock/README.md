# Rock Data Plus drop folder

Put Rock exports here as CSV. Files in this folder are git-ignored, apart from this README, so licensed data never reaches GitHub.
When a file below exists, `bedrock.clean` uses it **instead of** the public source. Then rerun `python -m bedrock.pipeline`.

| File | Columns (header row, exact names) | Replaces |
|---|---|---|
| `prices.csv` | `date, code, name, close, prev, day_low, day_high, volume` | Mendeley NSE daily prices |
| `foreign_flows.csv` | `period, net_flow_kes_m` (optional: `buys_kes_m, sells_kes_m`) | CMA monthly net flows |

Notes
- `date` / `period` as `YYYY-MM-DD`. Weekly flows should use the week-ending date (Friday). Module B detects weekly data automatically.
- `close` = the day's closing or VWAP price; `prev` = the previous close; `volume` = shares traded (0 if none).
- Bonds (optional Module D) would use `gov_yields.csv` and `corp_bonds.csv`. See `src/bedrock/bonds.py`.
- If Rock's column names differ, rename them in a small script, or add a mapping in `clean.load_prices_raw`.
