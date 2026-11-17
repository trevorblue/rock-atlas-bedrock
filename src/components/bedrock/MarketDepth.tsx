import React, { useMemo, useState } from 'react';
import { BedrockData } from '../../bedrock/types';
import { days as fmtDays, kes, niceDate, pct, shortName } from '../../bedrock/data';
import { daysToExit } from '../../bedrock/stressModel';
import { ColumnChart, DataTable, HowToRead, Kpi, KpiRow, ModelStrip, Note, PageHead, Panel, PanelTitle, Pill } from './kit';
import { MultiLineChart } from '../Charts';

const POSITIONS = [1e6, 10e6, 50e6, 100e6];

const BANDS: Array<{ label: string; upper: number; tone: 'good' | 'warn' | 'bad' | 'muted' }> = [
  { label: '≤ 2 days', upper: 2, tone: 'good' },
  { label: '2–5', upper: 5, tone: 'warn' },
  { label: '5–20', upper: 20, tone: 'warn' },
  { label: '20–250', upper: 250, tone: 'bad' },
  { label: '> 250 or none', upper: Infinity, tone: 'bad' },
];

export const MarketDepth: React.FC<{ data: BedrockData }> = ({ data }) => {
  const [position, setPosition] = useState<number>(data.meta.settings.positionKes);
  const participation = data.meta.settings.participation;

  const equities = useMemo(() => data.depth.filter((r) => r.instrument === 'Equity'), [data.depth]);

  const withDays = useMemo(
    () => equities.map((r) => ({ ...r, days: daysToExit(r.adv_kes, position, participation) })),
    [equities, position, participation]
  );

  const over20 = withDays.filter((r) => r.days === null || r.days > 20).length / Math.max(1, withDays.length);
  const within2 = withDays.filter((r) => r.days !== null && r.days <= 2).length;
  const noTrades = withDays.filter((r) => r.days === null).length / Math.max(1, withDays.length);

  const bandCounts = BANDS.map((b, i) => {
    const lower = i === 0 ? -Infinity : BANDS[i - 1].upper;
    const n = withDays.filter((r) => {
      const d = r.days === null ? Infinity : r.days;
      return d > lower && d <= b.upper;
    }).length;
    return { label: b.label, value: n, tone: b.tone, hint: `${b.label}: ${n} stocks` };
  });

  const history = data.depthHistory;
  const sorted = [...withDays].sort((a, b) => (a.days ?? Infinity) - (b.days ?? Infinity));

  return (
    <div className="space-y-6">
      <PageHead
        eyebrow="Market depth · Bedrock engine"
        question="How easy is it to sell a share on the NSE without crashing its price?"
        title={`${pct(over20)} of NSE shares need more than 20 trading days to sell ${kes(position)}`}
        subtitle={`${withDays.length} ordinary shares, ${data.meta.settings.lookbackDays} trading days to ${niceDate(
          data.headline.depth.as_of
        )}. Assumes you sell no more than ${pct(participation)} of a normal day's trading, so your own selling does not crash the price.`}
      />

      <HowToRead
        purpose="Fund managers check how long it would take to get out of a holding before they buy it; Rock's research team tracks whether the market is getting deeper or thinner."
        points={[
          `Days to sell = position ÷ (${pct(participation)} × the stock's average daily value traded).`,
          'More than 20 trading days (about four weeks) counts as hard to sell.',
          'One-off block deals count for at most 10× the stock\'s normal day, so a takeover transfer does not make a stock look liquid.',
        ]}
      />

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500 dark:text-slate-400 mr-1">Position to sell:</span>
        {POSITIONS.map((p) => (
          <button
            key={p}
            onClick={() => setPosition(p)}
            className={`px-3 py-1.5 text-xs font-medium border transition-colors ${
              p === position
                ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 border-slate-900 dark:border-slate-100'
                : 'border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
            }`}
          >
            {kes(p)}
          </button>
        ))}
      </div>

      <KpiRow>
        <Kpi value={pct(over20)} label="need more than 20 trading days to sell" alert />
        <Kpi value={String(within2)} label="stocks can be sold within 2 days" />
        <Kpi value={pct(data.headline.depth.top5_share_of_value)} label="of all trading is in just five stocks" />
        <Kpi value={pct(noTrades)} label="of shares had no trades in six months" />
      </KpiRow>

      <ModelStrip
        name="Days-to-exit measure + K-means tiers"
        facts={[
          `${data.meta.settings.lookbackDays} trading days per stock`,
          'block deals capped at 10× a normal day',
          'holds at 62–72% under every assumption tested',
        ]}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel>
          <PanelTitle
            title="Most shares take weeks or months to sell"
            subtitle={`Number of stocks by trading days to sell ${kes(position)}`}
          />
          <ColumnChart data={bandCounts} height={260} valueFormatter={(v) => v.toFixed(0)} showEvery={1} barLabels width={560} />
        </Panel>

        <Panel>
          <PanelTitle
            title="The market thinned for a decade"
            subtitle="Share of ordinary shares needing more than 20 trading days to sell KES 10m, each quarter"
          />
          <MultiLineChart
            dates={history.map((h) => h.as_of)}
            series={[
              {
                id: 'hard',
                label: 'Hard to sell (> 20 days)',
                color: '#1D4ED8',
                values: history.map((h) => h.pct_over_20d * 100),
              },
            ]}
            height={260}
            valueFormatter={(v) => `${v.toFixed(0)}%`}
          />
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-2">
            54% in 2013 → a peak of 92% in March 2024 → {pct(data.headline.depth.pct_over_20d)} now. The rally lifted
            prices far more than it deepened the market.
          </p>
        </Panel>
      </div>

      <Panel>
        <PanelTitle title={`All ${sorted.length} ordinary shares, easiest to sell first`} />
        <DataTable
          rows={sorted}
          maxHeight="460px"
          columns={[
            { key: 'name', header: 'Company', render: (r) => <span className="font-medium">{shortName(r.name)}</span> },
            { key: 'sector', header: 'Sector', render: (r) => r.sector ?? '—' },
            {
              key: 'tier',
              header: 'Tier',
              render: (r) => (
                <Pill
                  text={r.tier.replace(/^\d\s/, '')}
                  tone={r.tier.startsWith('1') ? 'good' : r.tier.startsWith('2') ? 'warn' : r.tier.startsWith('3') ? 'bad' : 'muted'}
                />
              ),
            },
            { key: 'days', header: `Days to sell ${kes(position)}`, align: 'right', render: (r) => fmtDays(r.days) },
            { key: 'adv', header: 'Trades a day', align: 'right', render: (r) => kes(r.adv_kes) },
            { key: 'zero', header: 'No-trade days', align: 'right', render: (r) => pct(r.zero_trade_share) },
            { key: 'fp', header: 'Foreign-owned', align: 'right', render: (r) => pct(r.foreign_pct) },
          ]}
          caption="Tiers: Deep ≤ 2 days · Moderate ≤ 20 · Thin ≤ 250 · Frozen > 250 days or no trades."
        />
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel>
          <PanelTitle
            title="Does the headline hold under other assumptions?"
            subtitle="Share needing more than 20 days, across lookback windows, position sizes and participation rates"
          />
          <DataTable
            rows={data.robustnessDepth.sensitivity.filter((s) => s.position_kes === position || s.position_kes === 10e6)}
            maxHeight="300px"
            columns={[
              { key: 'lb', header: 'Window', align: 'right', render: (r) => `${r.lookback_days} days` },
              { key: 'pos', header: 'Position', align: 'right', render: (r) => kes(r.position_kes) },
              { key: 'part', header: 'Sell per day', align: 'right', render: (r) => pct(r.participation) },
              { key: 'o20', header: '> 20 days', align: 'right', render: (r) => pct(r.pct_over_20d) },
              { key: 'o5', header: '> 5 days', align: 'right', render: (r) => pct(r.pct_over_5d) },
            ]}
          />
        </Panel>

        <Panel>
          <PanelTitle
            title="Block deals barely move the headline"
            subtitle="A one-off transfer like NCBA's KES 100bn on 3 Nov 2026 would otherwise make a stock look liquid"
          />
          <DataTable
            rows={data.robustnessDepth.blockCap}
            columns={[
              { key: 'cap', header: 'Block deals counted at most', render: (r) => r.block_cap },
              { key: 'o20', header: '> 20 days', align: 'right', render: (r) => pct(r.pct_over_20d) },
              { key: 't5', header: 'Top-5 share', align: 'right', render: (r) => pct(r.top5_share_of_value) },
            ]}
          />
          <div className="mt-3">
            <Note label="Reading">
              The depth finding is strong: it stays between 66% and 67% with caps from 5× to 50×, and 62% with no cap
              at all. The cap mostly changes the top-5 share, because one-off transfers inflate a few big stocks.
            </Note>
          </div>
        </Panel>
      </div>
    </div>
  );
};
