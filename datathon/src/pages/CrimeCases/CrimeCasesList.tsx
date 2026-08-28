import React, { useEffect, useState } from 'react';
import {
  getCrimeCases,
  getCrimeCaseInsights,
  deleteCrimeCase,
  getCrimeCategories,
  getLocationsList,
} from '../../services/api';
import type { CrimeCaseDetailRecord, CrimeCaseInsights } from '../../services/api';
import { Search, Plus, Eye, Edit2, Trash2, ShieldAlert } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useRealtimeStore } from '../../store/realtimeStore';
import CrimeInsightsBar from '../../components/crimeCases/CrimeInsightsBar';

interface CrimeCasesListProps {
  onSelectCase: (id: string) => void;
  onCreateCase: () => void;
  onEditCase: (id: string) => void;
}

const CrimeCasesList: React.FC<CrimeCasesListProps> = ({
  onSelectCase,
  onCreateCase,
  onEditCase
}) => {
  const user = useAuthStore((state) => state.user);
  const [cases, setCases] = useState<CrimeCaseDetailRecord[]>([]);
  const [categories, setCategories] = useState<Array<{ id: string; name: string }>>([]);
  const [districts, setDistricts] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [districtFilter, setDistrictFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [insights, setInsights] = useState<CrimeCaseInsights | null>(null);

  const fetchInsights = async () => {
    try {
      const result = await getCrimeCaseInsights({
        status: statusFilter || undefined,
        category_id: categoryFilter || undefined,
        district: districtFilter || undefined,
        priority: priorityFilter || undefined,
      });
      setInsights(result);
    } catch {
      setInsights(null);
    }
  };

  const fetchCases = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCrimeCases(search || undefined, statusFilter || undefined, 1, 20, {
        category_id: categoryFilter || undefined,
        district: districtFilter || undefined,
        priority: priorityFilter || undefined,
      });
      setCases(response.results);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch crime cases');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
    fetchInsights();
  }, [search, statusFilter, categoryFilter, districtFilter, priorityFilter]);

  // Load filter dropdown options once
  useEffect(() => {
    getCrimeCategories()
      .then(setCategories)
      .catch(() => {});
    getLocationsList()
      .then((locations) =>
        setDistricts(Array.from(new Set(locations.map((loc) => loc.district))).sort()),
      )
      .catch(() => {});
  }, []);

  // Real-time feed: newly created cases appear at the top instantly.
  useEffect(() => {
    useRealtimeStore.getState().connect();
    const unsubscribe = useRealtimeStore.getState().onCaseCreated((liveCase) => {
      if (search || (statusFilter && statusFilter !== liveCase.status)) return;
      setCases((prev) => [
        {
          id: liveCase.id || '',
          case_number: liveCase.case_number,
          category_id: '',
          location_id: '',
          occurred_at: liveCase.time || new Date().toISOString(),
          reported_at: new Date().toISOString(),
          description: `Newly registered ${liveCase.crime_type} case at ${liveCase.location}`,
          mo_tags: null,
          status: liveCase.status,
          priority: liveCase.priority,
          progress: 0,
        } as unknown as CrimeCaseDetailRecord,
        ...prev.filter((c) => c.case_number !== liveCase.case_number),
      ].slice(0, 20));
      fetchInsights();
    });
    return () => {
      unsubscribe();
      useRealtimeStore.getState().disconnect();
    };
  }, [search, statusFilter]);

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this crime case?')) return;
    try {
      await deleteCrimeCase(id);
      fetchCases();
      fetchInsights();
    } catch (err: any) {
      alert(err?.message || 'Failed to delete case');
    }
  };

  const getStatusStyle = (status: string) => {
    switch (status.toLowerCase()) {
      case 'open':
        return 'bg-blue-500/10 text-blue-400 border border-blue-500/30';
      case 'assigned':
        return 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30';
      case 'investigating':
        return 'bg-purple-500/10 text-purple-400 border border-purple-500/30';
      case 'evidence collected':
        return 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30';
      case 'charge sheet filed':
        return 'bg-orange-500/10 text-orange-400 border border-orange-500/30';
      case 'closed':
        return 'bg-[#0E9E78]/10 text-[#0E9E78] border border-[#0E9E78]/30';
      default:
        return 'bg-[var(--bg-tertiary)] text-[var(--text-muted)] border border-[var(--border-secondary)]/30';
    }
  };

  const getPriorityStyle = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'low':
        return 'bg-[var(--bg-tertiary)] text-[var(--text-muted)] border border-[var(--border-secondary)]/20';
      case 'medium':
        return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
      case 'high':
        return 'bg-orange-500/10 text-orange-400 border border-orange-500/30';
      case 'critical':
        return 'bg-[#C94A2A]/15 text-[#C94A2A] border border-[#C94A2A]/40 font-bold';
      default:
        return 'bg-[var(--bg-tertiary)] text-[var(--text-muted)] border border-[var(--border-secondary)]/20';
    }
  };
  const formatCaseDate = (dateStr: string | null | undefined): string => {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header telemetry area */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 p-5 bg-secondary-bg border border-border-color rounded-card shadow-glow-blue/5">
        <div>
          <h2 className="text-sm uppercase tracking-[0.2em] font-bold text-[var(--text-primary)]">SAKSHA Crime Intelligence Cases</h2>
          <p className="text-[10px] text-[var(--text-muted)] mt-1">OPERATOR SYSTEM PROFILE CLEARANCE LEVEL: {user?.role}</p>
        </div>
        <button
          onClick={onCreateCase}
          className="flex items-center gap-2 px-4 py-2 bg-[#1E6FD9] hover:bg-[#1E6FD9]/80 transition-colors rounded text-xs text-[var(--text-primary)] cursor-pointer uppercase font-semibold"
        >
          <Plus className="w-4 h-4" /> Create Crime Case
        </button>
      </div>

      {/* Visual Crime Telemetry & Insights Ribbon */}
      <CrimeInsightsBar
        insights={insights}
        activeStatus={statusFilter}
        activePriority={priorityFilter}
        onSelectStatus={(s) => setStatusFilter(s)}
        onSelectPriority={(p) => setPriorityFilter(p)}
        onResetFilters={() => {
          setSearch('');
          setStatusFilter('');
          setCategoryFilter('');
          setDistrictFilter('');
          setPriorityFilter('');
        }}
      />

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="SEARCH BY CASE NUMBER (E.G. 5537), DESCRIPTION..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-secondary-bg border border-border-color rounded font-mono text-xs text-[var(--text-primary)] uppercase placeholder-[var(--text-muted)] focus:border-[#1E6FD9]/60 focus:outline-none"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="w-full md:w-44 px-3 py-2 bg-secondary-bg border border-border-color rounded font-mono text-xs text-[var(--text-primary)] focus:border-[#1E6FD9]/60 focus:outline-none cursor-pointer"
        >
          <option value="">ALL STATUS LEVELS</option>
          <option value="open">OPEN</option>
          <option value="assigned">ASSIGNED</option>
          <option value="investigating">INVESTIGATING</option>
          <option value="evidence collected">EVIDENCE COLLECTED</option>
          <option value="charge sheet filed">CHARGE SHEET FILED</option>
          <option value="closed">CLOSED</option>
        </select>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="w-full md:w-48 px-3 py-2 bg-secondary-bg border border-border-color rounded font-mono text-xs text-[var(--text-primary)] focus:border-[#1E6FD9]/60 focus:outline-none cursor-pointer"
        >
          <option value="">ALL CATEGORIES</option>
          {categories.map((cat) => (
            <option key={cat.id} value={cat.id}>{cat.name.toUpperCase()}</option>
          ))}
        </select>
        <select
          value={districtFilter}
          onChange={(e) => setDistrictFilter(e.target.value)}
          className="w-full md:w-44 px-3 py-2 bg-secondary-bg border border-border-color rounded font-mono text-xs text-[var(--text-primary)] focus:border-[#1E6FD9]/60 focus:outline-none cursor-pointer"
        >
          <option value="">ALL DISTRICTS</option>
          {districts.map((dist) => (
            <option key={dist} value={dist}>{dist.toUpperCase()}</option>
          ))}
        </select>
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="w-full md:w-40 px-3 py-2 bg-secondary-bg border border-border-color rounded font-mono text-xs text-[var(--text-primary)] focus:border-[#1E6FD9]/60 focus:outline-none cursor-pointer"
        >
          <option value="">ALL PRIORITIES</option>
          <option value="low">LOW</option>
          <option value="medium">MEDIUM</option>
          <option value="high">HIGH</option>
          <option value="critical">CRITICAL</option>
        </select>
        {(search || statusFilter || categoryFilter || districtFilter || priorityFilter) && (
          <button
            onClick={() => {
              setSearch('');
              setStatusFilter('');
              setCategoryFilter('');
              setDistrictFilter('');
              setPriorityFilter('');
            }}
            className="px-4 py-2 bg-secondary-bg border border-border-color rounded font-mono text-xs text-[var(--text-muted)] hover:text-[#1E6FD9] hover:border-[#1E6FD9]/60 transition-colors uppercase cursor-pointer"
          >
            Reset
          </button>
        )}
      </div>

      {/* Main Grid View */}
      {loading ? (
        <div className="min-h-[40vh] flex items-center justify-center">
          <div className="w-8 h-8 rounded-full border-2 border-[#1E6FD9] border-t-transparent animate-spin" />
        </div>
      ) : error ? (
        <div className="p-5 border border-[#C94A2A]/20 bg-[#C94A2A]/5 text-[#C94A2A] rounded-card text-xs flex items-center gap-3">
          <ShieldAlert className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : cases.length === 0 ? (
        <div className="p-8 border border-border-color bg-secondary-bg rounded-card text-center text-xs text-[var(--text-muted)]">
          NO ACTIVE CRIME CASES ENROLLED MATCHING CURRENT TELEMETRY FILTERS
        </div>
      ) : (
        <div className="border border-border-color rounded-card overflow-hidden bg-secondary-bg">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse font-mono text-xs text-left">
              <thead>
                <tr className="border-b border-border-color bg-[var(--bg-secondary)]/40 text-[var(--text-muted)] uppercase select-none">
                  <th className="p-4">Case Details</th>
                  <th className="p-4">Occurred At</th>
                  <th className="p-4 text-center">Status</th>
                  <th className="p-4 text-center">Priority</th>
                  <th className="p-4">Progress Tracker</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-color/65">
                {cases.map((c) => (
                   <tr key={c.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors group">
                    <td className="p-4">
                      <div className="font-bold text-[var(--text-primary)] group-hover:text-[var(--text-primary)] uppercase">
                        {c.case_number}
                      </div>
                      <div className="text-[10px] text-[var(--text-muted)] mt-1 line-clamp-1 max-w-sm">
                        {c.description || 'No description provided'}
                      </div>
                    </td>
                    <td className="p-4 text-[var(--text-secondary)]">
                      {formatCaseDate(c.occurred_at)}
                    </td>
                    <td className="p-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider ${getStatusStyle(c.status)}`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] uppercase tracking-wider ${getPriorityStyle(c.priority)}`}>
                        {c.priority}
                      </span>
                    </td>
                    <td className="p-4 min-w-[150px]">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-[var(--bg-tertiary)] rounded-full overflow-hidden border border-[var(--border-primary)]">
                          <div
                            className="h-full bg-gradient-to-r from-[#1E6FD9] to-[#0E9E78] transition-all duration-500"
                            style={{ width: `${c.progress}%` }}
                          />
                        </div>
                        <span className="text-[10px] font-bold text-[var(--text-primary)] shrink-0">
                          {c.progress}%
                        </span>
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center justify-end gap-2.5">
                        <button
                          onClick={() => onSelectCase(c.id)}
                          title="View Case Dossier"
                          className="p-1.5 hover:bg-[#1E6FD9]/15 border border-border-color rounded text-[var(--text-secondary)] hover:text-[#1E6FD9] transition-colors cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => onEditCase(c.id)}
                          title="Edit Configuration"
                          className="p-1.5 hover:bg-[#0E9E78]/15 border border-border-color rounded text-[var(--text-secondary)] hover:text-[#0E9E78] transition-colors cursor-pointer"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        {user?.role === 'SCRB' && (
                          <button
                            onClick={() => handleDelete(c.id)}
                            title="Purge Case Record"
                            className="p-1.5 hover:bg-[#C94A2A]/15 border border-border-color rounded text-[var(--text-secondary)] hover:text-[#C94A2A] transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default CrimeCasesList;
