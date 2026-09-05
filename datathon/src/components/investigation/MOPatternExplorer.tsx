import React, { useEffect, useState, useMemo } from 'react';
import {
  ShieldAlert,
  Fingerprint,
  Users,
  FileText,
  MapPin,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  ExternalLink,
  SlidersHorizontal,
  X,
  Clock,
  ChevronRight,
  MoreVertical,
  Network,
  Calendar,
  Layers,
  Filter,
  ArrowUpDown,
  Search,
  Check,
  Minus,
  Shield,
  AlertTriangle,
} from 'lucide-react';
import {
  getCaseMOMatches,
  getRecurringMOPatterns,
  compareMOEntities,
  type MOMatchCaseResponse,
  type MOPattern,
  type MOMatchingCase,
  type MOMatchingSuspect,
  type MOCompareResponse,
} from '../../services/api';

interface MOPatternExplorerProps {
  currentCaseId?: string;
  currentCaseNumber?: string;
  onSelectCase?: (caseId: string) => void;
  onSelectCriminal?: (criminalId: string) => void;
}

type SortOption = 'similarity' | 'confidence' | 'status';

interface SelectedDetail {
  type: 'suspect' | 'case';
  suspect?: MOMatchingSuspect;
  caseItem?: MOMatchingCase;
}

// ── Readability helpers & compact UI primitives ─────────────────────────────

const humanizeTag = (tag: string): string =>
  (tag || '')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .slice(0, 48);

interface TagClusterProps {
  tags: string[];
  limit?: number;
  empty?: string;
  accent?: string;
}

/** Compact chip row for MO tags: first `limit` chips + expandable remainder. */
const TagCluster: React.FC<TagClusterProps> = ({ tags, limit = 6, empty = 'None recorded', accent }) => {
  const [expanded, setExpanded] = useState(false);
  const clean = (tags || []).filter(Boolean);
  if (clean.length === 0) {
    return <span className="text-[11px] text-[var(--text-muted)] italic">{empty}</span>;
  }
  const visible = expanded ? clean : clean.slice(0, limit);
  const hidden = clean.length - visible.length;
  return (
    <div className="flex flex-wrap items-center gap-1.5 min-w-0">
      {visible.map((tag) => (
        <span
          key={tag}
          title={humanizeTag(tag)}
          className={`px-2 py-0.5 rounded-md border text-[10px] font-mono font-medium tracking-wide whitespace-nowrap max-w-full overflow-hidden text-ellipsis ${
            accent || 'bg-[#1E6FD9]/10 border-[#1E6FD9]/25 text-[var(--text-secondary)]'
          }`}
        >
          {humanizeTag(tag)}
        </span>
      ))}
      {hidden > 0 && !expanded && (
        <span
          role="button"
          tabIndex={-1}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setExpanded(true);
          }}
          className="px-2 py-0.5 rounded-md border border-[var(--border-primary)] bg-[var(--bg-secondary)] text-[10px] font-semibold text-[#1E6FD9] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
        >
          +{hidden} more
        </span>
      )}
      {expanded && clean.length > limit && (
        <span
          role="button"
          tabIndex={-1}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setExpanded(false);
          }}
          className="px-2 py-0.5 text-[10px] font-semibold text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          − collapse
        </span>
      )}
    </div>
  );
};

const patternDisplayName = (p: MOPattern, index: number): string => {
  if (p.dominant_category) return p.dominant_category;
  const tags = (p.shared_tags || []).filter(Boolean);
  if (tags.length > 0) return `${tags.slice(0, 2).map(humanizeTag).join(' & ')} Pattern`;
  return `Cluster ${String(index + 1).padStart(2, '0')}`;
};

const threatColor = (score: number): string => {
  if (score >= 70) return 'bg-red-950/40 text-red-400 border-red-800/60';
  if (score >= 40) return 'bg-amber-950/40 text-amber-400 border-amber-800/60';
  return 'bg-emerald-950/40 text-emerald-400 border-emerald-800/60';
};

const compareStatus = (status: 'match' | 'partial' | 'mismatch' | 'same_district' | 'no_data') => {
  if (status === 'match') {
    return <span className="text-emerald-400 font-bold">✓ Match</span>;
  }
  if (status === 'partial') {
    return <span className="text-amber-400 font-bold">△ Partial</span>;
  }
  if (status === 'mismatch') {
    return <span className="text-red-400/80 font-medium">✕ Mismatch</span>;
  }
  if (status === 'same_district') {
    return <span className="text-emerald-400 font-bold">✓ Same District</span>;
  }
  return <span className="text-slate-500">— No Data</span>;
};

