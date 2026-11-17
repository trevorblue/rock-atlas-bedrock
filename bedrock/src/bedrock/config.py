"""Paths and model settings for Bedrock. Change numbers here, not inside the modules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
ROCK = DATA / "rock"  # drop Rock Data Plus exports here (git-ignored)
MANUAL = DATA / "manual"  # hand-made inputs that ARE committed (news checks)

for _p in (RAW, PROCESSED, ROCK, MANUAL):
    _p.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

# ---------- Module A: Market Depth ----------
POSITION_KES = 10_000_000      # position size for "days to exit"
PARTICIPATION = 0.20           # max share of a day's average value traded you can sell
LOOKBACK_DAYS = 120            # trading days used for liquidity metrics (~6 months)
BLOCK_MULT = 10            # a day counts for at most 10x the stock's median traded day (block deals)
TIER_BOUNDS = (2, 20, 250)     # days to exit: <=2 Deep, <=20 Moderate, <=250 Thin, else Frozen
N_CLUSTERS = 3                 # K-means cross-check on stocks that traded in the window
EXIT_THRESHOLDS = (5, 20)      # headline: % of stocks taking > Y days to exit

# ---------- Module B: Sell-off Alert ----------
# Inputs of the live sell-off model. Chosen by an out-of-sample comparison of 3 input sets x 2 models
# (robustness.selloff_feature_sets): with ~140 monthly points, flows alone beat flows + macro + market.
SELLOFF_FEATURES = ["flow", "flow_3"]
SELLOFF_QUANTILE = 0.25        # "heavy selling" = net foreign flow in worst 25% of periods
MIN_TRAIN_PERIODS = 60         # walk-forward: first model trained on 60 months
HIGH_RISK_PROB = 0.45          # p >= this -> "HIGH RISK"; below -> "NO CALL".
# No "LOW RISK" band: out of sample, low readings (<= 15%) were followed by heavy selling 21% of the time,
# close to the 26% normal rate, so the model cannot give an all-clear.

# ---------- Module C: Speculation Watch ----------
ANOMALY_WINDOW = 60            # each stock's own "normal" = previous 60 trading days
ANOMALY_CONTAMINATION = 0.01   # share of stock-days the Isolation Forest flags
FWD_HORIZONS = (5, 20)         # trading days after a flag used to check what happened next

# ---------- Screen 4: Stress Test ----------
DEFAULT_SCENARIO_KES = 2_000_000_000
DEFAULT_SCENARIO_DAYS = 5
IMPACT_K = 1.0                 # square-root impact law coefficient
STRATEGIC_CUTOFF = 0.50        # foreign stakes above this are treated as a parent's strategic holding (not sold)

RANDOM_STATE = 42
