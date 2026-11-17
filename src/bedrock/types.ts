/**
 * Shapes of the files that `export_for_atlas.py` writes into public/data/bedrock/.
 * Every number in them comes from Bedrock's Python pipeline, run on real NSE data.
 */

export interface BedrockMeta {
  asOf: { stocks: string; flows: string; macro: string };
  usesRockData: boolean;
  engine: string;
  sources: string[];
  settings: {
    positionKes: number;
    participation: number;
    lookbackDays: number;
    blockDealCapMultiple: number;
    tierBounds: number[];
    highRiskProb: number;
    impactK: number;
    strategicCutoff: number;
    crashDrop: number;
    crashHorizonDays: number;
    exitDays: number;
  };
}

export interface DepthHeadline {
  n_stocks: number;
  as_of: string;
  pct_over_5d: number;
  pct_over_20d: number;
  pct_no_trade_in_window: number;
  top5_share_of_value: number;
}

export interface Headline {
  depth: DepthHeadline;
  selloff: { period: string; probability: number; signal: string; model: string };
  stress_default: {
    total_sell_kes: number;
    n_hit: number;
    n_trapped: number;
    n_no_market: number;
    value_trapped_kes: number;
    weighted_impact: number;
    worst: Array<{ code: string; price_impact: number; days_to_absorb: number }>;
  };
  crash?: {
    top10_rate: number;
    base_rate: number;
    safest10_rate: number;
    rule_top10_rate: number;
    riskiest_now: string[];
  };
  uses_rock_data: boolean;
  data_as_of: { stocks: string; flows: string; macro: string };
}

/** One ordinary share in Bedrock's liquidity snapshot. `days_to_exit` is null when it never traded. */
export interface DepthRow {
  code: string;
  name: string;
  sector: string | null;
  instrument: string;
  tier: string;
  days_to_exit: number | null;
  adv_kes: number;
  median_value_kes: number | null;
  zero_trade_share: number;
  amihud: number | null;
  turnover_annual: number | null;
  market_cap_kes: number | null;
  foreign_pct: number | null;
  volatility: number | null;
  price: number | null;
  as_of: string;
}

export interface SelloffLive {
  period: string;
  probability: number;
  signal: string;
  threshold_kes_m: number;
  base_rate: number;
  model: string;
  features_used: string[];
  features_dropped: string[];
  n_train: number;
  freq: string;
}

export interface SelloffBundle {
  live: SelloffLive;
  walkForward: Array<{
    period: string;
    threshold: number;
    actual: number;
    flow_next: number;
    climatology: number;
    logistic: number;
    xgboost: number;
  }>;
  evaluation: Array<Record<string, number | string>>;
  significance: Array<{
    model: string;
    high_risk_calls: number;
    hits: number;
    hit_rate: number;
    base_rate: number;
    p_value_vs_base: number;
  }>;
  featureSets: Array<Record<string, number | string | null>>;
  calibration: Array<{ bin: string; n: number; predicted: number; actual: number }>;
  thresholds: Array<Record<string, number | string>>;
  drivers: Array<{ feature: string; label: string; value: number; contribution: number; direction: string }>;
}

export interface CrashSummary {
  crash_drop: number;
  horizon_days: number;
  n_test: number;
  n_samples: number;
  n_stocks: number;
  first_test_year: number;
  base_rate: number;
  top10_rate: number;
  lift: number;
  p_value_top10: number;
  safest10_rate: number;
  rule_top10_rate: number;
  auc_model: number;
  auc_rule: number;
  auc_gap_vs_rule: { gap: number; ci_low: number; ci_high: number };
  riskiest_now: string[];
  as_of: string;
}

