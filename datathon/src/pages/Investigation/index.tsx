import React, { useEffect, useState } from 'react';
import { Search, ArrowLeft, Layers, Activity, Users, Shield, Briefcase, FileText, Brain } from 'lucide-react';
import { getInvestigation, getCrimeCases, searchInvestigation } from '../../services/api';
import type {
  InvestigationData,
  CrimeCaseDetailRecord,
  InvestigationGroupedSearchResponse,
  InvestigationSearchItem,
} from '../../services/api';
import InvestigationDashboard from '../../components/investigation/InvestigationDashboard';
import CaseProgress from '../../components/investigation/CaseProgress';
import InvestigationTimeline from '../../components/investigation/InvestigationTimeline';
import LinkedFIRs from '../../components/investigation/LinkedFIRs';
import LinkedCriminals from '../../components/investigation/LinkedCriminals';
import LinkedEvidence from '../../components/investigation/LinkedEvidence';
import AIRecommendations from '../../components/investigation/AIRecommendations';
import AIChatPanel from '../../components/investigation/AIChatPanel';
import { MOPatternExplorer } from '../../components/investigation/MOPatternExplorer';
import { CardSkeleton } from '../../components/ui/Skeleton';

type ViewState = 'list' | 'detail';

const SEARCH_GROUPS: { key: keyof Pick<InvestigationGroupedSearchResponse, 'persons' | 'victims' | 'cases' | 'firs' | 'mo_matches'>; label: string; icon: React.ReactNode; tone: string }[] = [
  { key: 'persons', label: 'Criminals / Suspects', icon: <Users className="w-3.5 h-3.5" />, tone: '#1E6FD9' },
  { key: 'victims', label: 'Victims / Witnesses', icon: <Shield className="w-3.5 h-3.5" />, tone: '#22c55e' },
  { key: 'cases', label: 'Cases', icon: <Briefcase className="w-3.5 h-3.5" />, tone: '#7c5cff' },
  { key: 'firs', label: 'FIRs', icon: <FileText className="w-3.5 h-3.5" />, tone: '#14b8a6' },
  { key: 'mo_matches', label: 'MO Matches', icon: <Brain className="w-3.5 h-3.5" />, tone: '#a855f7' },
];

const navigateTo = (tab: string, targetId?: string) => {
  window.dispatchEvent(new CustomEvent('navigate-tab', { detail: { tab, targetId } }));
};

const isUuidish = (v?: string | null): v is string =>
  !!v && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v);

