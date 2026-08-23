import React, { useEffect, useState } from 'react';
import { Search, ArrowLeft, Layers, Activity } from 'lucide-react';
import { getInvestigation, getCrimeCases } from '../../services/api';
import type { InvestigationData, CrimeCaseDetailRecord } from '../../services/api';
import InvestigationDashboard from '../../components/investigation/InvestigationDashboard';
import CaseProgress from '../../components/investigation/CaseProgress';
import InvestigationTimeline from '../../components/investigation/InvestigationTimeline';
import LinkedFIRs from '../../components/investigation/LinkedFIRs';
import LinkedCriminals from '../../components/investigation/LinkedCriminals';
import LinkedEvidence from '../../components/investigation/LinkedEvidence';
import AIRecommendations from '../../components/investigation/AIRecommendations';
import AIChatPanel from '../../components/investigation/AIChatPanel';
import { CardSkeleton } from '../../components/ui/Skeleton';

type ViewState = 'list' | 'detail';

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

  useEffect(() => {
    loadCases();
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
              placeholder="Search cases by number, description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-[var(--bg-secondary)]/70 border border-[var(--border-primary)] rounded text-[var(--text-primary)] outline-none focus:border-[#1E6FD9] text-[10.5px]"
            />
            <Search className="absolute left-2.5 w-3.5 h-3.5 text-[var(--text-muted)]" />
          </div>
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
        </div>

        {/* Case List */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {loading ? (
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
              {cases.map((caseItem) => (
                <button
                  key={caseItem.id}
                  onClick={() => loadInvestigation(caseItem.id)}
                  className="p-4 bg-secondary-bg border border-border-color rounded-card text-left hover:border-[#1E6FD9]/30 hover:bg-[#1E6FD9]/5 transition-all cursor-pointer group"
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
                      {caseItem.status.replace(/_/g, ' ')}
                    </span>
                    <span>{caseItem.progress}% complete</span>
                  </div>
                </button>
              ))}
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
        <div className="flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors text-xs uppercase font-bold">
          <ArrowLeft className="w-4 h-4" /> Back to Case List
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

