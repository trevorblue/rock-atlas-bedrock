import React from 'react';
import { BedrockData } from '../../bedrock/types';
import { DataTable, HowToRead, Kpi, KpiRow, PageHead, Panel, PanelTitle, Pill } from './kit';

interface Upgrade {
  upgrade: string;
  improves: string;
  why: string;
  priority: { text: string; tone: 'bad' | 'warn' | 'muted' };
}

const DATA_UPGRADES: Upgrade[] = [
  {
    upgrade: 'Daily foreign buying and selling for each stock',
    improves: 'Sell-off alert, crash risk, stress test',
    why: 'Shows who is selling which stock, every day. The alert becomes per-stock and daily, with about 20 times more data points, and the stress test can use real foreign positions instead of a single ownership snapshot.',
    priority: { text: 'Most needed', tone: 'bad' },
  },
  {
    upgrade: 'Weekly market-wide foreign flows',
    improves: 'Sell-off alert',
    why: 'About 600 data points instead of 140, so earlier warnings, and enough data for the economic inputs (exchange rate, interest rates, oil) to start helping rather than adding noise.',
    priority: { text: 'High', tone: 'warn' },
  },
  {
    upgrade: 'Company financials (earnings, dividends, balance sheets)',
    improves: 'Opportunity radar, Security Explorer, Fundamentals',
    why: "Adds value and quality to the score, so it rates the business and not only the share price. Today's fundamentals pages run on clearly labelled demo data for exactly this reason.",
    priority: { text: 'High', tone: 'warn' },
  },
  {
    upgrade: 'Bid-ask spreads, order book, block-trade flags',
    improves: 'Market depth, stress test',
    why: 'Measures the true cost of selling, and separates one-off negotiated deals from everyday trading instead of capping them with a rule of thumb.',
    priority: { text: 'Medium', tone: 'muted' },
  },
  {
    upgrade: 'Dividends and corporate actions (adjusted prices)',
    improves: 'Crash risk, speculation watch',
    why: 'Removes false "crashes" on dividend days and false "jumps" on share splits.',
    priority: { text: 'Medium', tone: 'muted' },
  },
  {
    upgrade: 'Verified daily prices from Rock',
    improves: 'Every page',
    why: 'Replaces our own reading of scanned NSE price lists (99% of volumes and 96% of closes match) with the source data.',
    priority: { text: 'Medium', tone: 'muted' },
  },
];

const MODEL_UPGRADES: Array<{ upgrade: string; adds: string; improves: string }> = [
  {
    upgrade: 'Volatility forecasting (GARCH family)',
    adds: 'First version built and already running as a challenger on the Crash Risk page: the best crash ranking of six methods, though not yet proven. Next: versions designed for thin trading, and daily data.',
    improves: 'Crash risk, stress test',
  },
  {
    upgrade: 'Regime-switching models (Markov)',
    adds: 'Detects when the market has moved into an "exit wave", the periods where most past sell-offs clustered (2020, 2022), instead of treating every month alike.',
    improves: 'Sell-off alert',
  },
  {
    upgrade: 'Self-exciting selling models (Hawkes)',
    adds: 'Captures how one heavy selling day raises the chance of the next, which is exactly how foreign exits behave. Needs daily flows.',
    improves: 'Sell-off alert',
  },
  {
    upgrade: 'Tail-risk models (extreme value theory)',
    adds: 'Estimates how big a rare crash could be, not only how likely it is.',
    improves: 'Crash risk, stress test',
  },
  {
    upgrade: 'Probability calibration',
    adds: 'Makes a reading of 53% mean a real 53% chance, so scores can be quoted as probabilities in client reports.',
    improves: 'Crash risk, sell-off alert',
  },
  {
    upgrade: 'Model monitoring and governance',
    adds: 'Live tracking of hit rates, alerts when data or accuracy drifts, versioned and documented models, and new models tested against the current one before they replace it.',
    improves: 'Every model',
  },
];

const PRODUCT: Array<[string, string]> = [
  ['Daily automatic refresh', 'New data in every morning, with no manual run'],
  ['Alerts', 'Email or SMS when the sell-off alert turns HIGH RISK, or when a holding fails the exit check'],
  ['Watch-lists and saved stock reports', 'Each client follows their own stocks'],
  ['An API for Rock\'s research team', "Pull the numbers straight into Rock's weekly research notes"],
];

export const MarketReady: React.FC<{ data: BedrockData }> = ({ data }) => (
  <div className="space-y-6">
    <PageHead
      eyebrow="Market-ready roadmap"
      question="What would make this platform better, and ready for real clients?"
      title="Six data upgrades would take it from prototype to a weekly tool for Rock's clients"
      subtitle="Most of the gain is in data, and much of that data is exactly what Rock Data Plus is built to provide. Compute is not the constraint: the whole engine reruns on a laptop in a few minutes."
    />

    <HowToRead
      purpose="The plan for turning a competition prototype into something Rock's research desk and clients would use every week."
      points={[
        'Priority shows what to add first. "Most needed" is daily foreign buying and selling for each stock.',
        'Each row says which models get better and why, so the value of the data is concrete.',
        'The model roadmap is what makes the predictions production-grade, not just the data.',
      ]}
    />

    <KpiRow>
      <Kpi value="#1 need" label="daily foreign buying and selling for each stock: it improves the most models at once" alert />
      <Kpi value="About 20×" label="more data points for the sell-off alert with daily instead of monthly flows" />
      <Kpi value={String(data.pricesMeta.stocks)} label="real NSE stocks already flowing through every engine" />
      <Kpi value="Minutes" label="to rerun the entire engine when new data arrives" />
    </KpiRow>

    <Panel>
      <PanelTitle title="Data upgrades, in order of payoff" subtitle="What each one unlocks, and why the models get better" />
      <DataTable
        rows={DATA_UPGRADES}
        columns={[
          { key: 'u', header: 'Upgrade', width: '24%', render: (r) => <span className="font-semibold">{r.upgrade}</span> },
          { key: 'i', header: 'Makes better', width: '18%', render: (r) => r.improves },
          { key: 'w', header: 'Why the models get better', render: (r) => r.why },
          { key: 'p', header: 'Priority', width: '11%', render: (r) => <Pill text={r.priority.text} tone={r.priority.tone} /> },
        ]}
      />
    </Panel>

    <Panel>
      <PanelTitle
        title="What makes the models production-grade"
        subtitle="Financial data moves through time and has fat tails, so the next generation adds dedicated time-series and stochastic methods on top of today's tested machine learning. Each will be tested the same honest way: trained only on the past, compared with a simple rule, and reported in full."
      />
      <DataTable
        rows={MODEL_UPGRADES}
        columns={[
          { key: 'u', header: 'Upgrade', width: '26%', render: (r) => <span className="font-semibold">{r.upgrade}</span> },
          { key: 'a', header: 'What it adds', render: (r) => r.adds },
          { key: 'i', header: 'Improves', width: '18%', render: (r) => r.improves },
        ]}
      />
    </Panel>

    <Panel>
      <PanelTitle title="What makes it user-ready" />
      <DataTable
        rows={PRODUCT.map(([a, b]) => ({ a, b }))}
        columns={[
          { key: 'a', header: 'Feature', width: '30%', render: (r) => <span className="font-semibold">{r.a}</span> },
          { key: 'b', header: 'What it means', render: (r) => r.b },
        ]}
      />
    </Panel>
  </div>
);