const InvestigationPage: React.FC = () => {
  const [viewState, setViewState] = useState<ViewState>('list');
  const [cases, setCases] = useState<CrimeCaseDetailRecord[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [investigationData, setInvestigationData] = useState<InvestigationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [fedResults, setFedResults] = useState<InvestigationGroupedSearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Check if returning from Criminals / other tab with a target case ID
  useEffect(() => {
    const redirectId = sessionStorage.getItem('selected_entity_id') || sessionStorage.getItem('return_to_case_id');
    if (redirectId) {
      sessionStorage.removeItem('selected_entity_id');
      loadInvestigation(redirectId);
    }
  }, []);

  // Fetch case list on mount
  const loadCases = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCrimeCases(searchQuery || undefined, statusFilter || undefined, 1, 50);
      setCases(response.results || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load cases');
    } finally {
      setLoading(false);
    }
  };

  // Debounce search so we don't fire a query (and hammer the DB pool) per keystroke.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const term = searchQuery.trim();
      if (term) {
        setSearching(true);
        setFedResults(null);
        setSearchError(null);
        searchInvestigation(term, 15)
          .then((res) => setFedResults(res))
          .catch((err: any) => setSearchError(err?.message || 'Failed to search records'))
          .finally(() => setSearching(false));
      } else {
        setFedResults(null);
        loadCases();
      }
    }, 400);
    return () => window.clearTimeout(timer);
  }, [searchQuery, statusFilter]);

  // Fetch investigation detail
  const loadInvestigation = async (caseId: string) => {
    setLoadingDetail(true);
    setError(null);
    try {
      const data = await getInvestigation(caseId);
      setInvestigationData(data);
      setSelectedCaseId(caseId);
      setViewState('detail');
    } catch (err: any) {
      setError(err?.message || 'Failed to load investigation data');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleBack = () => {
    setViewState('list');
    setInvestigationData(null);
    setSelectedCaseId(null);
  };

  const openFederatedItem = (item: InvestigationSearchItem) => {
    if (item.type === 'case') {
      const caseId = item.meta?.case_id || item.id.replace('case-', '');
      if (isUuidish(caseId)) loadInvestigation(caseId);
    } else if (item.type === 'fir') {
      const caseId = item.meta?.case_id;
      if (isUuidish(caseId)) loadInvestigation(caseId);
      else navigateTo('fir');
    } else if (item.type === 'person') {
      const id = item.meta?.criminal_id || item.id.replace('criminal-', '');
      navigateTo('criminals', id);
    } else if (item.type === 'victim') {
      const id = item.meta?.victim_id || item.id.replace('victim-', '');
      navigateTo('victims', id);
    } else if (item.type === 'mo') {
      const docId = String(item.meta?.doc_id || item.id || '').replace(/^(criminal|crime_case|fir)-/, '');
      if (item.status === 'criminal') navigateTo('criminals', docId);
      else if (item.status === 'crime_case' && isUuidish(docId)) loadInvestigation(docId);
      else if (item.status === 'fir') navigateTo('fir');
    }
  };

  const renderFederatedResults = () => {
    if (searching) {
      return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      );
    }
    if (searchError) {
      return (
        <div className="p-10 text-center text-[10px] text-amber-400 uppercase border border-dashed border-amber-500/30 rounded-lg">
          {searchError}
        </div>
      );
    }
    if (!fedResults || fedResults.total === 0) {
      return (
        <div className="p-12 text-center text-[10px] text-[var(--text-muted)] uppercase border border-dashed border-[var(--border-primary)] rounded-lg">
          No records found for &ldquo;{searchQuery.trim()}&rdquo;
          <div className="mt-1 text-[9px] normal-case">Try a person/victim name, FIR, case number or MO description.</div>
        </div>
      );
    }
    return (
      <div className="space-y-3">
        {!fedResults.mo_intelligence && (
          <div className="px-3 py-2 rounded border border-amber-500/30 bg-amber-500/5 text-[9px] font-mono text-amber-300">
            MO semantic matches are filtered for your clearance level.
          </div>
        )}
        {SEARCH_GROUPS.map((group) => {
          const items = fedResults[group.key];
          if (!items || items.length === 0) return null;
          return (
            <div key={group.key} className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 overflow-hidden">
              <div className="flex items-center gap-2 px-3 py-1.5 border-b border-[var(--border-primary)]">
                <span style={{ color: group.tone }}>{group.icon}</span>
                <span className="text-[8.5px] font-mono font-bold uppercase tracking-wider text-[var(--text-primary)]">{group.label}</span>
                <span className="ml-auto text-[8px] font-mono text-[var(--text-muted)]">{items.length}</span>
              </div>
              <div className="divide-y divide-[var(--border-primary)]/50">
                {items.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => openFederatedItem(item)}
                    className="w-full text-left px-3 py-2 hover:bg-[var(--bg-elevated)]/40 transition-colors cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-semibold text-[var(--text-primary)] truncate">{item.name}</span>
                      {item.status && (
                        <span className="px-1.5 py-0.5 rounded text-[7px] font-mono uppercase bg-[var(--bg-elevated)] border border-[var(--border-primary)] text-[var(--text-muted)] shrink-0">
                          {item.status.replace(/_/g, ' ')}
                        </span>
                      )}
                    </div>
                    {item.subtitle && <div className="text-[8.5px] font-mono text-[var(--text-muted)] truncate">{item.subtitle}</div>}
                    {item.detail && <div className="text-[9px] text-[var(--text-secondary)] line-clamp-1">{item.detail}</div>}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // ── List View ──
  if (viewState === 'list') {
    return (
      <div className="h-[84vh] flex flex-col gap-4 p-1 md:p-3 select-none">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-[var(--border-muted)] pb-3 shrink-0">
          <div>
            <h2 className="text-md font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-5 h-5 text-[#1E6FD9]" />
              Unified Investigation Interface
            </h2>
            <p className="text-[9.5px] font-mono text-[var(--text-muted)] mt-0.5">
              KARNATAKA POLICE — INVESTIGATION DASHBOARD, TIMELINE, FIRs, CRIMINALS, EVIDENCE & AI ANALYSIS
            </p>
            {error && <p className="text-[9px] font-mono text-amber-400 uppercase mt-1">{error}</p>}
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-3 shrink-0 text-[10px] font-mono">
          <div className="flex items-center relative flex-1 max-w-md">
            <input
              type="text"
              placeholder="Search by person, victim, FIR, case number, MO keywords…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-[var(--bg-secondary)]/70 border border-[var(--border-primary)] rounded text-[var(--text-primary)] outline-none focus:border-[#1E6FD9] text-[10.5px]"
            />
            <Search className="absolute left-2.5 w-3.5 h-3.5 text-[var(--text-muted)]" />
          </div>
          {!searchQuery.trim() && (
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded text-[var(--text-secondary)] outline-none focus:border-[#1E6FD9] cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="open">OPEN</option>
              <option value="assigned">ASSIGNED</option>
              <option value="investigating">INVESTIGATING</option>
              <option value="evidence collected">EVIDENCE COLLECTED</option>
              <option value="charge sheet filed">CHARGE SHEET FILED</option>
              <option value="closed">CLOSED</option>
            </select>
          )}
        </div>

        {/* Case List */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {searchQuery.trim() ? (
            renderFederatedResults()
          ) : loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <CardSkeleton key={i} />
              ))}
            </div>
          ) : cases.length === 0 ? (
            <div className="p-12 text-center text-[10px] text-[var(--text-muted)] uppercase border border-dashed border-[var(--border-primary)] rounded-lg">
              No cases matching your filters
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {cases.map((caseItem) => {
                const isOpening = loadingDetail && selectedCaseId === caseItem.id;
                return (
                  <button
                    key={caseItem.id}
                    onClick={() => loadInvestigation(caseItem.id)}
                    disabled={loadingDetail}
                    className={`p-4 bg-secondary-bg border border-border-color rounded-card text-left transition-all cursor-pointer group ${
                      isOpening
                        ? 'border-[#1E6FD9]/60 shadow-glow-blue/10'
                        : 'hover:border-[#1E6FD9]/30 hover:bg-[#1E6FD9]/5'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-[11px] font-bold text-[var(--text-primary)] uppercase group-hover:text-[#1E6FD9] transition-colors">
                        {caseItem.case_number}
                      </span>
                      <span className={`px-1.5 py-0.5 text-[7.5px] rounded font-bold uppercase ${
                        caseItem.priority === 'critical' ? 'bg-red-950/40 text-red-400 border border-red-900/40' :
                        caseItem.priority === 'high' ? 'bg-orange-950/40 text-orange-400 border border-orange-900/40' :
                        caseItem.priority === 'medium' ? 'bg-yellow-950/40 text-yellow-400 border border-yellow-900/40' :
                        'bg-green-950/40 text-green-400 border border-green-900/40'
                      }`}>
                        {caseItem.priority}
                      </span>
                    </div>
                    <p className="text-[9px] text-[var(--text-secondary)] line-clamp-2 leading-relaxed mb-2">
                      {caseItem.description || 'No description'}
                    </p>
                    <div className="flex items-center justify-between text-[8px] text-[var(--text-muted)]">
                      <span className="flex items-center gap-1">
                        <Activity className="w-3 h-3" />
                        {isOpening ? (
                          <span className="flex items-center gap-1.5 text-[#1E6FD9]">
                            <span className="w-2.5 h-2.5 rounded-full border border-[#1E6FD9] border-t-transparent animate-spin inline-block" />
                            Loading dossier...
                          </span>
                        ) : (
                          caseItem.status.replace(/_/g, ' ')
                        )}
                      </span>
                      <span>{caseItem.progress}% complete</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Detail View ──
  if (loadingDetail || !investigationData) {
    return (
      <div className="min-h-[84vh] space-y-6 p-1 md:p-3">
        <button
          onClick={handleBack}
          className="flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors text-xs uppercase font-bold cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Case List
        </button>

        {/* Clear, labeled loading state */}
        <div className="p-6 bg-secondary-bg border border-border-color rounded-card flex flex-col items-center justify-center gap-4 text-center">
          <div className="w-10 h-10 rounded-full border-2 border-[#1E6FD9] border-t-transparent animate-spin" />
          <div>
            <p className="text-xs uppercase tracking-[0.2em] font-bold text-[var(--text-primary)]">
              Loading Investigation Dossier
            </p>
            <p className="text-[10px] text-[var(--text-muted)] mt-1 uppercase">
              Aggregating case, FIRs, criminals, evidence, timelime & AI intelligence...
            </p>
          </div>
          <div className="flex items-center gap-2 text-[9px] text-[var(--text-muted)] uppercase">
            <span className="w-1.5 h-1.5 rounded-full bg-[#1E6FD9] animate-pulse" />
            Securing unified investigation context
          </div>
        </div>

        <div className="space-y-4">
          <CardSkeleton />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              <CardSkeleton />
              <CardSkeleton />
            </div>
            <div className="space-y-4">
              <CardSkeleton />
              <CardSkeleton />
            </div>
          </div>
        </div>
      </div>
    );
  }

  const { case: caseInfo, firs, criminals, evidence, timeline, ai_recommendations } = investigationData;

  return (
    <div className="min-h-[84vh] space-y-6 p-1 md:p-3">
      {/* Back button */}
      <button
        onClick={handleBack}
        className="flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer text-xs uppercase font-bold"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Case List
      </button>

      {/* Dashboard Header */}
      <InvestigationDashboard data={caseInfo} />

      {/* Progress */}
      <CaseProgress progress={caseInfo.progress} status={caseInfo.status} />

      {/* MO Pattern Intelligence & Explainable Matching Section */}
      <MOPatternExplorer
        currentCaseId={selectedCaseId!}
        currentCaseNumber={caseInfo.case_number}
        onSelectCase={(caseId) => loadInvestigation(caseId)}
        onSelectCriminal={(criminalId) => {
          if (selectedCaseId) {
            sessionStorage.setItem('return_to_case_id', selectedCaseId);
            sessionStorage.setItem('return_to_case_number', caseInfo.case_number);
          }
          window.dispatchEvent(
            new CustomEvent('navigate-tab', {
              detail: { tab: 'criminals', targetId: criminalId },
            })
          );
        }}
      />

      {/* Main Grid: 3 columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: FIRs + Criminals */}
        <div className="lg:col-span-2 space-y-6">
          <LinkedFIRs firs={firs} />
          <LinkedCriminals criminals={criminals} />
          <LinkedEvidence evidence={evidence} />
        </div>

        {/* Right Column: Timeline + AI + Chat */}
        <div className="space-y-6">
          <InvestigationTimeline events={timeline} />
          <AIRecommendations recommendations={ai_recommendations} />
          <AIChatPanel caseId={selectedCaseId!} />
        </div>
      </div>
    </div>
  );
};

export default InvestigationPage;