export interface CrashBundle {
  summary: CrashSummary;
  live: Array<{
    date: string;
    code: string;
    name: string;
    close: number;
    crash_prob: number;
    risk_rank: number;
    risk_decile: number;
    group_crash_rate: number;
    mom_1m: number | null;
    mom_3m: number | null;
    vol_60: number | null;
    dd_1y: number | null;
    zero_60: number | null;
    spikes_60: number | null;
    garch_vol?: number | null;
  }>;
  deciles: Array<{ decile: number; stock_months: number; crash_rate: number; avg_predicted: number }>;
  compare: Array<{
    model: string;
    auc: number;
    top10_crash_rate: number;
    top10_n: number;
    lift: number;
    p_value_top10: number;
    caught_in_top20: number;
    brier_skill: number | null;
    base_rate: number;
    n: number;
  }>;
  byYear: Array<{
    year: number;
    stock_months: number;
    crashes: number;
    base_rate: number;
    auc_model: number;
    auc_volatility: number;
    top10_crash_rate: number;
  }>;
  robust: Array<{ crash_definition: string; base_rate: number; auc_model: number; auc_volatility: number }>;
  importance: Array<{ feature: string; importance: number; label: string }>;
  garch: {
    n: number;
    median_error_garch: number;
    median_error_last60: number;
    garch_closer_share: number;
    corr_garch: number;
    corr_last60: number;
    fits: number;
    failed_or_explosive: number;
    auc_gap_vs_last60_rule: { gap: number; ci_low: number; ci_high: number };
    auc_gap_vs_live_model: { gap: number; ci_low: number; ci_high: number };
  } | null;
}

export interface SpeculationBundle {
  recentFlags: Array<{
    date: string;
    code: string;
    name: string;
    close: number;
    ret: number;
    ex_ret: number;
    value_kes: number;
    z_ret: number;
    z_value: number;
    anomaly_score: number;
    direction: string;
    fwd_5d: number | null;
    fwd_20d: number | null;
    news: string;
  }>;
  totalFlags: number;
  validation: Array<Record<string, number | string>>;
  bootstrap: Array<{
    size: string;
    horizon: string;
    n_watch: number;
    n_other: number;
    n_stocks: number;
    watch_mean: number;
    other_mean: number;
    gap: number;
    ci_low: number;
    ci_high: number;
    ci_excludes_zero: boolean;
  }>;
  newsChecked: number;
  noNews: number;
}

export interface RadarBundle {
  summary: {
    months: number;
    first: string;
    last: string;
    avg_ok_stocks: number;
    top_avg: number;
    bottom_avg: number;
    spread_avg: number;
    spread_t: number;
    spread_win_share: number;
    top_vs_all_avg: number;
    top_vs_all_t: number;
    paper_fail_share_1m: number;
    paper_fail_share_10m: number;
    res_months: number;
    res_top_avg: number;
    res_bottom_avg: number;
    res_spread_avg: number;
    res_spread_t: number;
    res_win_share: number;
    exit_days: number;
    test_position_kes: number;
  };
  live: Array<{
    date: string;
    code: string;
    name: string;
    score: number;
    paper_rank: number;
    mom_12_1: number;
    vol_60: number;
    resilience: number;
    adv: number;
    days_exit_1m: number | null;
    days_exit_10m: number | null;
    days_exit_50m: number | null;
    exit_ok_1m: boolean;
    exit_ok_10m: boolean;
    exit_ok_50m: boolean;
  }>;
  monthly: Array<Record<string, number | string>>;
  resilienceMonthly: Array<Record<string, number | string>>;
}

export interface DemoBundle {
  fundamentals: Array<Record<string, number | string | boolean>>;
  opportunities: Array<Record<string, number | string | boolean>>;
  foreignFlows: Array<{ date: string; company: string; turnover_kes: number; net_foreign_kes: number; net_foreign_share: number }>;
  selloffFlows: Array<{ period: string; flow: number; flow_3: number | null; flow_next: number | null }>;
  selloffWalkForward: Array<{ period: string; actual: number; xgboost: number; climatology: number; logistic: number }>;
  selloffLive: SelloffLive | null;
}

export interface BedrockData {
  meta: BedrockMeta;
  headline: Headline;
  depth: DepthRow[];
  depthHistory: Array<{ as_of: string; pct_over_20d: number; pct_over_5d?: number; n_stocks?: number }>;
  concentration: Array<{ period: string; total_value_kes: number; top5_share: number; n_traded?: number }>;
  robustnessDepth: {
    sensitivity: Array<{ lookback_days: number; position_kes: number; participation: number; pct_over_20d: number; pct_over_5d: number; n_stocks: number }>;
    blockCap: Array<{ block_cap: string; pct_over_20d: number; pct_over_5d: number; top5_share_of_value: number; n_stocks: number }>;
  };
  selloff: SelloffBundle;
  flows: Array<{ period: string; flow: number; flow_3: number | null }>;
  crash: CrashBundle;
  speculation: SpeculationBundle;
  radar: RadarBundle;
  demo: DemoBundle;
  pricesMeta: { rows: number; stocks: number; start: string; end: string; note: string };
}
