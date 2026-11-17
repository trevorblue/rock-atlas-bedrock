/**
 * ROCK ATLAS × Bedrock — the merged shell.
 *
 * The partner's original App.tsx is kept beside this file, unchanged, as the record of the MVP. This version
 * keeps every one of his eight workspaces and every feature in them, and adds:
 *   · real NSE data loaded into his own CSV parser, so his six TypeScript engines run on real prices
 *   · Bedrock's seven pages (Market Depth, Sell-off Alert, Crash Risk, Speculation Watch, Stress Test,
 *     Market-Ready, Guide)
 *   · a Bedrock block on each of his workspaces, so pages that do the same job carry both projects' work
 *   · a Demo group: exact clones of his eight workspaces on the synthetic corpus, plus Bedrock's four demo pages
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  BacktestConfig,
  DataClassification,
  KMRIWeights,
  OpportunityWeights,
  ParsedDataset,
  WorkspaceId,
} from './engines/types';
import { createSyntheticNseDataset, parseCsvDataset } from './engines/dataGovernance';
import { computeMarketIntelligence } from './engines/marketEngine';
import { computeFundamentalIntelligence } from './engines/fundamentalEngine';
import { computeRiskIntelligence } from './engines/riskEngine';
import { computeOpportunityRadar, DEFAULT_OPPORTUNITY_WEIGHTS } from './engines/opportunityEngine';
import { computeKMRI, DEFAULT_KMRI_WEIGHTS } from './engines/kmriEngine';
import { computePredictiveIntelligence } from './engines/predictiveEngine';
import { LIVE_DEMO_STEPS } from './engines/researchContent';
import { CommandCentre } from './components/workspaces/CommandCentre';
import { OpportunityRadar } from './components/workspaces/OpportunityRadar';
import { SecurityExplorer } from './components/workspaces/SecurityExplorer';
import { RiskLaboratory } from './components/workspaces/RiskLaboratory';
import { PredictiveWorkspace } from './components/workspaces/PredictiveWorkspace';
import { KMRIWorkspace } from './components/workspaces/KMRIWorkspace';
import { ResearchStudio } from './components/workspaces/ResearchStudio';
import { GovernanceWorkspace } from './components/workspaces/GovernanceWorkspace';
// --- Bedrock engine: real NSE data and its tested models ---------------------------------------------------
import { fetchRealPricesCsv, useBedrockData } from './bedrock/data';
import { MarketDepth } from './components/bedrock/MarketDepth';
import { SelloffAlert } from './components/bedrock/SelloffAlert';
import { CrashRisk } from './components/bedrock/CrashRisk';
import { SpeculationWatch } from './components/bedrock/SpeculationWatch';
import { StressTest } from './components/bedrock/StressTest';
import { MarketReady } from './components/bedrock/MarketReady';
import { BedrockGuide } from './components/bedrock/BedrockGuide';
import { LoadingPanel } from './components/bedrock/kit';
import {
  DepthRiskPanel,
  ExitCheckPanel,
  HeadlinePanel,
  PredictivePanel,
  ProvenancePanel,
  ResilienceTestPanel,
  StockSignalsPanel,
} from './components/bedrock/panels';
import { ForeignFlowsDemo, FundamentalsDemo, OpportunitiesDemo, SelloffDemo } from './components/bedrock/demos';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Compass,
  Database,
  Eye,
  FileText,
  FlaskConical,
  Gauge,
  Layers,
  Menu,
  Moon,
  Play,
  Rocket,
  ShieldAlert,
  ShieldCheck,
  Sun,
  TrendingDown,
  TrendingUp,
  Upload,
  X,
} from 'lucide-react';

/** Every page in the merged platform. */
type PageId =
  | WorkspaceId
  | 'bd-depth'
  | 'bd-selloff'
  | 'bd-crash'
  | 'bd-speculation'
  | 'bd-stress'
  | 'bd-ready'
  | 'bd-guide'
  | 'demo-command-centre'
  | 'demo-opportunity-radar'
  | 'demo-security-explorer'
  | 'demo-risk-laboratory'
  | 'demo-predictive-intelligence'
  | 'demo-kmri'
  | 'demo-research-studio'
  | 'demo-governance'
  | 'bd-demo-selloff'
  | 'bd-demo-opportunities'
  | 'bd-demo-fundamentals'
  | 'bd-demo-flows';

