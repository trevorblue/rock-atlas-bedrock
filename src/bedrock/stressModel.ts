/**
 * Faithful TypeScript port of Bedrock's stress test (bedrock/src/bedrock/stress.py), so the scenario stays
 * interactive in the browser. The Python version remains the source of truth and is unchanged; this file
 * reproduces it line for line:
 *
 *   1. Split the foreign sale across stocks in proportion to foreign-held value (foreign % x market cap).
 *      A stake above the strategic cut-off is assumed held by a foreign parent and is not sold.
 *   2. Days to absorb = the stock's share of the sale / (participation x average daily value traded).
 *   3. Price impact from the square-root law: impact = -min(k x daily volatility x sqrt(sale / ADV), 0.9).
 *   4. Status: no trades at all -> "no market"; clears inside the window -> "absorbed"; inside 4x -> "strained";
 *      longer -> "trapped".
 */
import { DepthRow } from './types';

export interface StressInputs {
  totalSellKes: number;
  days: number;
  participation: number;
  maxForeignPct: number;
}

export interface StressRow {
  code: string;
  name: string;
  sector: string | null;
  tier: string;
  foreignPct: number;
  foreignValueKes: number;
  sellKes: number;
  advKes: number;
  sellVsAdv: number | null;
  daysToAbsorb: number | null;
  priceImpact: number | null;
  status: 'not hit' | 'no market' | 'absorbed' | 'strained' | 'trapped';
}

export interface StressSummary {
  totalSellKes: number;
  nHit: number;
  nTrapped: number;
  nNoMarket: number;
  valueTrappedKes: number;
  weightedImpact: number;
}

const IMPACT_K = 1.0;

const median = (xs: number[]): number => {
  const s = xs.filter((x) => Number.isFinite(x)).slice().sort((a, b) => a - b);
  if (s.length === 0) return 0;
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
};

export function runScenario(snapshot: DepthRow[], inputs: StressInputs): StressRow[] {
  const { totalSellKes, days, participation, maxForeignPct } = inputs;

  const universe = snapshot.filter(
    (r) => r.instrument === 'Equity' && r.foreign_pct !== null && r.market_cap_kes !== null
  );

  const medianVol = median(universe.map((r) => r.volatility ?? NaN));

  const foreignValue = universe.map((r) =>
    (r.foreign_pct as number) <= maxForeignPct ? (r.foreign_pct as number) * (r.market_cap_kes as number) : 0
  );
  const totalFv = foreignValue.reduce((a, b) => a + b, 0);

  return universe
    .map((r, i): StressRow => {
      const weight = totalFv > 0 ? foreignValue[i] / totalFv : 0;
      const sellKes = weight * totalSellKes;
      const adv = r.adv_kes > 0 ? r.adv_kes : null;
      const vol = r.volatility ?? medianVol;

      const daysToAbsorb = adv === null ? null : sellKes / (participation * adv);
      let priceImpact: number | null =
        adv === null ? null : -Math.min(IMPACT_K * vol * Math.sqrt(sellKes / adv), 0.9);
      if (sellKes <= 0) priceImpact = 0;

      let status: StressRow['status'];
      if (sellKes <= 0) status = 'not hit';
      else if (r.adv_kes <= 0) status = 'no market';
      else if ((daysToAbsorb as number) <= days) status = 'absorbed';
      else if ((daysToAbsorb as number) <= 4 * days) status = 'strained';
      else status = 'trapped';

      return {
        code: r.code,
        name: r.name,
        sector: r.sector,
        tier: r.tier,
        foreignPct: r.foreign_pct as number,
        foreignValueKes: foreignValue[i],
        sellKes,
        advKes: r.adv_kes,
        sellVsAdv: adv === null ? null : sellKes / days / adv,
        daysToAbsorb,
        priceImpact,
        status,
      };
    })
    .sort((a, b) => (a.priceImpact ?? 0) - (b.priceImpact ?? 0));
}

export function summarize(rows: StressRow[], totalSellKes: number): StressSummary {
  const hit = rows.filter((r) => r.sellKes > 0);
  const withMarket = hit.filter((r) => r.status !== 'no market');
  const sellSum = withMarket.reduce((a, r) => a + r.sellKes, 0);
  const weightedImpact =
    sellSum > 0 ? withMarket.reduce((a, r) => a + (r.sellKes / sellSum) * (r.priceImpact ?? 0), 0) : 0;

  const trapped = hit.filter((r) => r.status === 'trapped' || r.status === 'no market');

  return {
    totalSellKes,
    nHit: hit.length,
    nTrapped: trapped.length,
    nNoMarket: hit.filter((r) => r.status === 'no market').length,
    valueTrappedKes: trapped.reduce((a, r) => a + r.sellKes, 0),
    weightedImpact,
  };
}

/** Days to sell a position, Bedrock's definition: position / (participation x average daily value traded). */
export function daysToExit(advKes: number, positionKes: number, participation = 0.2): number | null {
  if (!Number.isFinite(advKes) || advKes <= 0) return null;
  return positionKes / (participation * advKes);
}
