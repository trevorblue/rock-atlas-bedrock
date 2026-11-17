import React, { useMemo, useState } from 'react';
import { BedrockData } from '../../bedrock/types';
import { days as fmtDays, kes, pct, shortName, signedPct } from '../../bedrock/data';
import { runScenario, summarize } from '../../bedrock/stressModel';
import { DataTable, HBarChart, HowToRead, Kpi, KpiRow, ModelStrip, Note, PageHead, Panel, PanelTitle, Pill } from './kit';

const STATUS_TONE: Record<string, 'good' | 'warn' | 'bad' | 'muted'> = {
  absorbed: 'good',
  strained: 'warn',
  trapped: 'bad',
  'no market': 'bad',
  'not hit': 'muted',
};

export const StressTest: React.FC<{ data: BedrockData }> = ({ data }) => {
  const [amountBn, setAmountBn] = useState(data.headline.stress_default.total_sell_kes / 1e9);
  const [days, setDays] = useState(5);
  const [participation, setParticipation] = useState(data.meta.settings.participation);
  const [cutoff, setCutoff] = useState(data.meta.settings.strategicCutoff);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { rows, summary } = useMemo(() => {
    const r = runScenario(data.depth, {
      totalSellKes: amountBn * 1e9,
      days,
      participation,
      maxForeignPct: cutoff,
    });
    return { rows: r, summary: summarize(r, amountBn * 1e9) };
  }, [data.depth, amountBn, days, participation, cutoff]);

  const hardest = rows.filter((r) => r.sellKes > 0 && r.priceImpact !== null).slice(0, 15);
  const equityTrapped = rows.some((r) => r.code === 'EQTY' && r.status === 'trapped');

  return (
    <div className="space-y-6">
      <PageHead
        eyebrow="Stress test · Bedrock engine"
        question="If foreign investors sell a large amount quickly, which stocks break?"
        title={`Selling ${kes(amountBn * 1e9)} in ${days} trading days would trap ${summary.nTrapped} stocks${
          equityTrapped ? ', even Equity Group' : ''
        }`}
        subtitle="Trapped means a stock needs more than four times the selling window to absorb its share, or has no buyers at all. Move the sliders to try other scenarios: the model runs live."
      />

      <HowToRead
        purpose="A 'what if' for risk managers and Rock's research desk: what a foreign exit would do to each stock, not just to the index."
        points={[
          'The sale is split across stocks by how much of each one foreigners own (CMA ownership data).',
          `Stakes above ${pct(cutoff)} are treated as a foreign parent's strategic holding and are not sold.`,
          'Absorbed = clears inside the window · strained = up to 4× longer · trapped = longer still, or no market.',
        ]}
      />

      <Panel>
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          <div>
            <label className="text-xs font-medium text-slate-700 dark:text-slate-300 flex justify-between">
              <span>Foreign selling</span>
              <span className="font-mono tabular-nums text-slate-900 dark:text-slate-100">{kes(amountBn * 1e9)}</span>
            </label>
            <input
              type="range"
              min={0.5}
              max={10}
              step={0.5}
              value={amountBn}
              onChange={(e) => setAmountBn(Number(e.target.value))}
              className="w-full mt-2 accent-slate-900 dark:accent-slate-100"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-700 dark:text-slate-300 flex justify-between">
              <span>Over how many trading days</span>
              <span className="font-mono tabular-nums text-slate-900 dark:text-slate-100">{days}</span>
            </label>
            <input
              type="range"
              min={1}
              max={20}
              step={1}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-full mt-2 accent-slate-900 dark:accent-slate-100"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={() => setShowAdvanced((v) => !v)}
              className="px-3 py-1.5 text-xs font-medium border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              {showAdvanced ? 'Hide' : 'Show'} advanced assumptions
            </button>
          </div>
        </div>

        {showAdvanced && (
          <div className="grid gap-5 md:grid-cols-2 mt-5 pt-5 border-t border-slate-200 dark:border-slate-800">
            <div>
              <label className="text-xs font-medium text-slate-700 dark:text-slate-300 flex justify-between">
                <span>Most you can sell in a day, as a share of normal trading</span>
                <span className="font-mono tabular-nums">{pct(participation)}</span>
              </label>
              <input
                type="range"
                min={0.05}
                max={0.5}
                step={0.05}
                value={participation}
                onChange={(e) => setParticipation(Number(e.target.value))}
                className="w-full mt-2 accent-slate-900 dark:accent-slate-100"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-700 dark:text-slate-300 flex justify-between">
                <span>Foreign stakes above this are strategic and not sold</span>
                <span className="font-mono tabular-nums">{pct(cutoff)}</span>
              </label>
              <input
                type="range"
                min={0.3}
                max={1}
                step={0.05}
                value={cutoff}
                onChange={(e) => setCutoff(Number(e.target.value))}
                className="w-full mt-2 accent-slate-900 dark:accent-slate-100"
              />
            </div>
          </div>
        )}
      </Panel>

      <KpiRow>
        <Kpi value={String(summary.nHit)} label="stocks hit by the selling" />
        <Kpi value={String(summary.nTrapped)} label="trapped: cannot be sold in time" alert />
        <Kpi value={kes(summary.valueTrappedKes)} label="of selling stuck in trapped stocks" />
        <Kpi value={signedPct(summary.weightedImpact)} label="average price fall weighted by size: the index looks calm" />
      </KpiRow>

      <ModelStrip
        name="Square-root market-impact model"
        facts={[
          'selling split by foreign ownership (CMA, Aug 2026)',
          `stakes above ${pct(cutoff)} treated as strategic`,
          'runs live in the browser, identical to the Python model',
        ]}
      />

      <Panel>
        <PanelTitle
          title="The 15 hardest-hit stocks"
          subtitle="Estimated price fall from the selling. Bigger sales in thinner stocks move the price more."
        />
        <HBarChart
          data={hardest.map((r) => ({
            label: shortName(r.name),
            value: Math.abs(r.priceImpact ?? 0),
            display: signedPct(r.priceImpact ?? 0, 0),
            tone: STATUS_TONE[r.status] === 'good' ? 'good' : STATUS_TONE[r.status] === 'warn' ? 'warn' : 'bad',
            hint: `${shortName(r.name)}: price ${signedPct(r.priceImpact ?? 0)}, ${r.status}, about ${fmtDays(
              r.daysToAbsorb
            )} to clear its ${kes(r.sellKes)} share`,
          }))}
          labelWidth={220}
        />
        <div className="flex flex-wrap items-center gap-4 mt-3 text-[11px] text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 bg-teal-700" /> absorbed
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 bg-amber-600" /> strained
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 bg-red-600" /> trapped
          </span>
        </div>
      </Panel>

      <Panel>
        <PanelTitle title="Every stock in this scenario" />
        <DataTable
          rows={rows.filter((r) => r.sellKes > 0)}
          maxHeight="420px"
          columns={[
            { key: 'name', header: 'Company', render: (r) => <span className="font-medium">{shortName(r.name)}</span> },
            { key: 'status', header: 'Status', render: (r) => <Pill text={r.status} tone={STATUS_TONE[r.status]} /> },
            { key: 'fp', header: 'Foreign-owned', align: 'right', render: (r) => pct(r.foreignPct) },
            { key: 'sell', header: 'Its share of the sale', align: 'right', render: (r) => kes(r.sellKes) },
            { key: 'days', header: 'Days to clear', align: 'right', render: (r) => fmtDays(r.daysToAbsorb) },
            { key: 'imp', header: 'Price impact', align: 'right', render: (r) => (r.priceImpact === null ? '—' : signedPct(r.priceImpact)) },
          ]}
        />
      </Panel>

      <Note label="Reading">
        this is a scenario, not a forecast. It assumes today's liquidity holds while the selling happens; in a real
        sell-off liquidity falls, so these figures are optimistic. The point is the pattern: the index barely moves
        ({signedPct(summary.weightedImpact)}) while many smaller stocks become unsellable.
      </Note>
    </div>
  );
};