interface PageMeta {
  id: PageId;
  code: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  /** the partner's workspace this page renders, when it is one of his eight */
  workspace?: WorkspaceId;
  /** demo pages always run on the synthetic corpus, whatever the real pages are using */
  demo?: boolean;
}

interface NavGroup {
  title: string;
  hint: string;
  pages: PageMeta[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Real NSE data',
    hint: 'Powered by the Bedrock engine',
    pages: [
      { id: 'command-centre', code: '01.', label: 'Command Centre', icon: Activity, workspace: 'command-centre' },
      { id: 'opportunity-radar', code: '02.', label: 'Opportunity Radar', icon: Compass, workspace: 'opportunity-radar' },
      { id: 'security-explorer', code: '03.', label: 'Security Explorer', icon: BarChart3, workspace: 'security-explorer' },
      { id: 'risk-laboratory', code: '04.', label: 'Risk Laboratory', icon: ShieldAlert, workspace: 'risk-laboratory' },
      { id: 'predictive-intelligence', code: '05.', label: 'Predictive Models', icon: TrendingUp, workspace: 'predictive-intelligence' },
      { id: 'kmri', code: '06.', label: 'Resilience Index', icon: ShieldCheck, workspace: 'kmri' },
      { id: 'research-studio', code: '07.', label: 'Research Studio', icon: FileText, workspace: 'research-studio' },
      { id: 'governance', code: '08.', label: 'Data Governance', icon: Database, workspace: 'governance' },
      { id: 'bd-depth', code: '09.', label: 'Market Depth', icon: Layers },
      { id: 'bd-selloff', code: '10.', label: 'Sell-off Alert', icon: AlertTriangle },
      { id: 'bd-crash', code: '11.', label: 'Crash Risk', icon: TrendingDown },
      { id: 'bd-speculation', code: '12.', label: 'Speculation Watch', icon: Eye },
      { id: 'bd-stress', code: '13.', label: 'Stress Test', icon: Gauge },
      { id: 'bd-ready', code: '14.', label: 'Market-Ready', icon: Rocket },
      { id: 'bd-guide', code: '15.', label: 'Guide', icon: BookOpen },
    ],
  },
  {
    title: 'Demo',
    hint: 'Made-up data, kept separate',
    pages: [
      { id: 'demo-command-centre', code: 'D1.', label: 'Command Centre (demo)', icon: Activity, workspace: 'command-centre', demo: true },
      { id: 'demo-opportunity-radar', code: 'D2.', label: 'Opportunity Radar (demo)', icon: Compass, workspace: 'opportunity-radar', demo: true },
      { id: 'demo-security-explorer', code: 'D3.', label: 'Security Explorer (demo)', icon: BarChart3, workspace: 'security-explorer', demo: true },
      { id: 'demo-risk-laboratory', code: 'D4.', label: 'Risk Laboratory (demo)', icon: ShieldAlert, workspace: 'risk-laboratory', demo: true },
      { id: 'demo-predictive-intelligence', code: 'D5.', label: 'Predictive Models (demo)', icon: TrendingUp, workspace: 'predictive-intelligence', demo: true },
      { id: 'demo-kmri', code: 'D6.', label: 'Resilience Index (demo)', icon: ShieldCheck, workspace: 'kmri', demo: true },
      { id: 'demo-research-studio', code: 'D7.', label: 'Research Studio (demo)', icon: FileText, workspace: 'research-studio', demo: true },
      { id: 'demo-governance', code: 'D8.', label: 'Data Governance (demo)', icon: Database, workspace: 'governance', demo: true },
      { id: 'bd-demo-selloff', code: 'D9.', label: 'Sell-off Alert (demo)', icon: AlertTriangle, demo: true },
      { id: 'bd-demo-opportunities', code: 'D10.', label: 'Opportunities (demo)', icon: Compass, demo: true },
      { id: 'bd-demo-fundamentals', code: 'D11.', label: 'Fundamentals (demo)', icon: FlaskConical, demo: true },
      { id: 'bd-demo-flows', code: 'D12.', label: 'Foreign Flows by Stock (demo)', icon: TrendingDown, demo: true },
    ],
  },
];

const ALL_PAGES: PageMeta[] = NAV_GROUPS.flatMap((g) => g.pages);

