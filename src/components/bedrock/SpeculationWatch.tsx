import React, { useMemo, useState } from 'react';
import { BedrockData } from '../../bedrock/types';
import { kes, niceDate, num, shortName, signedPct } from '../../bedrock/data';
import { DataTable, DotIntervalChart, HowToRead, Kpi, KpiRow, ModelStrip, Note, PageHead, Panel, PanelTitle, Pill } from './kit';

const WINDOWS = [30, 90, 180, 365];

export const SpeculationWatch: React.FC<{ data: BedrockData }> = ({ data }) => {
  const [window, setWindow] = useState(90);
  const { recentFlags, bootstrap, newsChecked, noNews, totalFlags } = data.speculation;

  const latest = recentFlags.length ? recentFlags[0].date : data.headline.depth.as_of;
  const cutoff = useMemo(() => {
    const d = new Date(`${latest}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() - window);
    return d.toISOString().slice(0, 10);
  }, [latest, window]);

  const shown = recentFlags.filter((f) => f.date >= cutoff);
  const stocks = new Set(shown.map((f) => f.code)).size;

  const small5 = bootstrap.find((b) => b.size === 'small' && b.horizon === 'fwd_5d');
  const large20 = bootstrap.find((b) => b.size === 'large' && b.horizon === 'fwd_20d');

  const label = (b: typeof bootstrap[number]) =>
    `${b.size === 'small' ? 'Small' : 'Large'} companies, next ${b.horizon.replace(/\D/g, '')} days`;

  return (
    <div className="space-y-6">
      <PageHead
        eyebrow="Speculation watch · Bedrock engine"
        question="Which price jumps have no news behind them, and might be speculation?"
        title={`${shown.length} unusual price jumps in the last ${window} days, across ${stocks} stocks`}
        subtitle={`Price and trading both broke sharply from the stock's own previous 60 days while the market as a whole stayed calm. Each one is a lead to check, not proof. ${totalFlags.toLocaleString(
          'en-US'
        )} flags since 2013.`}
      />

      <HowToRead
        purpose="Leads for analysts and regulators: unusual price jumps worth checking against company announcements and the press."
        points={[
          'A flag means price and volume both broke from the stock\'s own normal while the market did not move with it.',
          '"No news found" makes a flag a candidate for speculation or an undisclosed block deal, not a verdict.',
          'The chart below asks whether flagged jumps behave differently afterwards from ordinary big up-days.',
        ]}
      />

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500 dark:text-slate-400 mr-1">Window:</span>
        {WINDOWS.map((w) => (
          <button
            key={w}
            onClick={() => setWindow(w)}
            className={`px-3 py-1.5 text-xs font-medium border transition-colors ${
              w === window
                ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 border-slate-900 dark:border-slate-100'
                : 'border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
            }`}
          >
            Last {w} days
          </button>
        ))}
      </div>

      <KpiRow>
        <Kpi value={String(shown.length)} label={`flags across ${stocks} stocks in the window`} />
        <Kpi value={`${noNews} of ${newsChecked}`} label="checked flags that had no news behind them" alert />
        <Kpi value={small5 ? signedPct(small5.gap) : '—'} label="extra gain for small caps in the week after a flag" />
        <Kpi value={large20 ? signedPct(large20.gap) : '—'} label="large caps give back over the next month" />
      </KpiRow>

      <ModelStrip
        name="Isolation Forest anomaly detector"
        facts={[
          'each stock against its own previous 60 days',
          'market-wide moves removed',
          'top flags checked by hand against NSE announcements and the press',
        ]}
      />

      <div className="grid gap-6 lg:grid-cols-5">
        <Panel className="lg:col-span-3">
          <PanelTitle title="Flagged stock-days" subtitle="Newest first. 'News found?' is a hand check." />
          <DataTable
            rows={shown}
            maxHeight="420px"
            columns={[
              { key: 'date', header: 'Date', render: (r) => niceDate(r.date) },
              { key: 'name', header: 'Company', render: (r) => <span className="font-medium">{shortName(r.name)}</span> },
              { key: 'ret', header: "Day's move", align: 'right', render: (r) => signedPct(r.ret) },
              { key: 'val', header: 'Traded', align: 'right', render: (r) => kes(r.value_kes) },
              {
                key: 'news',
                header: 'News found?',
                render: (r) =>
                  !r.news ? (
                    <Pill text="not checked yet" tone="muted" />
                  ) : r.news.startsWith('yes') ? (
                    <span className="text-slate-600 dark:text-slate-300">{r.news.replace(/^yes:\s*/, '')}</span>
                  ) : (
                    <Pill text="no news found" tone="bad" />
                  ),
              },
            ]}
          />
        </Panel>

        <Panel className="lg:col-span-2">
          <PanelTitle
            title="After a flag, small stocks keep rising"
            subtitle="Extra return compared with other days a stock rose more than 5%, with the 95% range. 2013–2026."
          />
          <DotIntervalChart
            data={bootstrap.map((b) => ({
              label: label(b),
              value: b.gap,
              low: b.ci_low,
              high: b.ci_high,
              certain: b.ci_excludes_zero,
              display: signedPct(b.gap),
            }))}
          />
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 leading-relaxed">
            Small caps keep running for about a week, which fits pump-style trading in thin stocks. Large caps partly
            reverse over the next month. Grey means the range crosses zero, so it could be chance.
          </p>
        </Panel>
      </div>

      <Panel>
        <PanelTitle title="Worked examples" subtitle="What the hand checks found" />
        <div className="grid gap-4 md:grid-cols-3 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
          <div>
            <div className="font-semibold text-slate-900 dark:text-slate-100 mb-1">
              TransCentury, Jan–Feb 2025 — no news
            </div>
            TCL normally traded about KES 64,000 a day. From 20 January it rose on 12 of the next 13 trading days, from
            KES 0.50 to 1.65 (+230%), on 10–100 times its usual value traded, then fell 39% in five days. We found no
            announcement or press coverage behind the run. Bedrock flagged it on the second day.
          </div>
          <div>
            <div className="font-semibold text-slate-900 dark:text-slate-100 mb-1">
              Car &amp; General, 2026 — news, with speculation on top
            </div>
            Flagged in April (results, dividend quadrupled) and in August (half-year profit up fourfold); the stock
            rose a further 54% in the five days after the August flag. Business Daily later described C&amp;G's
            tenfold rise as speculator-driven.
          </div>
          <div>
            <div className="font-semibold text-slate-900 dark:text-slate-100 mb-1">
              EABL, 18 Dec 2025 — the contrast
            </div>
            Rose 19% on the Asahi deal, then gave back 18% within a month: the large-cap reversal pattern, correctly
            marked as news rather than speculation.
          </div>
        </div>
        <div className="mt-4">
          <Note>
            the detector finds real events — {newsChecked - noNews} of {newsChecked} checked flags had a clear
            explanation — so the {noNews} without news are the ones worth a closer look. The largest no-news days look
            like negotiated block deals, so a flag is a lead, not proof.
          </Note>
        </div>
      </Panel>
    </div>
  );
};