export const MOPatternExplorer: React.FC<MOPatternExplorerProps> = ({
  currentCaseId,
  currentCaseNumber,
  onSelectCase,
  onSelectCriminal,
}) => {
  const [activeTab, setActiveTab] = useState<'case_matches' | 'recurring_clusters' | 'compare'>('case_matches');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Case Matching State
  const [caseMatchData, setCaseMatchData] = useState<MOMatchCaseResponse | null>(null);
  const [minSimilarity, setMinSimilarity] = useState<number>(0.25);
  const [sortBy, setSortBy] = useState<SortOption>('similarity');
  const [filterConfidence, setFilterConfidence] = useState<'all' | 'high' | 'medium'>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showFilters, setShowFilters] = useState<boolean>(false);

  // Progressive Disclosure: Detail Drawer State
  const [detailItem, setDetailItem] = useState<SelectedDetail | null>(null);
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  // Recurring Patterns State
  const [patterns, setPatterns] = useState<MOPattern[]>([]);
  const [selectedPattern, setSelectedPattern] = useState<MOPattern | null>(null);

  // Comparison State
  const [compareData, setCompareData] = useState<MOCompareResponse | null>(null);
  const [compareTargetEntity, setCompareTargetEntity] = useState<{ id: string; type: 'case' | 'criminal'; name: string } | null>(null);
  const [compareLoading, setCompareLoading] = useState<boolean>(false);

  // Close menus on outside click
  useEffect(() => {
    const handleGlobalClick = () => setActiveMenuId(null);
    window.addEventListener('click', handleGlobalClick);
    return () => window.removeEventListener('click', handleGlobalClick);
  }, []);

  // Keyboard shortcut: Esc to close drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setDetailItem(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Load Case MO Matches
  useEffect(() => {
    if (!currentCaseId) return;
    let isMounted = true;
    setLoading(true);
    setError(null);

    getCaseMOMatches(currentCaseId, minSimilarity, 10)
      .then((res) => {
        if (!isMounted) return;
        if (res.error) {
          setError(res.error);
        } else {
          setCaseMatchData(res);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : 'Failed to load MO matches');
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [currentCaseId, minSimilarity]);

  // Load Recurring Patterns
  useEffect(() => {
    if (activeTab !== 'recurring_clusters' && patterns.length > 0) return;
    let isMounted = true;
    setLoading(true);

    getRecurringMOPatterns(2, 10)
      .then((res) => {
        if (!isMounted) return;
        setPatterns(res.patterns || []);
        if (res.patterns && res.patterns.length > 0 && !selectedPattern) {
          setSelectedPattern(res.patterns[0]);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Failed to load recurring patterns:', err);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [activeTab]);

  const handleRunCompare = (entityId: string, entityType: 'case' | 'criminal', entityName: string) => {
    if (!currentCaseId) return;
    setCompareTargetEntity({ id: entityId, type: entityType, name: entityName });
    setActiveTab('compare');
    setDetailItem(null);
    setCompareLoading(true);

    compareMOEntities({
      entity_a_id: currentCaseId,
      entity_a_type: 'case',
      entity_b_id: entityId,
      entity_b_type: entityType,
    })
      .then((res) => {
        setCompareData(res);
      })
      .catch((err) => {
        console.error('MO comparison failed:', err);
      })
      .finally(() => {
        setCompareLoading(false);
      });
  };

  const handleNavigateNetwork = (targetId: string) => {
    window.dispatchEvent(
      new CustomEvent('navigate-tab', {
        detail: { tab: 'network', targetId },
      })
    );
  };

  const handleNavigateTimeline = (targetId: string) => {
    window.dispatchEvent(
      new CustomEvent('navigate-tab', {
        detail: { tab: 'investigation', targetId },
      })
    );
  };

  // Helper for semantic match badge color
  const getMatchTheme = (percent: number, level: string) => {
    if (level === 'high' || percent >= 70) {
      return {
        badge: 'bg-emerald-950/60 text-emerald-400 border-emerald-700/60',
        bar: 'bg-emerald-500',
        text: 'text-emerald-400',
        label: 'High Confidence',
      };
    }
    if (level === 'medium' || percent >= 45) {
      return {
        badge: 'bg-amber-950/60 text-amber-400 border-amber-700/60',
        bar: 'bg-amber-500',
        text: 'text-amber-400',
        label: 'Medium Confidence',
      };
    }
    return {
      badge: 'bg-blue-950/60 text-blue-400 border-blue-700/60',
      bar: 'bg-blue-500',
      text: 'text-blue-400',
      label: 'Analytical Lead',
    };
  };

  // Helper to extract a short summary from factors
  const getShortFactorSummary = (matchingFactors: string[]): string => {
    if (!matchingFactors || matchingFactors.length === 0) return 'No matching factors';
    if (matchingFactors.length === 1) return matchingFactors[0].split(':')[0] || matchingFactors[0];
    return `${matchingFactors.length} matching MO factors`;
  };

  // Filtered and sorted suspects
  const processedSuspects = useMemo(() => {
    if (!caseMatchData?.matching_suspects) return [];
    let list = [...caseMatchData.matching_suspects];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (s) =>
          s.full_name.toLowerCase().includes(q) ||
          (s.aliases && s.aliases.toLowerCase().includes(q)) ||
          s.status.toLowerCase().includes(q)
      );
    }

    if (filterConfidence === 'high') {
      list = list.filter((s) => s.match_level === 'high' || s.similarity_percent >= 75);
    } else if (filterConfidence === 'medium') {
      list = list.filter((s) => s.match_level === 'high' || s.match_level === 'medium');
    }

    if (sortBy === 'similarity') {
      list.sort((a, b) => b.similarity_percent - a.similarity_percent);
    } else if (sortBy === 'confidence') {
      list.sort((a, b) => b.confidence - a.confidence);
    } else if (sortBy === 'status') {
      list.sort((a, b) => a.status.localeCompare(b.status));
    }

    return list;
  }, [caseMatchData, searchQuery, filterConfidence, sortBy]);

  // Filtered and sorted cases
  const processedCases = useMemo(() => {
    if (!caseMatchData?.matching_cases) return [];
    let list = [...caseMatchData.matching_cases];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (c) =>
          c.case_number.toLowerCase().includes(q) ||
          (c.category && c.category.toLowerCase().includes(q)) ||
          (c.station && c.station.toLowerCase().includes(q)) ||
          (c.district && c.district.toLowerCase().includes(q))
      );
    }

    if (filterConfidence === 'high') {
      list = list.filter((c) => c.match_level === 'high' || c.similarity_percent >= 75);
    } else if (filterConfidence === 'medium') {
      list = list.filter((c) => c.match_level === 'high' || c.match_level === 'medium');
    }

    if (sortBy === 'similarity') {
      list.sort((a, b) => b.similarity_percent - a.similarity_percent);
    } else if (sortBy === 'confidence') {
      list.sort((a, b) => b.confidence - a.confidence);
    } else if (sortBy === 'status') {
      list.sort((a, b) => a.status.localeCompare(b.status));
    }

    return list;
  }, [caseMatchData, searchQuery, filterConfidence, sortBy]);

  const targetCase = caseMatchData?.target_case;
  const targetProfile = targetCase?.profile || {};

  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl overflow-hidden shadow-sm relative text-left">
      {/* 1. Header Banner: Target Subject */}
      <div className="p-4 sm:p-5 bg-[var(--bg-tertiary)]/40 border-b border-[var(--border-primary)]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 bg-[#1E6FD9]/10 border border-[#1E6FD9]/30 rounded-xl text-[#1E6FD9] shrink-0 mt-0.5 shadow-xs">
              <Fingerprint className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <span className="text-[10px] font-mono tracking-widest text-[#1E6FD9] uppercase font-bold px-2 py-0.5 bg-[#1E6FD9]/10 rounded border border-[#1E6FD9]/20">
                  TARGET SUBJECT
                </span>
                <span className="text-sm font-bold text-[var(--text-primary)] font-mono">
                  {currentCaseNumber || targetCase?.case_number || 'Target Case'}
                </span>
                {targetCase?.category && (
                  <span className="text-xs px-2.5 py-0.5 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-md font-medium text-[var(--text-secondary)]">
                    {targetCase.category}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-4 text-xs text-[var(--text-muted)] mt-1.5 flex-wrap">
                {targetCase?.district && (
                  <span className="flex items-center gap-1.5 font-medium">
                    <MapPin className="w-3.5 h-3.5 text-[#1E6FD9]" />
                    {targetProfile.station || targetCase.district}
                  </span>
                )}
                {targetProfile.time_window && (
                  <span className="flex items-center gap-1.5 font-medium">
                    <Clock className="w-3.5 h-3.5 text-amber-400" />
                    {targetProfile.time_window}
                  </span>
                )}
                {targetProfile.target_type && (
                  <span className="flex items-center gap-1.5 font-medium">
                    <ShieldAlert className="w-3.5 h-3.5 text-indigo-400" />
                    {targetProfile.target_type}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Navigation Tab Pills */}
          <div className="flex items-center bg-[var(--bg-primary)] p-1 rounded-lg border border-[var(--border-primary)] text-xs shrink-0 self-start sm:self-auto">
            <button
              onClick={() => setActiveTab('case_matches')}
              className={`px-3.5 py-1.5 rounded-md font-semibold transition-all cursor-pointer ${
                activeTab === 'case_matches'
                  ? 'bg-[#1E6FD9] text-white shadow-xs'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              Ranked Matches
            </button>
            <button
              onClick={() => setActiveTab('recurring_clusters')}
              className={`px-3.5 py-1.5 rounded-md font-semibold transition-all cursor-pointer ${
                activeTab === 'recurring_clusters'
                  ? 'bg-[#1E6FD9] text-white shadow-xs'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              Statewide Clusters
            </button>
            {compareData && (
              <button
                onClick={() => setActiveTab('compare')}
                className={`px-3.5 py-1.5 rounded-md font-semibold transition-all cursor-pointer ${
                  activeTab === 'compare'
                    ? 'bg-[#1E6FD9] text-white shadow-xs'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Deep Compare
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 2. Compact Analysis Toolbar */}
      {activeTab === 'case_matches' && (
        <div className="px-4 sm:px-5 py-3 bg-[var(--bg-primary)]/80 border-b border-[var(--border-primary)] flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Left info & search */}
          <div className="flex items-center gap-3.5 flex-wrap flex-1 min-w-[220px]">
            <span className="text-xs text-[var(--text-muted)] font-mono">
              Evaluated:{' '}
              <strong className="text-[var(--text-primary)] font-semibold">
                {caseMatchData?.total_cases_evaluated || 0} cases
              </strong>{' '}
              ·{' '}
              <strong className="text-[var(--text-primary)] font-semibold">
                {caseMatchData?.total_criminals_evaluated || 0} offenders
              </strong>
            </span>

            <div className="relative flex-1 max-w-[240px]">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
              <input
                type="text"
                placeholder="Filter by name, station..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-2.5 py-1.5 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg text-xs text-[var(--text-primary)] focus:outline-none focus:border-[#1E6FD9]"
              />
            </div>
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-2.5 flex-wrap">
            {/* Sort Selector */}
            <div className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
              <ArrowUpDown className="w-3.5 h-3.5 text-[var(--text-muted)]" />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                aria-label="Sort by"
                className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg px-2.5 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none focus:border-[#1E6FD9] cursor-pointer"
              >
                <option value="similarity">Similarity (Highest)</option>
                <option value="confidence">Confidence</option>
                <option value="status">Status</option>
              </select>
            </div>

            {/* Filter Popover Toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-3 py-1.5 rounded-lg border text-xs flex items-center gap-1.5 transition-all cursor-pointer ${
                showFilters || minSimilarity !== 0.25 || filterConfidence !== 'all'
                  ? 'bg-[#1E6FD9]/15 border-[#1E6FD9]/40 text-[#1E6FD9] font-semibold'
                  : 'bg-[var(--bg-secondary)] border-[var(--border-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              <span>Filters</span>
              {(minSimilarity !== 0.25 || filterConfidence !== 'all') && (
                <span className="w-1.5 h-1.5 rounded-full bg-[#1E6FD9]" />
              )}
            </button>

            {/* Refresh */}
            <button
              onClick={() => {
                if (currentCaseId) {
                  setLoading(true);
                  getCaseMOMatches(currentCaseId, minSimilarity, 10).then((res) => {
                    setCaseMatchData(res);
                    setLoading(false);
                  });
                }
              }}
              title="Refresh database match"
              className="p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] rounded-lg transition-all cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      )}

      {/* Expanded Filters Drawer */}
      {showFilters && activeTab === 'case_matches' && (
        <div className="p-4 bg-[var(--bg-tertiary)]/50 border-b border-[var(--border-primary)] grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-semibold text-[var(--text-secondary)]">
                Minimum Match Threshold: <strong className="text-[#1E6FD9]">{Math.round(minSimilarity * 100)}%</strong>
              </label>
              <button
                onClick={() => setMinSimilarity(0.25)}
                className="text-[11px] text-[var(--text-muted)] hover:underline cursor-pointer"
              >
                Reset
              </button>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.80"
              step="0.05"
              value={minSimilarity}
              onChange={(e) => setMinSimilarity(parseFloat(e.target.value))}
              className="w-full accent-[#1E6FD9] cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-[var(--text-muted)] mt-1 font-mono">
              <span>10% (Broad)</span>
              <span>25% (Standard)</span>
              <span>50% (Strict)</span>
              <span>75% (High Only)</span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5">
              Confidence Filter
            </label>
            <div className="flex gap-2">
              {(['all', 'medium', 'high'] as const).map((conf) => (
                <button
                  key={conf}
                  onClick={() => setFilterConfidence(conf)}
                  className={`px-3 py-1.5 rounded-lg border text-xs capitalize cursor-pointer transition-all ${
                    filterConfidence === conf
                      ? 'bg-[#1E6FD9] border-[#1E6FD9] text-white font-semibold'
                      : 'bg-[var(--bg-secondary)] border-[var(--border-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  {conf === 'all' ? 'All Confidences' : `${conf} Confidence`}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="p-4 sm:p-5">
        {loading && !caseMatchData ? (
          /* Loading skeleton */
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <div className="h-4 w-36 bg-[var(--bg-tertiary)] animate-pulse rounded" />
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-4 bg-[var(--bg-tertiary)]/50 rounded-xl border border-[var(--border-primary)] space-y-3">
                  <div className="h-4 bg-[var(--bg-tertiary)] animate-pulse rounded w-3/4" />
                  <div className="h-3 bg-[var(--bg-tertiary)] animate-pulse rounded w-1/2" />
                  <div className="h-7 bg-[var(--bg-tertiary)] animate-pulse rounded w-1/3" />
                </div>
              ))}
            </div>
            <div className="space-y-3">
              <div className="h-4 w-36 bg-[var(--bg-tertiary)] animate-pulse rounded" />
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-4 bg-[var(--bg-tertiary)]/50 rounded-xl border border-[var(--border-primary)] space-y-3">
                  <div className="h-4 bg-[var(--bg-tertiary)] animate-pulse rounded w-3/4" />
                  <div className="h-3 bg-[var(--bg-tertiary)] animate-pulse rounded w-1/2" />
                  <div className="h-7 bg-[var(--bg-tertiary)] animate-pulse rounded w-1/3" />
                </div>
              ))}
            </div>
          </div>
        ) : error ? (
          <div className="p-6 bg-red-950/20 border border-red-900/40 rounded-xl text-center text-red-300 text-xs space-y-2">
            <p className="font-semibold text-sm">Unable to load analytical MO matches</p>
            <p className="text-xs text-red-400/80">{error}</p>
          </div>
        ) : activeTab === 'case_matches' ? (
          /* 3. Progressive Disclosure: Two-Column Scannable Match List */
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 sm:gap-6 items-start">
            {/* LEFT COLUMN: Suspect / Offender Matches */}
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-[var(--border-primary)] pb-2.5">
                <span className="text-xs font-bold uppercase tracking-wider text-[#1E6FD9] flex items-center gap-2 font-mono">
                  <Users className="w-4 h-4" /> Suspect MO Matches ({processedSuspects.length})
                </span>
                <span className="text-[10px] text-[var(--text-muted)] font-mono">RANKED BY SIMILARITY</span>
              </div>

              {processedSuspects.length > 0 ? (
                <div className="space-y-3">
                  {processedSuspects.map((suspect) => {
                    const theme = getMatchTheme(suspect.similarity_percent, suspect.match_level);
                    return (
                      <div
                        key={suspect.criminal_id}
                        className={`p-3.5 sm:p-4 bg-[var(--bg-tertiary)]/30 hover:bg-[var(--bg-tertiary)]/70 border rounded-xl transition-all duration-150 relative ${
                          detailItem?.suspect?.criminal_id === suspect.criminal_id
                            ? 'border-[#1E6FD9] ring-2 ring-[#1E6FD9]/30 bg-[var(--bg-tertiary)]/90 shadow-sm'
                            : 'border-[var(--border-primary)]'
                        }`}
                      >
                        {/* Compact Card Header */}
                        <div className="flex justify-between items-start gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <h4 className="text-sm font-bold text-[var(--text-primary)] truncate">
                                {suspect.full_name}
                              </h4>
                              {suspect.aliases && (
                                <span className="text-xs text-[var(--text-muted)] truncate">
                                  (alias: {suspect.aliases})
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 mt-1.5 flex-wrap text-xs">
                              <span
                                className={`px-2 py-0.5 border rounded-md font-semibold text-[10px] uppercase ${
                                  suspect.is_confirmed_relationship
                                    ? 'bg-emerald-950/50 text-emerald-400 border-emerald-800/60'
                                    : 'bg-indigo-950/50 text-indigo-400 border-indigo-800/60'
                                }`}
                              >
                                {suspect.relationship_label}
                              </span>
                              <span className="text-[var(--text-muted)] text-[11px] uppercase font-mono font-medium">
                                {suspect.status}
                              </span>
                              {suspect.gang_affiliation && (
                                <span className="text-amber-400/90 font-mono text-[11px]">
                                  Gang: {suspect.gang_affiliation}
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Match Meter Gauge */}
                          <div className="text-right shrink-0">
                            <div className="flex items-center gap-1.5 justify-end">
                              <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded-md border ${theme.badge}`}>
                                {suspect.similarity_percent}% MATCH
                              </span>
                            </div>
                            <span className="text-[10px] text-[var(--text-muted)] block mt-0.5 font-medium">
                              {theme.label}
                            </span>
                          </div>
                        </div>

                        {/* Visual Similarity Gauge Bar */}
                        <div className="w-full bg-[var(--bg-primary)] rounded-full h-1.5 mt-3 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${theme.bar}`}
                            style={{ width: `${Math.min(100, Math.max(5, suspect.similarity_percent))}%` }}
                          />
                        </div>

                        {/* Summary factor line & Actions */}
                        <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-[var(--border-primary)]/50 gap-2">
                          <span className="text-xs text-[var(--text-secondary)] truncate flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            {getShortFactorSummary(suspect.matching_factors)}
                          </span>

                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              onClick={() => setDetailItem({ type: 'suspect', suspect })}
                              className="px-3 py-1.5 bg-[#1E6FD9] hover:bg-[#1858ad] text-white rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
                            >
                              <span>View Analysis</span>
                              <ChevronRight className="w-3.5 h-3.5" />
                            </button>

                            {/* Secondary Menu */}
                            <div className="relative">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(activeMenuId === suspect.criminal_id ? null : suspect.criminal_id);
                                }}
                                aria-label="More actions"
                                className="p-1.5 hover:bg-[var(--bg-secondary)] border border-transparent hover:border-[var(--border-primary)] rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-all cursor-pointer"
                              >
                                <MoreVertical className="w-4 h-4" />
                              </button>

                              {activeMenuId === suspect.criminal_id && (
                                <div
                                  onClick={(e) => e.stopPropagation()}
                                  className="absolute right-0 top-full mt-1 w-48 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-xl shadow-xl py-1.5 z-30 text-xs"
                                >
                                  <button
                                    onClick={() => {
                                      setActiveMenuId(null);
                                      handleRunCompare(suspect.criminal_id, 'criminal', suspect.full_name);
                                    }}
                                    className="w-full px-3.5 py-2 text-left hover:bg-[var(--bg-tertiary)] flex items-center gap-2.5 text-[var(--text-primary)] font-medium cursor-pointer"
                                  >
                                    <SlidersHorizontal className="w-3.5 h-3.5 text-[#1E6FD9]" />
                                    <span>Deep Compare</span>
                                  </button>
                                  {onSelectCriminal && (
                                    <button
                                      onClick={() => {
                                        setActiveMenuId(null);
                                        onSelectCriminal(suspect.criminal_id);
                                      }}
                                      className="w-full px-3.5 py-2 text-left hover:bg-[var(--bg-tertiary)] flex items-center gap-2.5 text-[var(--text-primary)] font-medium cursor-pointer"
                                    >
                                      <ExternalLink className="w-3.5 h-3.5 text-emerald-400" />
                                      <span>Open Dossier</span>
                                    </button>
                                  )}
                                  <button
                                    onClick={() => {
                                      setActiveMenuId(null);
                                      handleNavigateNetwork(suspect.criminal_id);
                                    }}
                                    className="w-full px-3.5 py-2 text-left hover:bg-[var(--bg-tertiary)] flex items-center gap-2.5 text-[var(--text-primary)] font-medium cursor-pointer"
                                  >
                                    <Network className="w-3.5 h-3.5 text-indigo-400" />
                                    <span>View in Network</span>
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-6 bg-[var(--bg-tertiary)]/20 border border-dashed border-[var(--border-primary)] rounded-xl text-center text-[var(--text-muted)] text-xs">
                  No suspect MO matches found above {Math.round(minSimilarity * 100)}% similarity.
                </div>
              )}
            </div>

            {/* RIGHT COLUMN: Serial Crime Case Links */}
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-[var(--border-primary)] pb-2.5">
                <span className="text-xs font-bold uppercase tracking-wider text-[#1E6FD9] flex items-center gap-2 font-mono">
                  <FileText className="w-4 h-4" /> Serial Case Links ({processedCases.length})
                </span>
                <span className="text-[10px] text-[var(--text-muted)] font-mono">SIMILAR PATTERNS</span>
              </div>

              {processedCases.length > 0 ? (
                <div className="space-y-3">
                  {processedCases.map((otherCase) => {
                    const theme = getMatchTheme(otherCase.similarity_percent, otherCase.match_level);
                    return (
                      <div
                        key={otherCase.case_id}
                        className={`p-3.5 sm:p-4 bg-[var(--bg-tertiary)]/30 hover:bg-[var(--bg-tertiary)]/70 border rounded-xl transition-all duration-150 relative ${
                          detailItem?.caseItem?.case_id === otherCase.case_id
                            ? 'border-[#1E6FD9] ring-2 ring-[#1E6FD9]/30 bg-[var(--bg-tertiary)]/90 shadow-sm'
                            : 'border-[var(--border-primary)]'
                        }`}
                      >
                        {/* Compact Card Header */}
                        <div className="flex justify-between items-start gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <h4 className="text-sm font-bold text-[var(--text-primary)] font-mono truncate">
                                Case {otherCase.case_number}
                              </h4>
                              {otherCase.category && (
                                <span className="text-xs px-2 py-0.5 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-md text-[var(--text-secondary)] font-medium truncate">
                                  {otherCase.category}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2.5 mt-1.5 text-xs text-[var(--text-muted)]">
                              <span className="flex items-center gap-1 truncate font-medium">
                                <MapPin className="w-3.5 h-3.5 text-[#1E6FD9] shrink-0" />
                                {otherCase.station || otherCase.district || 'Jurisdiction unspecified'}
                              </span>
                              <span>•</span>
                              <span className="uppercase font-mono font-medium">{otherCase.status}</span>
                            </div>
                          </div>

                          {/* Match Meter Gauge */}
                          <div className="text-right shrink-0">
                            <div className="flex items-center gap-1.5 justify-end">
                              <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded-md border ${theme.badge}`}>
                                {otherCase.similarity_percent}% MATCH
                              </span>
                            </div>
                            <span className="text-[10px] text-[var(--text-muted)] block mt-0.5 font-medium">
                              {theme.label}
                            </span>
                          </div>
                        </div>

                        {/* Visual Similarity Gauge Bar */}
                        <div className="w-full bg-[var(--bg-primary)] rounded-full h-1.5 mt-3 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${theme.bar}`}
                            style={{ width: `${Math.min(100, Math.max(5, otherCase.similarity_percent))}%` }}
                          />
                        </div>

                        {/* Summary factor line & Actions */}
                        <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-[var(--border-primary)]/50 gap-2">
                          <span className="text-xs text-[var(--text-secondary)] truncate flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            {getShortFactorSummary(otherCase.matching_factors)}
                          </span>

                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              onClick={() => setDetailItem({ type: 'case', caseItem: otherCase })}
                              className="px-3 py-1.5 bg-[#1E6FD9] hover:bg-[#1858ad] text-white rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
                            >
                              <span>View Analysis</span>
                              <ChevronRight className="w-3.5 h-3.5" />
                            </button>

                            {/* Secondary Menu */}
                            <div className="relative">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(activeMenuId === otherCase.case_id ? null : otherCase.case_id);
                                }}
                                aria-label="More actions"
                                className="p-1.5 hover:bg-[var(--bg-secondary)] border border-transparent hover:border-[var(--border-primary)] rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-all cursor-pointer"
                              >
                                <MoreVertical className="w-4 h-4" />
                              </button>

                              {activeMenuId === otherCase.case_id && (
                                <div
                                  onClick={(e) => e.stopPropagation()}
                                  className="absolute right-0 top-full mt-1 w-48 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-xl shadow-xl py-1.5 z-30 text-xs"
                                >
                                  <button
                                    onClick={() => {
                                      setActiveMenuId(null);
                                      handleRunCompare(otherCase.case_id, 'case', otherCase.case_number);
                                    }}
                                    className="w-full px-3.5 py-2 text-left hover:bg-[var(--bg-tertiary)] flex items-center gap-2.5 text-[var(--text-primary)] font-medium cursor-pointer"
                                  >
                                    <SlidersHorizontal className="w-3.5 h-3.5 text-[#1E6FD9]" />
                                    <span>Deep Compare</span>
                                  </button>
                                  {onSelectCase && (
                                    <button
                                      onClick={() => {
                                        setActiveMenuId(null);
                                        onSelectCase(otherCase.case_id);
                                      }}
                                      className="w-full px-3.5 py-2 text-left hover:bg-[var(--bg-tertiary)] flex items-center gap-2.5 text-[var(--text-primary)] font-medium cursor-pointer"
                                    >
                                      <ArrowRight className="w-3.5 h-3.5 text-emerald-400" />
                                      <span>Switch Investigation</span>
                                    </button>
                                  )}
                                  <button
                                    onClick={() => {
                                      setActiveMenuId(null);
                                      handleNavigateTimeline(otherCase.case_id);
                                    }}
                                    className="w-full px-3.5 py-2 text-left hover:bg-[var(--bg-tertiary)] flex items-center gap-2.5 text-[var(--text-primary)] font-medium cursor-pointer"
                                  >
                                    <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                                    <span>View Timeline</span>
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-6 bg-[var(--bg-tertiary)]/20 border border-dashed border-[var(--border-primary)] rounded-xl text-center text-[var(--text-muted)] text-xs">
                  No matching serial cases found above {Math.round(minSimilarity * 100)}% similarity.
                </div>
              )}
            </div>
          </div>
        ) : activeTab === 'recurring_clusters' ? (
          /* 4. Statewide MO Pattern Clusters (structured intelligence cards) */
          <div className="space-y-4 min-w-0">
            <div className="flex items-center justify-between border-b border-[var(--border-primary)] pb-2.5">
              <span className="text-xs font-bold uppercase tracking-wider text-[#1E6FD9] flex items-center gap-2 font-mono">
                <Layers className="w-4 h-4" /> Statewide MO Patterns & Syndicate Clusters
              </span>
              <span className="text-[10px] text-[var(--text-muted)] font-mono">UNSUPERVISED TACTICAL MINING</span>
            </div>

            {loading && patterns.length === 0 ? (
              <div className="p-10 text-center text-xs text-[var(--text-muted)] space-y-2.5">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto text-[#1E6FD9]" />
                <p className="font-medium">Mining statewide MO patterns...</p>
              </div>
            ) : patterns.length === 0 ? (
              <div className="p-10 text-center text-xs text-[var(--text-muted)] border border-dashed border-[var(--border-primary)] rounded-xl">
                No recurring MO patterns detected yet. Patterns require at least two entities sharing
                overlapping modus-operandi signatures.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
                {/* Left: selectable cluster cards */}
                <div className="space-y-2.5 max-h-[560px] overflow-y-auto pr-1 min-w-0">
                  {patterns.map((p, idx) => (
                    <button
                      key={p.pattern_id}
                      onClick={() => setSelectedPattern(p)}
                      className={`w-full max-w-full p-3.5 rounded-xl border text-left transition-all cursor-pointer min-w-0 ${
                        selectedPattern?.pattern_id === p.pattern_id
                          ? 'bg-[#1E6FD9]/15 border-[#1E6FD9] shadow-xs'
                          : 'bg-[var(--bg-tertiary)]/40 hover:bg-[var(--bg-tertiary)]/80 border-[var(--border-primary)]'
                      }`}
                    >
                      <div className="flex justify-between items-center gap-2 min-w-0">
                        <span className="text-xs font-bold text-[var(--text-primary)] capitalize truncate">
                          {patternDisplayName(p, idx)}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 bg-[#1E6FD9]/20 text-[#1E6FD9] font-bold rounded-md shrink-0">
                          {p.case_count || 0} cases
                        </span>
                      </div>
                      <p className="text-[11px] text-[var(--text-muted)] mt-1 min-w-0 truncate">
                        {p.case_count || 0} case{p.case_count === 1 ? '' : 's'} · {p.criminal_count || 0} suspect{p.criminal_count === 1 ? '' : 's'}
                        {p.districts && p.districts.length > 0
                          ? ` · ${p.districts.slice(0, 2).join(', ')}${p.districts.length > 2 ? '…' : ''}`
                          : ''}
                      </p>
                      <div className="mt-2 min-w-0">
                        <TagCluster tags={p.shared_tags || []} limit={3} />
                      </div>
                      <div className="flex items-center justify-between gap-2 text-[11px] text-[var(--text-muted)] mt-2.5 pt-2 border-t border-[var(--border-primary)]/40 min-w-0">
                        <span className="truncate">{p.peak_time_window || 'Time not recorded'}</span>
                        <span className={`shrink-0 font-bold ${p.at_large_members ? 'text-red-400' : 'text-emerald-400'}`}>
                          {p.at_large_members || 0} at-large
                        </span>
                      </div>
                    </button>
                  ))}
                </div>

                {/* Right: selected cluster detail */}
                {selectedPattern && (
                  <div className="md:col-span-2 p-5 bg-[var(--bg-tertiary)]/30 border border-[var(--border-primary)] rounded-xl space-y-5 min-w-0 overflow-hidden">
                    {/* Cluster header */}
                    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border-primary)] pb-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="text-sm font-bold text-[var(--text-primary)] capitalize">
                            {patternDisplayName(selectedPattern, 0)}
                          </h4>
                          {selectedPattern.dominant_category && (
                            <span className="text-[10px] px-2 py-0.5 rounded-md bg-indigo-950/40 text-indigo-300 border border-indigo-800/50 font-mono uppercase tracking-wide">
                              {selectedPattern.dominant_category}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-[var(--text-secondary)] mt-1 min-w-0 break-words">
                          {selectedPattern.example_narrative
                            ? selectedPattern.example_narrative
                            : `${selectedPattern.case_count} cases and ${selectedPattern.criminal_count} suspects identified statewide.`}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 flex-wrap">
                        {selectedPattern.threat_score > 0 && (
                          <span className={`text-xs font-bold px-2.5 py-1 rounded-md border ${threatColor(selectedPattern.threat_score)}`}>
                            Threat {selectedPattern.threat_score}
                          </span>
                        )}
                        <span className={`text-xs font-bold px-2.5 py-1 rounded-md border ${
                          selectedPattern.at_large_members
                            ? 'bg-red-950/40 text-red-400 border-red-800/60'
                            : 'bg-emerald-950/40 text-emerald-400 border-emerald-800/60'
                        }`}>
                          {selectedPattern.at_large_members || 0} Active At-Large
                        </span>
                      </div>
                    </div>

                    {/* Stat tiles */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
                      {[
                        { label: 'Related Cases', value: selectedPattern.case_count || 0, icon: <FileText className="w-3.5 h-3.5" /> },
                        { label: 'Subjects', value: selectedPattern.criminal_count || 0, icon: <Users className="w-3.5 h-3.5" /> },
                        { label: 'At-Large', value: selectedPattern.at_large_members || 0, icon: <AlertTriangle className="w-3.5 h-3.5" /> },
                        { label: 'Threat Score', value: selectedPattern.threat_score || 0, icon: <Shield className="w-3.5 h-3.5" /> },
                        { label: 'Districts', value: selectedPattern.districts?.length || 0, icon: <MapPin className="w-3.5 h-3.5" /> },
                      ].map((s) => (
                        <div key={s.label} className="p-2.5 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg min-w-0">
                          <div className="flex items-center gap-1.5 text-[var(--text-muted)]">
                            {s.icon}
                            <span className="text-[9px] uppercase tracking-wider font-mono truncate">{s.label}</span>
                          </div>
                          <div className="text-base font-bold text-[var(--text-primary)] font-mono mt-1">{s.value}</div>
                        </div>
                      ))}
                    </div>

                    {/* Key MO patterns */}
                    <div className="min-w-0">
                      <h5 className="text-xs font-bold uppercase text-[var(--text-muted)] mb-2 font-mono">
                        Key MO Patterns
                      </h5>
                      <TagCluster tags={selectedPattern.shared_tags || []} limit={8} />
                    </div>

                    {/* Geographic spread */}
                    <div className="min-w-0">
                      <h5 className="text-xs font-bold uppercase text-[var(--text-muted)] mb-2 font-mono">
                        Geographic Spread
                      </h5>
                      {selectedPattern.districts && selectedPattern.districts.length > 0 ? (
                        <TagCluster tags={selectedPattern.districts} limit={8} empty="Statewide / unspecified" />
                      ) : (
                        <span className="text-[11px] text-[var(--text-muted)] italic">Statewide / unspecified</span>
                      )}
                    </div>

                    {/* Related crime category + time pattern */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 min-w-0">
                      <div>
                        <h5 className="text-xs font-bold uppercase text-[var(--text-muted)] mb-2 font-mono">
                          Related Crime Category
                        </h5>
                        {selectedPattern.dominant_category ? (
                          <span className="inline-flex px-2.5 py-1 rounded-md bg-indigo-950/40 text-indigo-300 border border-indigo-800/50 text-[11px] font-mono uppercase tracking-wide max-w-full overflow-hidden text-ellipsis whitespace-nowrap">
                            {selectedPattern.dominant_category}
                          </span>
                        ) : (
                          <span className="text-[11px] text-[var(--text-muted)] italic">No category recorded</span>
                        )}
                      </div>
                      <div>
                        <h5 className="text-xs font-bold uppercase text-[var(--text-muted)] mb-2 font-mono">
                          Relevant Time Pattern
                        </h5>
                        {selectedPattern.peak_time_window ? (
                          <div className="text-[11px] text-[var(--text-secondary)] min-w-0">
                            <span className="font-semibold text-[var(--text-primary)]">{selectedPattern.peak_time_window}</span>
                            {(selectedPattern.first_occurred || selectedPattern.last_occurred) && (
                              <span className="block text-[var(--text-muted)] mt-0.5">
                                {selectedPattern.first_occurred
                                  ? new Date(selectedPattern.first_occurred).toLocaleDateString()
                                  : ''}
                                {selectedPattern.last_occurred
                                  ? ` – ${new Date(selectedPattern.last_occurred).toLocaleDateString()}`
                                  : ''}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-[11px] text-[var(--text-muted)] italic">No time data recorded</span>
                        )}
                      </div>
                    </div>

                    {/* Associated entities */}
                    <div className="min-w-0">
                      <h5 className="text-xs font-bold uppercase text-[var(--text-muted)] mb-2.5 font-mono">
                        Associated Entities ({selectedPattern.members?.length || 0})
                      </h5>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-[360px] overflow-y-auto pr-1">
                        {(selectedPattern.members || []).map((m) => (
                          <div
                            key={m.id}
                            className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg flex justify-between items-center gap-2 min-w-0"
                          >
                            <div className="min-w-0">
                              <span className="text-xs font-bold text-[var(--text-primary)] block truncate">
                                {m.label}
                              </span>
                              <span className="text-[11px] text-[var(--text-muted)] block truncate">
                                {m.kind === 'criminal' ? 'Suspect' : 'Case'} · <strong className="text-[var(--text-secondary)]">{m.status || 'Active'}</strong> · {m.district || 'Karnataka'}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5 shrink-0">
                              {m.kind === 'criminal' && (
                                <button
                                  onClick={() => handleNavigateNetwork(m.id)}
                                  title="View in Network"
                                  className="hidden sm:inline-flex px-2 py-1 bg-[var(--bg-tertiary)] hover:bg-[var(--bg-secondary)] text-[var(--text-secondary)] text-xs font-bold rounded border border-[var(--border-primary)] transition-all cursor-pointer"
                                >
                                  Network
                                </button>
                              )}
                              {m.kind === 'criminal' && onSelectCriminal && (
                                <button
                                  onClick={() => onSelectCriminal(m.id)}
                                  className="px-2.5 py-1 bg-[#1E6FD9]/10 hover:bg-[#1E6FD9]/20 text-[#1E6FD9] text-xs font-bold rounded border border-[#1E6FD9]/30 transition-all cursor-pointer"
                                >
                                  Dossier
                                </button>
                              )}
                              {m.kind === 'case' && onSelectCase && (
                                <button
                                  onClick={() => onSelectCase(m.id)}
                                  className="px-2.5 py-1 bg-[#1E6FD9]/10 hover:bg-[#1E6FD9]/20 text-[#1E6FD9] text-xs font-bold rounded border border-[#1E6FD9]/30 transition-all cursor-pointer"
                                >
                                  Case
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          /* 5. Dedicated Side-by-Side Deep Compare View */
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-[var(--border-primary)] pb-2.5">
              <span className="text-xs font-bold uppercase tracking-wider text-[#1E6FD9] flex items-center gap-2 font-mono">
                <SlidersHorizontal className="w-4 h-4" /> Multi-Feature Side-by-Side Comparison
              </span>
              <button
                onClick={() => setActiveTab('case_matches')}
                className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer font-medium"
              >
                ← Back to Ranked Matches
              </button>
            </div>

            {compareLoading ? (
              <div className="p-10 text-center text-xs text-[var(--text-muted)] space-y-2.5">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto text-[#1E6FD9]" />
                <p className="font-medium">Computing multi-feature analytical similarity...</p>
              </div>
            ) : compareData ? (
              <div className="space-y-4">
                {/* Score Summary Banner */}
                <div className="p-4 sm:p-5 bg-[var(--bg-tertiary)]/50 border border-[var(--border-primary)] rounded-xl flex flex-col sm:flex-row items-center justify-between gap-3">
                  <div>
                    <span className="text-xs text-[var(--text-muted)] uppercase font-mono block">
                      Target Subject vs Compared Entity
                    </span>
                    <h4 className="text-sm sm:text-base font-bold text-[var(--text-primary)] mt-1">
                      {compareData.entity_a.label || 'Target Case'} ↔ {compareData.entity_b.label || compareTargetEntity?.name}
                    </h4>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className="text-xl font-bold font-mono text-[#1E6FD9] block">
                        {compareData.similarity_percent}%
                      </span>
                      <span className="text-xs text-[var(--text-muted)] uppercase font-medium">
                        {compareData.match_level} Confidence
                      </span>
                    </div>
                  </div>
                </div>

                {/* Structured Comparison Matrix Table */}
                <div className="border border-[var(--border-primary)] rounded-xl overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full table-fixed text-xs text-left">
                      <thead className="bg-[var(--bg-tertiary)] text-[var(--text-muted)] font-mono text-xs uppercase border-b border-[var(--border-primary)]">
                        <tr>
                          <th className="p-3 w-[22%] align-top">MO Dimension</th>
                          <th className="p-3 w-[30%] align-top">Target Case</th>
                          <th className="p-3 w-[30%] align-top">Compared Record</th>
                          <th className="p-3 w-[18%] text-center align-top">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border-primary)]/60 text-xs align-top">
                        {/* Crime Category */}
                        <tr>
                          <td className="p-3 font-semibold text-[var(--text-secondary)] font-mono text-[10px] uppercase tracking-wide">Crime Category</td>
                          <td className="p-3 text-[var(--text-primary)] break-words">
                            {compareData.entity_a.category || <span className="text-[var(--text-muted)]">No data</span>}
                          </td>
                          <td className="p-3 text-[var(--text-primary)] break-words">
                            {compareData.entity_b.category || <span className="text-[var(--text-muted)]">No data</span>}
                          </td>
                          <td className="p-3 text-center">
                            {compareData.entity_a.category && compareData.entity_b.category
                              ? (compareData.entity_a.category === compareData.entity_b.category ? compareStatus('match') : compareStatus('mismatch'))
                              : compareStatus('no_data')}
                          </td>
                        </tr>
                        {/* Operating Time Window */}
                        <tr>
                          <td className="p-3 font-semibold text-[var(--text-secondary)] font-mono text-[10px] uppercase tracking-wide">Operating Time Window</td>
                          <td className="p-3 text-[var(--text-primary)] break-words">
                            {compareData.entity_a.time_window || <span className="text-[var(--text-muted)]">No data</span>}
                          </td>
                          <td className="p-3 text-[var(--text-primary)] break-words">
                            {compareData.entity_b.time_window || <span className="text-[var(--text-muted)]">No data</span>}
                          </td>
                          <td className="p-3 text-center">
                            {compareData.entity_a.time_window && compareData.entity_b.time_window
                              ? (compareData.entity_a.time_window === compareData.entity_b.time_window ? compareStatus('match') : compareStatus('mismatch'))
                              : compareStatus('no_data')}
                          </td>
                        </tr>
                        {/* Geographic Jurisdiction */}
                        <tr>
                          <td className="p-3 font-semibold text-[var(--text-secondary)] font-mono text-[10px] uppercase tracking-wide">Geographic Jurisdiction</td>
                          <td className="p-3 text-[var(--text-primary)] break-words">
                            {compareData.entity_a.station || compareData.entity_a.district || <span className="text-[var(--text-muted)]">No data</span>}
                          </td>
                          <td className="p-3 text-[var(--text-primary)] break-words">
                            {compareData.entity_b.station || compareData.entity_b.district || <span className="text-[var(--text-muted)]">No data</span>}
                          </td>
                          <td className="p-3 text-center">
                            {(() => {
                              const sa = compareData.entity_a.station;
                              const sb = compareData.entity_b.station;
                              const da = compareData.entity_a.district;
                              const db = compareData.entity_b.district;
                              if (!da || !db) return compareStatus('no_data');
                              if (sa && sb && sa === sb) return <span className="text-emerald-400 font-bold">✓ Same Station</span>;
                              if (da === db) return compareStatus('same_district');
                              return compareStatus('mismatch');
                            })()}
                          </td>
                        </tr>
                        {/* Target Environment */}
                        <tr>
                          <td className="p-3 font-semibold text-[var(--text-secondary)] font-mono text-[10px] uppercase tracking-wide">Target Environment</td>
                          <td className="p-3 text-[var(--text-primary)] break-words">
                            {compareData.entity_a.target_type || <span className="text-[var(--text-muted)]">No data</span>}
                          </td>
                          <td className="p-3 text-[var(--text-primary)] break-words">
                            {compareData.entity_b.target_type || <span className="text-[var(--text-muted)]">No data</span>}
                          </td>
                          <td className="p-3 text-center">
                            {compareData.entity_a.target_type && compareData.entity_b.target_type
                              ? (compareData.entity_a.target_type === compareData.entity_b.target_type ? compareStatus('match') : compareStatus('mismatch'))
                              : compareStatus('no_data')}
                          </td>
                        </tr>
                        {/* Tactical Methods & MO Tags */}
                        <tr>
                          <td className="p-3 font-semibold text-[var(--text-secondary)] font-mono text-[10px] uppercase tracking-wide align-top">Tactical Methods & MO Tags</td>
                          <td className="p-3 min-w-0 align-top">
                            <TagCluster tags={compareData.entity_a.mo_tags || []} limit={6} empty="No tags recorded" />
                          </td>
                          <td className="p-3 min-w-0 align-top">
                            <TagCluster tags={compareData.entity_b.mo_tags || []} limit={6} empty="No tags recorded" />
                          </td>
                          <td className="p-3 text-center align-top">
                            {(() => {
                              const a: string[] = compareData.entity_a.mo_tags || [];
                              const b: string[] = compareData.entity_b.mo_tags || [];
                              if (a.length === 0 || b.length === 0) return compareStatus('no_data');
                              const shared = a.filter((t) => b.includes(t)).length;
                              if (shared === 0) return compareStatus('mismatch');
                              return new Set([...a, ...b]).size === shared ? compareStatus('match') : compareStatus('partial');
                            })()}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Explainability Breakdown */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="p-4 bg-emerald-950/20 border border-emerald-900/40 rounded-xl space-y-2">
                    <span className="text-emerald-400 font-bold block text-xs">
                      Matching Factors ({compareData.matching_factors.length})
                    </span>
                    {compareData.matching_factors.map((f, i) => (
                      <div key={i} className="flex items-start gap-2 text-emerald-300 text-xs">
                        <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5 text-emerald-400" />
                        <span>{f}</span>
                      </div>
                    ))}
                  </div>

                  <div className="p-4 bg-amber-950/20 border border-amber-900/40 rounded-xl space-y-2">
                    <span className="text-amber-400 font-bold block text-xs">
                      Divergent Factors ({compareData.divergent_factors.length})
                    </span>
                    {compareData.divergent_factors.map((f, i) => (
                      <div key={i} className="flex items-start gap-2 text-amber-300 text-xs">
                        <XCircle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-400" />
                        <span>{f}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>

      {/* 6. SLIDE-OVER DETAIL DRAWER (Progressive Disclosure — Spacious & Uncongested) */}
      {detailItem && (
        <>
          {/* Backdrop - High Z-Index to overlay over all headers */}
          <div
            onClick={() => setDetailItem(null)}
            className="fixed inset-0 bg-black/65 z-[110] backdrop-blur-xs transition-opacity"
          />

          {/* Spacious Drawer Panel - High Z-Index to sit above all headers */}
          <div className="fixed top-0 right-0 h-full w-full sm:w-[580px] lg:w-[640px] xl:w-[680px] max-w-[92vw] bg-[var(--bg-primary)] border-l border-[var(--border-primary)] shadow-2xl z-[120] flex flex-col transition-transform duration-200 ease-out overflow-hidden text-left">
            {/* Drawer Header with Back Button */}
            <div className="p-4 sm:p-5 bg-[var(--bg-secondary)] border-b border-[var(--border-primary)] flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                {/* Top Row: Back button + Badges */}
                <div className="flex items-center gap-2.5 mb-2.5 flex-wrap">
                  <button
                    onClick={() => setDetailItem(null)}
                    className="flex items-center gap-1.5 px-3 py-1 bg-[var(--bg-tertiary)] hover:bg-[#1E6FD9] hover:text-white text-[var(--text-primary)] border border-[var(--border-primary)] rounded-lg text-xs font-semibold transition-all cursor-pointer shadow-xs"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Back</span>
                  </button>
                  <span className="text-xs font-mono uppercase tracking-wider text-[#1E6FD9] font-bold px-2.5 py-0.5 bg-[#1E6FD9]/10 rounded border border-[#1E6FD9]/20">
                    {detailItem.type === 'suspect' ? 'SUSPECT ANALYSIS' : 'CASE LINK ANALYSIS'}
                  </span>
                  <span className="text-xs px-2.5 py-0.5 bg-[var(--bg-tertiary)] border border-[var(--border-primary)] rounded font-semibold text-[var(--text-secondary)] uppercase">
                    {detailItem.type === 'suspect' ? detailItem.suspect?.status : detailItem.caseItem?.status}
                  </span>
                </div>

                <h3 className="text-lg sm:text-xl font-bold text-[var(--text-primary)] truncate">
                  {detailItem.type === 'suspect'
                    ? detailItem.suspect?.full_name
                    : `Case ${detailItem.caseItem?.case_number}`}
                </h3>
                {detailItem.type === 'suspect' && detailItem.suspect?.aliases && (
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">Alias: {detailItem.suspect.aliases}</p>
                )}
                {detailItem.type === 'case' && detailItem.caseItem?.category && (
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">{detailItem.caseItem.category}</p>
                )}
              </div>

              {/* Close button */}
              <button
                onClick={() => setDetailItem(null)}
                aria-label="Close analysis drawer"
                className="p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] rounded-xl transition-all cursor-pointer shrink-0 mt-0.5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Match Confidence Gauge Header */}
            {(() => {
              const percent =
                detailItem.type === 'suspect'
                  ? detailItem.suspect?.similarity_percent || 0
                  : detailItem.caseItem?.similarity_percent || 0;
              const level =
                detailItem.type === 'suspect'
                  ? detailItem.suspect?.match_level || 'low'
                  : detailItem.caseItem?.match_level || 'low';
              const conf =
                detailItem.type === 'suspect'
                  ? detailItem.suspect?.confidence || 0
                  : detailItem.caseItem?.confidence || 0;
              const theme = getMatchTheme(percent, level);

              return (
                <div className="px-5 sm:px-6 py-4 bg-[var(--bg-secondary)]/50 border-b border-[var(--border-primary)] space-y-3">
                  <div className="flex justify-between items-center">
                    <div>
                      <span className="text-sm font-bold text-[var(--text-primary)]">Analytical MO Match Score</span>
                      <p className="text-xs text-[var(--text-muted)] mt-0.5">Evaluated against real database attributes</p>
                    </div>
                    <div className="text-right">
                      <span className={`text-lg font-bold font-mono px-3 py-1 rounded-lg border ${theme.badge}`}>
                        {percent}% Match
                      </span>
                    </div>
                  </div>
                  <div className="w-full bg-[var(--bg-tertiary)] rounded-full h-2 overflow-hidden">
                    <div className={`h-full rounded-full ${theme.bar} transition-all duration-300`} style={{ width: `${percent}%` }} />
                  </div>
                  <div className="flex justify-between items-center text-xs text-[var(--text-muted)] font-mono">
                    <span>Algorithm Confidence: {Math.round(conf * 100)}%</span>
                    <span className="capitalize font-semibold">{level} Match Priority</span>
                  </div>
                </div>
              );
            })()}

            {/* Drawer Body: Scrollable Details — Spacious, Clear & High Contrast */}
            <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6 text-xs">
              {/* Section 1: Matching Factors (Clean Individual Verified Cards) */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-2 font-mono">
                    <CheckCircle2 className="w-4 h-4" /> Verified Matching Factors
                  </h4>
                  <span className="text-[11px] text-[var(--text-muted)] font-mono">
                    {(detailItem.type === 'suspect' ? detailItem.suspect?.matching_factors : detailItem.caseItem?.matching_factors)?.length || 0} factors aligned
                  </span>
                </div>

                <div className="space-y-2.5">
                  {(detailItem.type === 'suspect'
                    ? detailItem.suspect?.matching_factors
                    : detailItem.caseItem?.matching_factors
                  )?.map((factor, i) => (
                    <div
                      key={i}
                      className="p-3.5 bg-[var(--bg-secondary)] border border-emerald-900/50 hover:border-emerald-700/60 rounded-xl flex items-start gap-3 transition-all"
                    >
                      <div className="p-1 bg-emerald-950/60 border border-emerald-800/60 rounded-md text-emerald-400 shrink-0 mt-0.5">
                        <Check className="w-3.5 h-3.5" />
                      </div>
                      <span className="text-xs text-[var(--text-primary)] leading-relaxed font-medium">
                        {factor}
                      </span>
                    </div>
                  ))}

                  {(!detailItem.suspect?.matching_factors?.length && !detailItem.caseItem?.matching_factors?.length) && (
                    <div className="p-4 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl text-center text-[var(--text-muted)]">
                      No explicit matching factors identified.
                    </div>
                  )}
                </div>
              </div>

              {/* Section 2: Structured Comparative Attribute Matrix (Spacious Two-Column Grid) */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)] font-mono">
                    Comparative Attribute Matrix
                  </h4>
                  <span className="text-[11px] text-[var(--text-muted)] font-mono">Target Case vs Candidate</span>
                </div>

                <div className="border border-[var(--border-primary)] rounded-xl overflow-hidden divide-y divide-[var(--border-primary)] bg-[var(--bg-secondary)]">
                  {/* Crime Category Row */}
                  <div className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 hover:bg-[var(--bg-tertiary)]/40 transition-colors">
                    <span className="text-xs font-medium text-[var(--text-muted)] w-40 shrink-0">Crime Category</span>
                    <span className="text-xs font-semibold text-[var(--text-primary)] text-left sm:text-right">
                      {detailItem.type === 'case' ? detailItem.caseItem?.category || 'Unspecified' : targetCase?.category || 'Unspecified'}
                    </span>
                  </div>

                  {/* Jurisdiction Row */}
                  <div className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 hover:bg-[var(--bg-tertiary)]/40 transition-colors">
                    <span className="text-xs font-medium text-[var(--text-muted)] w-40 shrink-0">Jurisdiction / Station</span>
                    <span className="text-xs font-semibold text-[var(--text-primary)] text-left sm:text-right">
                      {detailItem.type === 'case'
                        ? detailItem.caseItem?.station || detailItem.caseItem?.district || 'Unspecified'
                        : targetProfile.station || targetCase?.district || 'Unspecified'}
                    </span>
                  </div>

                  {/* Operating Time Row */}
                  <div className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 hover:bg-[var(--bg-tertiary)]/40 transition-colors">
                    <span className="text-xs font-medium text-[var(--text-muted)] w-40 shrink-0">Operating Time</span>
                    <span className="text-xs font-semibold text-[var(--text-primary)] text-left sm:text-right">
                      {targetProfile.time_window || 'Unspecified'}
                    </span>
                  </div>

                  {/* Target Environment Row */}
                  <div className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 hover:bg-[var(--bg-tertiary)]/40 transition-colors">
                    <span className="text-xs font-medium text-[var(--text-muted)] w-40 shrink-0">Target Environment</span>
                    <span className="text-xs font-semibold text-[var(--text-primary)] text-left sm:text-right">
                      {targetProfile.target_type || 'General'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Section 3: Meaningful Differences (Clear Amber Breakdown) */}
              {((detailItem.type === 'suspect'
                ? detailItem.suspect?.divergent_factors
                : detailItem.caseItem?.divergent_factors
              )?.length || 0) > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-2 font-mono">
                    <XCircle className="w-4 h-4" /> Meaningful Operational Differences
                  </h4>
                  <div className="space-y-2.5">
                    {(detailItem.type === 'suspect'
                      ? detailItem.suspect?.divergent_factors
                      : detailItem.caseItem?.divergent_factors
                    )?.map((diff, i) => (
                      <div
                        key={i}
                        className="p-3.5 bg-[var(--bg-secondary)] border border-amber-900/50 hover:border-amber-700/60 rounded-xl flex items-start gap-3 transition-all"
                      >
                        <div className="p-1 bg-amber-950/60 border border-amber-800/60 rounded-md text-amber-400 shrink-0 mt-0.5">
                          <Minus className="w-3.5 h-3.5" />
                        </div>
                        <span className="text-xs text-[var(--text-primary)] leading-relaxed font-medium">
                          {diff}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Section 4: Dimensional Coverage & Completeness (Clear & Informative) */}
              {(() => {
                const unrecorded =
                  detailItem.type === 'suspect'
                    ? detailItem.suspect?.insufficient_data || []
                    : detailItem.caseItem?.insufficient_data || [];
                const totalDims = 7;
                const evaluatedDims = totalDims - unrecorded.length;
                const coveragePercent = Math.round((evaluatedDims / totalDims) * 100);

                return (
                  <div className="p-4 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl space-y-3">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <HelpCircle className="w-4 h-4 text-[#1E6FD9]" />
                        <span className="text-xs font-bold text-[var(--text-primary)] font-mono">
                          Attribute Evaluation Coverage
                        </span>
                      </div>
                      <span className="text-xs font-bold font-mono text-[#1E6FD9]">
                        {evaluatedDims}/{totalDims} Dimensions ({coveragePercent}%)
                      </span>
                    </div>

                    <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                      Similarity was calculated across all available recorded attributes.
                      {unrecorded.length > 0
                        ? ` The following dimensions were not logged in the original case/FIR records: ${unrecorded.join(', ')}.`
                        : ' All 7 investigative dimensions had complete data.'}
                    </p>
                  </div>
                );
              })()}
            </div>

            {/* Drawer Footer Actions */}
            <div className="p-4 sm:p-5 bg-[var(--bg-secondary)] border-t border-[var(--border-primary)] flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setDetailItem(null)}
                  className="px-3.5 py-2.5 bg-[var(--bg-tertiary)] hover:bg-[#1E6FD9] hover:text-white border border-[var(--border-primary)] rounded-xl text-[var(--text-primary)] font-semibold transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back</span>
                </button>

                <button
                  onClick={() => {
                    if (detailItem.type === 'suspect' && detailItem.suspect) {
                      handleRunCompare(
                        detailItem.suspect.criminal_id,
                        'criminal',
                        detailItem.suspect.full_name
                      );
                    } else if (detailItem.type === 'case' && detailItem.caseItem) {
                      handleRunCompare(
                        detailItem.caseItem.case_id,
                        'case',
                        detailItem.caseItem.case_number
                      );
                    }
                  }}
                  className="px-3.5 py-2.5 bg-[var(--bg-tertiary)] hover:bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-xl text-[var(--text-primary)] font-semibold transition-all flex items-center gap-2 cursor-pointer shadow-xs"
                >
                  <SlidersHorizontal className="w-4 h-4 text-[#1E6FD9]" />
                  <span>Deep Compare</span>
                </button>
              </div>

              <div className="flex items-center gap-2.5">
                {detailItem.type === 'suspect' && onSelectCriminal && (
                  <button
                    onClick={() => {
                      onSelectCriminal(detailItem.suspect!.criminal_id);
                      setDetailItem(null);
                    }}
                    className="px-4 py-2.5 bg-[#1E6FD9] hover:bg-[#1858ad] text-white rounded-xl font-semibold transition-all flex items-center gap-2 cursor-pointer shadow-sm"
                  >
                    <span>Open Dossier</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                )}

                {detailItem.type === 'case' && onSelectCase && (
                  <button
                    onClick={() => {
                      onSelectCase(detailItem.caseItem!.case_id);
                      setDetailItem(null);
                    }}
                    className="px-4 py-2.5 bg-[#1E6FD9] hover:bg-[#1858ad] text-white rounded-xl font-semibold transition-all flex items-center gap-2 cursor-pointer shadow-sm"
                  >
                    <span>Switch Investigation</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