export default function AppMerged() {
  const [darkMode, setDarkMode] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [activePage, setActivePage] = useState<PageId>('command-centre');

  // The synthetic corpus the MVP ships with. Unchanged, and now the data behind the demo group.
  const syntheticDataset = useMemo(() => createSyntheticNseDataset(), []);
  // What the real-data pages use: Bedrock's real NSE export, or whatever the analyst uploads.
  const [dataset, setDataset] = useState<ParsedDataset>(syntheticDataset);
  const [realDataLoaded, setRealDataLoaded] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedTicker, setSelectedTicker] = useState<string>('SCOM');

  const [radarWeights, setRadarWeights] = useState<OpportunityWeights>(DEFAULT_OPPORTUNITY_WEIGHTS);
  const [kmriWeights, setKmriWeights] = useState<KMRIWeights>(DEFAULT_KMRI_WEIGHTS);
  const [riskFreeRate, setRiskFreeRate] = useState<number>(0.145);
  const [backtestConfig, setBacktestConfig] = useState<BacktestConfig>({
    trainFraction: 0.6,
    rebalanceDays: 20,
    topK: 3,
    transactionCostBps: 180,
    riskFreeRate: 0.145,
  });

  const [demoStepIdx, setDemoStepIdx] = useState<number | null>(null);
  const quickFileInputRef = useRef<HTMLInputElement>(null);

  // Bedrock's model results: static JSON written by its Python pipeline.
  const bedrock = useBedrockData();

  const pageMeta = ALL_PAGES.find((p) => p.id === activePage) ?? ALL_PAGES[0];
  const isDemoPage = Boolean(pageMeta.demo);

  /** His six engines run on the synthetic corpus for demo pages, and on real data everywhere else. */
  const activeDataset = isDemoPage ? syntheticDataset : dataset;

  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) root.classList.add('dark');
    else root.classList.remove('dark');
  }, [darkMode]);

  useEffect(() => {
    setBacktestConfig((prev) => ({ ...prev, riskFreeRate }));
  }, [riskFreeRate]);

  // Load Bedrock's real NSE prices through Atlas's own parser, so all six engines run on real data unchanged.
  useEffect(() => {
    let cancelled = false;
    fetchRealPricesCsv()
      .then((csv) => {
        if (cancelled) return;
        const parsed = parseCsvDataset(
          csv,
          'NSE real prices (Bedrock export)',
          'Bedrock pipeline: Mendeley Data 2013-2026 + NSE daily price lists read by OCR',
          'VERIFIED DATA'
        );
        setDataset(parsed);
        setRealDataLoaded(true);
        const codes = new Set(parsed.securities.map((s) => s.ticker));
        setSelectedTicker(codes.has('SCOM') ? 'SCOM' : parsed.securities[0]?.ticker ?? 'SCOM');
      })
      .catch(() => {
        if (!cancelled) setRealDataLoaded(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Execute all six interconnected analytical engines deterministically
  const market = useMemo(() => computeMarketIntelligence(activeDataset), [activeDataset]);
  const fundamentals = useMemo(() => computeFundamentalIntelligence(activeDataset), [activeDataset]);
  const risk = useMemo(() => computeRiskIntelligence(activeDataset, riskFreeRate), [activeDataset, riskFreeRate]);
  const opportunities = useMemo(
    () => computeOpportunityRadar(market, fundamentals, risk.profiles, radarWeights),
    [market, fundamentals, risk.profiles, radarWeights]
  );
  const kmri = useMemo(
    () => computeKMRI(activeDataset, market, risk.profiles, kmriWeights),
    [activeDataset, market, risk.profiles, kmriWeights]
  );
  const backtest = useMemo(
    () => computePredictiveIntelligence(activeDataset, backtestConfig),
    [activeDataset, backtestConfig]
  );

  const handleUploadCsv = (
    csvText: string,
    fileName: string,
    sourceLabel = 'User-Uploaded CSV Dataset',
    classification: DataClassification = 'VERIFIED DATA'
  ) => {
    try {
      const parsed = parseCsvDataset(csvText, fileName, sourceLabel, classification);
      setDataset(parsed);
      setRealDataLoaded(true);
      setSelectedTicker(parsed.securities[0]?.ticker ?? '');
      setUploadError(null);
      setActivePage('governance');

      fetch('/api/datasets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: fileName,
          source: sourceLabel,
          classification,
          securityCount: parsed.metadata.securityCount,
          tradingDays: parsed.metadata.tradingDays,
          csvText,
        }),
      }).catch(() => {});
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : 'Unable to parse CSV file.');
      setActivePage('governance');
    }
  };

  const handleQuickCsvInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      handleUploadCsv(String(reader.result ?? ''), file.name);
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleSelectSecurity = (ticker: string) => {
    setSelectedTicker(ticker);
    setActivePage(isDemoPage ? 'demo-security-explorer' : 'security-explorer');
  };

  const handleStartLiveDemo = () => {
    setDemoStepIdx(0);
    setActivePage(LIVE_DEMO_STEPS[0].workspace);
  };

  const handleMoveDemoStep = (nextIdx: number) => {
    if (nextIdx < 0 || nextIdx >= LIVE_DEMO_STEPS.length) return;
    setDemoStepIdx(nextIdx);
    setActivePage(LIVE_DEMO_STEPS[nextIdx].workspace);
  };

  const isSynthetic = activeDataset.metadata.classification === 'SYNTHETIC DATA';

  /** The Bedrock block that belongs on each of his eight workspaces (real-data pages only). */
  const bedrockPanelFor = (workspace: WorkspaceId): React.ReactNode => {
    if (!bedrock.data) return null;
    const d = bedrock.data;
    switch (workspace) {
      case 'command-centre':
        return <HeadlinePanel data={d} />;
      case 'opportunity-radar':
        return <ExitCheckPanel data={d} />;
      case 'security-explorer':
        return <StockSignalsPanel data={d} ticker={selectedTicker} />;
      case 'risk-laboratory':
        return <DepthRiskPanel data={d} />;
      case 'predictive-intelligence':
        return <PredictivePanel data={d} />;
      case 'kmri':
        return <ResilienceTestPanel data={d} />;
      case 'governance':
        return <ProvenancePanel data={d} />;
      default:
        return null;
    }
  };

  const renderWorkspace = (workspace: WorkspaceId): React.ReactNode => {
    switch (workspace) {
      case 'command-centre':
        return (
          <CommandCentre
            metadata={activeDataset.metadata}
            validation={activeDataset.validation}
            market={market}
            opportunities={opportunities}
            onSelectSecurity={handleSelectSecurity}
            onNavigate={(w) => setActivePage(isDemoPage ? (`demo-${w}` as PageId) : w)}
          />
        );
      case 'opportunity-radar':
        return (
          <OpportunityRadar
            opportunities={opportunities}
            weights={radarWeights}
            onChangeWeights={setRadarWeights}
            onSelectSecurity={handleSelectSecurity}
          />
        );
      case 'security-explorer':
        return (
          <SecurityExplorer
            dataset={activeDataset}
            market={market}
            fundamentals={fundamentals}
            riskProfiles={risk.profiles}
            selectedTicker={selectedTicker}
            onSelectTicker={setSelectedTicker}
          />
        );
      case 'risk-laboratory':
        return (
          <RiskLaboratory
            dataset={activeDataset}
            profiles={risk.profiles}
            correlation={risk.correlation}
            riskFreeRate={riskFreeRate}
            onChangeRiskFreeRate={setRiskFreeRate}
          />
        );
      case 'predictive-intelligence':
        return <PredictiveWorkspace backtest={backtest} config={backtestConfig} onChangeConfig={setBacktestConfig} />;
      case 'kmri':
        return <KMRIWorkspace kmri={kmri} weights={kmriWeights} onChangeWeights={setKmriWeights} />;
      case 'research-studio':
        return (
          <ResearchStudio
            metadata={activeDataset.metadata}
            validation={activeDataset.validation}
            market={market}
            opportunities={opportunities}
            riskProfiles={risk.profiles}
            kmri={kmri}
            backtest={backtest}
          />
        );
      case 'governance':
        return (
          <GovernanceWorkspace
            dataset={activeDataset}
            metadata={activeDataset.metadata}
            validation={activeDataset.validation}
            onUploadCsv={handleUploadCsv}
            onResetSynthetic={() => {
              setDataset(syntheticDataset);
              setRealDataLoaded(false);
              setSelectedTicker('SCOM');
              setUploadError(null);
            }}
            uploadError={uploadError}
          />
        );
      default:
        return null;
    }
  };

  const renderBedrockPage = (node: (d: NonNullable<typeof bedrock.data>) => React.ReactNode): React.ReactNode =>
    bedrock.data ? node(bedrock.data) : <LoadingPanel error={bedrock.error} />;

  const renderPage = (): React.ReactNode => {
    if (pageMeta.workspace) {
      const panel = isDemoPage ? null : bedrockPanelFor(pageMeta.workspace);
      return (
        <div className="space-y-6">
          {pageMeta.workspace === 'command-centre' && panel}
          {renderWorkspace(pageMeta.workspace)}
          {pageMeta.workspace !== 'command-centre' && panel}
        </div>
      );
    }

    switch (activePage) {
      case 'bd-depth':
        return renderBedrockPage((d) => <MarketDepth data={d} />);
      case 'bd-selloff':
        return renderBedrockPage((d) => <SelloffAlert data={d} />);
      case 'bd-crash':
        return renderBedrockPage((d) => <CrashRisk data={d} />);
      case 'bd-speculation':
        return renderBedrockPage((d) => <SpeculationWatch data={d} />);
      case 'bd-stress':
        return renderBedrockPage((d) => <StressTest data={d} />);
      case 'bd-ready':
        return renderBedrockPage((d) => <MarketReady data={d} />);
      case 'bd-guide':
        return renderBedrockPage((d) => <BedrockGuide data={d} />);
      case 'bd-demo-selloff':
        return renderBedrockPage((d) => <SelloffDemo data={d} />);
      case 'bd-demo-opportunities':
        return renderBedrockPage((d) => <OpportunitiesDemo data={d} />);
      case 'bd-demo-fundamentals':
        return renderBedrockPage((d) => <FundamentalsDemo data={d} />);
      case 'bd-demo-flows':
        return renderBedrockPage((d) => <ForeignFlowsDemo data={d} />);
      default:
        return null;
    }
  };

  const navButton = (page: PageMeta, onPick: () => void) => {
    const Icon = page.icon;
    const active = activePage === page.id;
    return (
      <button
        key={page.id}
        onClick={onPick}
        className={`w-full flex items-center gap-2.5 px-3 py-2 text-left text-xs font-medium transition-colors whitespace-nowrap ${
          active
            ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900'
            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100'
        }`}
      >
        <Icon className="h-4 w-4 shrink-0" />
        <span className="font-mono text-[11px] opacity-75 w-8 shrink-0">{page.code}</span>
        <span className="truncate">{page.label}</span>
      </button>
    );
  };

  const navSections = (onPick: (id: PageId) => void) =>
    NAV_GROUPS.map((group) => (
      <div key={group.title} className="mb-4">
        <div className="px-3 pt-2 pb-1.5">
          <div className="text-[10px] font-mono font-bold tracking-widest text-slate-900 dark:text-slate-100 uppercase">
            {group.title}
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">{group.hint}</div>
        </div>
        <div className="space-y-0.5">{group.pages.map((p) => navButton(p, () => onPick(p.id)))}</div>
      </div>
    ));

  return (
    <div className="min-h-screen flex bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex lg:w-[272px] lg:shrink-0 lg:flex-col border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div className="px-6 py-5 border-b border-slate-200 dark:border-slate-800">
          <div className="font-display text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100">
            ROCK ATLAS
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">African Market Intelligence</div>
          <div className="text-[10px] font-mono text-slate-400 dark:text-slate-500 mt-1.5">
            Intelligence engine: Bedrock
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-3">{navSections((id) => setActivePage(id))}</nav>

        <div className="p-4 border-t border-slate-200 dark:border-slate-800 space-y-3 text-xs">
          <div className="text-slate-500 dark:text-slate-400">
            <div>Initial Market: Kenya (NSE)</div>
            <div className="mt-0.5">Research. Discover. Evaluate. Explain.</div>
          </div>
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="w-full flex items-center justify-between px-3 py-2 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <span>{darkMode ? 'Light Research Theme' : 'Dark Terminal Theme'}</span>
            {darkMode ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          </button>
        </div>
      </aside>

      {/* Mobile Navigation Drawer */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="fixed inset-0 bg-slate-950/50" onClick={() => setMobileNavOpen(false)} />
          <aside className="relative z-10 w-[272px] flex flex-col bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800">
            <div className="px-5 py-4 flex items-center justify-between border-b border-slate-200 dark:border-slate-800">
              <span className="font-display font-bold text-base">ROCK ATLAS</span>
              <button onClick={() => setMobileNavOpen(false)} aria-label="Close navigation" className="p-1 text-slate-500">
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto p-3">
              {navSections((id) => {
                setActivePage(id);
                setMobileNavOpen(false);
              })}
            </nav>
          </aside>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="h-14 px-6 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-between gap-8 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open navigation"
              className="lg:hidden p-1.5 text-slate-600 dark:text-slate-300"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-2 text-sm truncate">
              <span className="font-display font-semibold text-slate-500 dark:text-slate-400 whitespace-nowrap">
                ROCK ATLAS
              </span>
              <span className="text-slate-300 dark:text-slate-700">/</span>
              <h1 className="font-display font-semibold text-slate-900 dark:text-slate-100 truncate">
                {pageMeta.code} {pageMeta.label}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <input
              ref={quickFileInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={handleQuickCsvInput}
              className="hidden"
            />
            <button
              onClick={() => quickFileInputRef.current?.click()}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
            >
              <Upload className="h-3.5 w-3.5" />
              <span>Upload CSV</span>
            </button>
            <button
              onClick={handleStartLiveDemo}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 hover:bg-slate-800 dark:hover:bg-slate-200 transition-colors whitespace-nowrap shrink-0"
            >
              <Play className="h-3.5 w-3.5" />
              <span>Live Demo</span>
            </button>
          </div>
        </header>

        {/* Data Governance Classification Strip */}
        <div
          className={`px-6 py-2.5 border-b text-xs flex flex-wrap items-center justify-between gap-2 ${
            isSynthetic
              ? 'bg-amber-50/70 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/60 text-amber-950 dark:text-amber-200'
              : 'bg-teal-50/60 dark:bg-teal-950/20 border-teal-200 dark:border-teal-900/60 text-teal-950 dark:text-teal-200'
          }`}
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono font-semibold">{activeDataset.metadata.classification}</span>
            <span aria-hidden="true">·</span>
            <span>{activeDataset.metadata.name}</span>
            <span aria-hidden="true">·</span>
            <span className="font-mono tabular-nums">
              {activeDataset.metadata.startDate} to {activeDataset.metadata.endDate} (
              {activeDataset.metadata.securityCount} equities)
            </span>
          </div>
          <div className="text-[11px] opacity-90">
            {isSynthetic
              ? 'Demonstration corpus only — every figure on this page is invented.'
              : `Source: ${activeDataset.metadata.source}`}
          </div>
        </div>

        {!realDataLoaded && !isDemoPage && (
          <div className="px-6 py-2 border-b border-amber-200 dark:border-amber-900/60 bg-amber-50/60 dark:bg-amber-950/20 text-[11px] text-amber-900 dark:text-amber-200">
            Real NSE prices have not loaded. Run <span className="font-mono">python export_for_atlas.py</span> to build{' '}
            <span className="font-mono">public/data/nse_prices.csv</span>; until then these pages fall back to the
            demonstration corpus.
          </div>
        )}

        {/* Guided End-to-End Live Demonstration Strip */}
        {demoStepIdx !== null && (
          <div className="px-6 py-3 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-4">
            <div className="text-xs">
              <div className="font-semibold text-slate-900 dark:text-slate-100">
                Live Demonstration Step {LIVE_DEMO_STEPS[demoStepIdx].stepNumber} of {LIVE_DEMO_STEPS.length}:{' '}
                {LIVE_DEMO_STEPS[demoStepIdx].title}
              </div>
              <div className="text-slate-600 dark:text-slate-400 mt-0.5">
                {LIVE_DEMO_STEPS[demoStepIdx].objective} — {LIVE_DEMO_STEPS[demoStepIdx].actionSummary}
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => handleMoveDemoStep(demoStepIdx - 1)}
                disabled={demoStepIdx === 0}
                className="flex items-center gap-1 px-2.5 py-1 text-xs border border-slate-300 dark:border-slate-700 disabled:opacity-40 whitespace-nowrap"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                <span>Prev</span>
              </button>
              <button
                onClick={() => handleMoveDemoStep(demoStepIdx + 1)}
                disabled={demoStepIdx === LIVE_DEMO_STEPS.length - 1}
                className="flex items-center gap-1 px-2.5 py-1 text-xs bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 disabled:opacity-40 whitespace-nowrap"
              >
                <span>Next</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setDemoStepIdx(null)}
                className="px-2.5 py-1 text-xs text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
              >
                Exit Demo
              </button>
            </div>
          </div>
        )}

        {/* Main Workspace Viewport */}
        <main className="flex-1 p-6 max-w-[1440px] w-full mx-auto">{renderPage()}</main>

        <footer className="px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-[11px] text-slate-500 dark:text-slate-400 flex flex-wrap items-center justify-between gap-3">
          <span>
            ROCK ATLAS — African financial research and decision-support platform, powered by the Bedrock engine. Does
            not constitute personalized investment advice or a guarantee of future performance.
          </span>
          <span className="font-mono">Research. Discover. Evaluate. Explain.</span>
        </footer>
      </div>
    </div>
  );
}
