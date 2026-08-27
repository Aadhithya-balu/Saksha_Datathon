import React, { useEffect, useRef, useState } from 'react';
import {
  Search,
  ArrowLeft,
  User,
  Briefcase,
  FileText,
  MapPin,
  Landmark,
  ScanFace,
  Brain,
  Sparkles,
  MessageSquare,
  Users,
  Network,
  X,
  ChevronRight,
  Camera,
  ShieldAlert,
  Clock,
  ChevronDown,
  Link2,
  Fingerprint,
  Boxes,
} from 'lucide-react';
import {
  searchInvestigation,
  interpretInvestigationQuery,
  searchInvestigationImage,
  getCriminal,
  getCaseMOMatches,
  getCriminalMOMatches,
} from '../../services/api';
import type {
  InvestigationGroupedSearchResponse,
  InvestigationSearchItem,
  InvestigationInterpretation,
  InvestigationImageSearchResponse,
} from '../../services/api';
import PersonAvatar from '../../components/ui/PersonAvatar';
import { CardSkeleton } from '../../components/ui/Skeleton';
import { useAuthStore } from '../../store/authStore';
import type { UserRole } from '../../store/authStore';

const MO_ROLES: UserRole[] = ['ADMIN', 'SCRB', 'IO', 'SP', 'INSPECTOR'];

interface PersonProfile {
  id: string;
  full_name: string;
  aliases?: string | null;
  status?: string;
  gender?: string | null;
  date_of_birth?: string | null;
  address?: string | null;
  identifying_marks?: string | null;
  mo_summary?: string | null;
  gang_affiliation?: string | null;
  image_url?: string | null;
  firs?: any[];
  ai_recommendations?: string[];
  ai_similar?: { similar: any[] };
}

type HubView = 'landing' | 'results' | 'person' | 'case';

interface SearchGroup {
  key: keyof Pick<
    InvestigationGroupedSearchResponse,
    'persons' | 'cases' | 'firs' | 'locations' | 'stations' | 'mo_matches'
  >;
  label: string;
  icon: React.ReactNode;
  emptyLabel: string;
}

const GROUPS: SearchGroup[] = [
  { key: 'persons', label: 'PERSONS', icon: <Users className="w-3.5 h-3.5" />, emptyLabel: 'No persons found' },
  { key: 'cases', label: 'CASES', icon: <Briefcase className="w-3.5 h-3.5" />, emptyLabel: 'No cases found' },
  { key: 'firs', label: 'FIRs', icon: <FileText className="w-3.5 h-3.5" />, emptyLabel: 'No FIRs found' },
  { key: 'stations', label: 'POLICE STATIONS', icon: <Landmark className="w-3.5 h-3.5" />, emptyLabel: 'No stations found' },
  { key: 'locations', label: 'LOCATIONS', icon: <MapPin className="w-3.5 h-3.5" />, emptyLabel: 'No locations found' },
  { key: 'mo_matches', label: 'MO MATCHES', icon: <Brain className="w-3.5 h-3.5" />, emptyLabel: 'No MO matches' },
];

const QUICK_ACTIONS = [
  { label: 'Search Person', icon: <User className="w-4 h-4" />, hint: 'By name or alias' },
  { label: 'Search FIR / Case', icon: <FileText className="w-4 h-4" />, hint: 'By number' },
  { label: 'Upload Image', icon: <Camera className="w-4 h-4" />, hint: 'Suspect photo' },
  { label: 'Search MO', icon: <Brain className="w-4 h-4" />, hint: 'Modus operandi' },
  { label: 'Search Location', icon: <MapPin className="w-4 h-4" />, hint: 'District / station' },
  { label: 'Network Investigation', icon: <Network className="w-4 h-4" />, hint: 'Focus graph' },
];

interface RecentSearch {
  term: string;
  ts: number;
}

const RECENT_KEY = 'saksha_investigation_recent';

function loadRecent(): RecentSearch[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    return raw ? (JSON.parse(raw) as RecentSearch[]) : [];
  } catch {
    return [];
  }
}

const typeAccent: Record<string, string> = {
  person: '#1E6FD9',
  case: '#7c5cff',
  fir: '#14b8a6',
  station: '#f59e0b',
  location: '#22c55e',
  mo: '#a855f7',
};

const InvestigationHub: React.FC = () => {
  const user = useAuthStore((state) => state.user);
  const [view, setView] = useState<HubView>('landing');
  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const [results, setResults] = useState<InvestigationGroupedSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [recent, setRecent] = useState<RecentSearch[]>([]);

  // NL / Kannada interpretation
  const [nlOpen, setNlOpen] = useState(false);
  const [nlQuery, setNlQuery] = useState('');
  const [interpretation, setInterpretation] = useState<InvestigationInterpretation | null>(null);
  const [nlLoading, setNlLoading] = useState(false);
  const [nlError, setNlError] = useState<string | null>(null);

  // Image search
  const [imageOpen, setImageOpen] = useState(false);
  const [imageState, setImageState] = useState<InvestigationImageSearchResponse | null>(null);
  const [imageLoading, setImageLoading] = useState(false);

  // Person profile
  const [person, setPerson] = useState<PersonProfile | null>(null);
  const [personLoading, setPersonLoading] = useState(false);
  const [personMO, setPersonMO] = useState<any>(null);

  // Case details
  const [caseInfo, setCaseInfo] = useState<any>(null);
  const [caseMatches, setCaseMatches] = useState<any>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setRecent(loadRecent());
  }, []);

  // Deep-link support: an incoming navigate-tab event (e.g. from the Command
  // Center) with tab 'intelligence' and a targetId (criminal id) opens the
  // person profile directly.
  useEffect(() => {
    const onNav = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      if (detail.tab !== 'intelligence' || !detail.targetId) return;
      openPerson(String(detail.targetId));
    };
    window.addEventListener('navigate-tab', onNav);
    return () => window.removeEventListener('navigate-tab', onNav);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 350);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    if (!debounced) {
      setResults(null);
      return;
    }
    runSearch(debounced);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  const runSearch = async (term: string) => {
    setLoading(true);
    setSearchError(null);
    try {
      const res = await searchInvestigation(term, 15);
      setResults(res);
      if (res.total > 0) {
        setRecent((prev) => {
          const next = prev.filter((r) => r.term !== term);
          next.unshift({ term, ts: Date.now() });
          return next.slice(0, 10);
        });
      }
      setView('results');
      setPerson(null);
      setCaseInfo(null);
    } catch (err: any) {
      setSearchError(err?.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const submitQuick = (label: string) => {
    const map: Record<string, string> = {
      'Search Person': 'person',
      'Search FIR / Case': 'case',
      'Upload Image': 'image',
      'Search MO': 'mo',
      'Search Location': 'location',
      'Network Investigation': 'network',
    };
    const mode = map[label];
    if (mode === 'image') {
      triggerImage();
      return;
    }
    if (mode === 'mo') {
      setNlOpen(true);
      inputRef.current?.blur();
      return;
    }
    if (mode === 'network') {
      navigate('network');
      return;
    }
    // focus search with a placeholder hint
    if (inputRef.current) inputRef.current.focus();
  };

  const triggerImage = async () => {
    setImageOpen(true);
    setImageLoading(true);
    setImageState(null);
    try {
      const res = await searchInvestigationImage();
      setImageState(res);
    } catch (err: any) {
      setImageState({
        status: 'unavailable',
        message: 'Image matching service is unavailable.',
        safe_fallback: 'Search by name, FIR, case, station or other identifier instead.',
        upload_required: true,
        matches: [],
        capability: 'none',
      });
    } finally {
      setImageLoading(false);
    }
  };

  const submitNL = async () => {
    if (!nlQuery.trim()) return;
    setNlLoading(true);
    setNlError(null);
    setInterpretation(null);
    try {
      const interp = await interpretInvestigationQuery(nlQuery.trim());
      setInterpretation(interp);
      // Run the interpreted search automatically.
      setQuery(interp.search_term);
      setNlOpen(false);
    } catch (err: any) {
      setNlError(err?.message || 'Could not interpret query');
    } finally {
      setNlLoading(false);
    }
  };

  const openPerson = async (id: string) => {
    setView('person');
    setPersonLoading(true);
    setPerson(null);
    setCaseMatches(null);
    setPersonMO(null);
    try {
      const p = await getCriminal(id);
      setPerson(p as unknown as PersonProfile);
      setPersonLoading(false);
      // Fetch MO similar in background
      getCriminalMOMatches(id, 0.25, 5)
        .then((m) => setPersonMO(m))
        .catch(() => setPersonMO(null));
    } catch (err: any) {
      setPersonLoading(false);
      setSearchError(err?.message || 'Failed to load person profile');
    }
  };

  const openCase = async (id: string, fromSearch = false) => {
    setView('case');
    setCaseInfo(null);
    setCaseMatches(null);
    try {
      const c = { id, fromSearch };
      setCaseInfo(c);
      const matches = await getCaseMOMatches(id, 0.2, 5);
      setCaseMatches(matches);
    } catch (err: any) {
      setSearchError(err?.message || 'Failed to load case');
    }
  };

  const navigate = (tab: string, targetId?: string) => {
    window.dispatchEvent(
      new CustomEvent('navigate-tab', { detail: { tab, targetId } }),
    );
  };

  const openItem = (item: InvestigationSearchItem) => {
    if (item.type === 'person') {
      const id = item.meta.criminal_id || item.id.replace('criminal-', '');
      openPerson(id);
    } else if (item.type === 'case') {
      const id = item.meta.case_id || item.id.replace('case-', '');
      openCase(id);
    } else if (item.type === 'fir') {
      const cid = item.meta.case_id;
      if (cid) openCase(cid); else navigate('fir');
    } else if (item.type === 'mo') {
      const id = item.meta.doc_id || '';
      if (item.status === 'criminal') openPerson(id);
      else if (item.status === 'crime_case') openCase(id);
    } else if (item.type === 'location') {
      setQuery(item.meta.district || item.name.split(',')[0]);
    }
  };

  const canShowMO = MO_ROLES.includes(user?.role || 'VIEWER');

  const groupList = (range: number) => Array.from({ length: range });

  // ── Landing / Entry ──────────────────────────────────────────────
  const renderLanding = () => (
    <div className="min-h-[80vh] flex flex-col items-center justify-center px-2 py-8">
      <div className="w-full max-w-2xl text-center mb-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--border-primary)] bg-[var(--bg-secondary)]/60 text-[9px] font-mono text-[var(--text-muted)] uppercase tracking-wider mb-4">
          <ScanFace className="w-3.5 h-3.5 text-[#1E6FD9]" />
          KSP Officer-Centric Intelligence
        </div>
        <h1 className="text-lg sm:text-2xl font-mono font-bold text-[var(--text-primary)] uppercase tracking-wide">
          Investigation Intelligence
        </h1>
        <p className="text-[10px] sm:text-xs font-mono text-[var(--text-muted)] mt-2 max-w-lg mx-auto">
          You have a clue. Search by person, FIR, case, station, district, location, MO or
          describe it naturally — in English or Kannada.
        </p>
      </div>

      {renderSearchBar(true)}

      {(canShowMO || true) && renderQuickActions()}

      {recent.length > 0 && (
        <div className="w-full max-w-2xl mt-6">
          <div className="flex items-center gap-2 text-[9px] font-mono uppercase tracking-wider text-[var(--text-muted)] mb-2">
            <Clock className="w-3 h-3" /> Recent Investigations
          </div>
          <div className="flex flex-wrap gap-2">
            {recent.map((r) => (
              <button
                key={r.term}
                onClick={() => { setQuery(r.term); }}
                className="px-3 py-1.5 rounded border border-[var(--border-primary)] bg-[var(--bg-secondary)]/50 text-[10px] text-[var(--text-secondary)] hover:border-[#1E6FD9]/40 hover:text-[var(--text-primary)] transition-colors cursor-pointer"
              >
                {r.term}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderQuickActions = () => (
    <div className="w-full max-w-2xl mt-6">
      <div className="text-[9px] font-mono uppercase tracking-wider text-[var(--text-muted)] mb-2">Quick Actions</div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {QUICK_ACTIONS.map((qa) => (
          <button
            key={qa.label}
            onClick={() => submitQuick(qa.label)}
            className="flex flex-col items-start gap-1.5 p-3 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/50 hover:border-[#1E6FD9]/40 hover:bg-[#1E6FD9]/5 transition-all cursor-pointer text-left"
          >
            <span className="text-[#1E6FD9]">{qa.icon}</span>
            <span className="text-[10px] font-semibold text-[var(--text-primary)]">{qa.label}</span>
            <span className="text-[8.5px] font-mono text-[var(--text-muted)]">{qa.hint}</span>
          </button>
        ))}
      </div>
    </div>
  );

  const renderSearchBar = (large = false) => (
    <div className="w-full max-w-2xl">
      <div className={`relative flex items-center rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)]/70 focus-within:border-[#1E6FD9] transition-colors ${large ? 'p-2' : ''}`}>
        <Search className={`${large ? 'w-5 h-5' : 'w-4 h-4'} text-[var(--text-muted)] mx-3 shrink-0`} />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search person, FIR, case, station, district, MO… ಕನ್ನಡದಲ್ಲೂ ಹುಡುಕಿ"
          className={`flex-1 bg-transparent text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)] min-w-0 ${large ? 'text-sm py-2' : 'text-xs py-2'}`}
        />
        {query && (
          <button onClick={() => setQuery('')} className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer shrink-0" aria-label="Clear">
            <X className="w-3.5 h-3.5" />
          </button>
        )}
        <button
          onClick={() => setNlOpen(true)}
          className="hidden sm:flex items-center gap-1.5 mx-2 px-2.5 py-1.5 rounded-lg border border-[var(--border-primary)] text-[9px] font-mono uppercase tracking-wider text-[#a855f7] hover:bg-[#a855f7]/10 transition-colors cursor-pointer shrink-0"
        >
          <Sparkles className="w-3.5 h-3.5" /> Ask
        </button>
      </div>
      <div className="flex flex-wrap gap-2 mt-3 justify-center text-[8.5px] font-mono text-[var(--text-muted)]">
        <span className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] border border-[var(--border-primary)]">Person</span>
        <span className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] border border-[var(--border-primary)]">FIR</span>
        <span className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] border border-[var(--border-primary)]">Case</span>
        <span className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] border border-[var(--border-primary)]">Station</span>
        <span className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] border border-[var(--border-primary)]">MO</span>
        <span className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] border border-[var(--border-primary)] text-[#a855f7]">ಕನ್ನಡ / English</span>
      </div>
    </div>
  );

  // ── Results ──────────────────────────────────────────────────────
  const renderResults = () => {
    if (loading) {
      return (
        <div className="space-y-4">
          {groupList(3).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      );
    }
    if (searchError) {
      return (
        <div className="p-6 text-center border border-dashed border-[var(--border-primary)] rounded-lg">
          <ShieldAlert className="w-6 h-6 text-amber-400 mx-auto mb-2" />
          <p className="text-xs text-[var(--text-secondary)]">{searchError}</p>
        </div>
      );
    }
    if (!results || results.total === 0) {
      return (
        <div className="p-8 text-center border border-dashed border-[var(--border-primary)] rounded-lg">
          <Search className="w-6 h-6 text-[var(--text-muted)] mx-auto mb-2" />
          <p className="text-xs text-[var(--text-muted)] uppercase tracking-wider">
            No records found for "{query}"
          </p>
          <p className="text-[10px] text-[var(--text-muted)] mt-2">
            Person not found in available records. Try FIR, case, station, district or MO.
          </p>
        </div>
      );
    }
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setView('landing')}
            className="inline-flex items-center gap-1.5 text-[10px] font-mono uppercase text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back
          </button>
          <span className="text-[10px] font-mono text-[var(--text-muted)]">
            {results.total} result(s) for &ldquo;{results.query}&rdquo;
          </span>
        </div>

        {!results.mo_intelligence && canShowMO && (
          <div className="px-3 py-2 rounded border border-amber-500/30 bg-amber-500/5 text-[9px] font-mono text-amber-300">
            MO semantic matches are filtered for your clearance level.
          </div>
        )}

        {GROUPS.map((group) => {
          const items = results[group.key];
          if (items.length === 0) return null;
          return (
            <div key={group.key} className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 overflow-hidden">
              <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--border-primary)] bg-[var(--bg-elevated)]/40">
                <span style={{ color: typeAccent[group.key === 'mo_matches' ? 'mo' : group.key === 'persons' ? 'person' : group.key === 'cases' ? 'case' : group.key === 'firs' ? 'fir' : group.key === 'stations' ? 'station' : 'location'] }}>
                  {group.icon}
                </span>
                <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-[var(--text-primary)]">
                  {group.label}
                </span>
                <span className="ml-auto text-[8px] font-mono text-[var(--text-muted)]">{items.length}</span>
              </div>
              <div className="divide-y divide-[var(--border-primary)/50]">
                {items.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => openItem(item)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-[var(--bg-elevated)]/40 transition-colors cursor-pointer text-left"
                  >
                    {item.type === 'person' ? (
                      <PersonAvatar name={item.name} size={34} accentColor={typeAccent.person} shape="circle" />
                    ) : (
                      <span className="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
                        style={{ background: `${typeAccent[item.type === 'mo_matches' ? 'mo' : item.type]}15`, color: typeAccent[item.type === 'mo_matches' ? 'mo' : item.type] }}>
                        {group.icon}
                      </span>
                    )}
                    <div className="flex-1 min-w-0">
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
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // ── Person profile ─────────────────────────────────────────────
  const renderPerson = () => {
    if (personLoading) {
      return (
        <div className="space-y-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      );
    }
    if (!person) {
      return (
        <div className="p-8 text-center border border-dashed border-[var(--border-primary)] rounded-lg">
          <ShieldAlert className="w-6 h-6 text-amber-400 mx-auto mb-2" />
          <p className="text-xs text-[var(--text-secondary)]">Could not load person profile.</p>
        </div>
      );
    }
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => setView('results')} className="inline-flex items-center gap-1.5 text-[10px] font-mono uppercase text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer">
            <ArrowLeft className="w-3.5 h-3.5" /> Back to results
          </button>
        </div>

        {/* Header card */}
        <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <PersonAvatar name={person.full_name} imageUrl={person.image_url} size={72} accentColor={typeAccent.person} shape="circle" className="mx-auto sm:mx-0" />
            <div className="flex-1 min-w-0 text-center sm:text-left">
              <div className="flex items-center justify-center sm:justify-start gap-2 flex-wrap">
                <h2 className="text-base font-mono font-bold text-[var(--text-primary)]">{person.full_name}</h2>
                {person.status && (
                  <span className="px-2 py-0.5 rounded text-[8px] font-mono uppercase bg-[var(--bg-elevated)] border border-[var(--border-primary)] text-[var(--text-secondary)]">
                    {person.status.replace(/_/g, ' ')}
                  </span>
                )}
              </div>
              {person.aliases && (
                <div className="text-[10px] font-mono text-[var(--text-muted)] mt-1">Alias: {person.aliases}</div>
              )}
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[9px] font-mono text-[var(--text-secondary)]">
                {person.gender && <span>Gender: {person.gender}</span>}
                {person.date_of_birth && <span>DOB: {person.date_of_birth}</span>}
                {person.gang_affiliation && <span>Gang: {person.gang_affiliation}</span>}
              </div>
              <div className="flex flex-wrap gap-2 mt-3">
                <button
                  onClick={() => navigate('criminals', person.id)}
                  className="px-2.5 py-1 rounded border border-[var(--border-primary)] text-[9px] font-mono uppercase text-[#1E6FD9] hover:bg-[#1E6FD9]/10 transition-colors cursor-pointer"
                >
                  Open Dossier
                </button>
                <button
                  onClick={() => { if (person.id) navigate('network', person.id); }}
                  className="px-2.5 py-1 rounded border border-[var(--border-primary)] text-[9px] font-mono uppercase text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer"
                >
                  <span className="inline-flex items-center gap-1"><Link2 className="w-3 h-3" /> Network</span>
                </button>
              </div>
            </div>
          </div>
          {person.address && (
            <div className="mt-3 pt-3 border-t border-[var(--border-primary)] text-[9px] font-mono text-[var(--text-muted)] flex items-center gap-1.5">
              <MapPin className="w-3 h-3" /> {person.address}
            </div>
          )}
        </div>

        {/* Expandable sections */}
        {person.mo_summary && <Expandable title="MODUS OPERANDI" accent="#a855f7"><p className="text-[10px] text-[var(--text-secondary)] leading-relaxed">{person.mo_summary}</p></Expandable>}
        {person.identifying_marks && <Expandable title="IDENTIFYING MARKS" accent="#f59e0b"><p className="text-[10px] text-[var(--text-secondary)] leading-relaxed">{person.identifying_marks}</p></Expandable>}

        {person.firs && person.firs.length > 0 && (
          <Expandable title={`LINKED CASES (${person.firs.length})`} accent="#14b8a6">
            <div className="divide-y divide-[var(--border-primary)/50]">
              {person.firs.map((f: any) => (
                <div key={f.id} className="py-2 flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5 text-[#14b8a6] shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-[10px] font-semibold text-[var(--text-primary)]">{f.fir_number || f.fir_number}</div>
                    <div className="text-[8.5px] text-[var(--text-muted)]">{f.crime_case_number ? `Case ${f.crime_case_number}` : f.status || ''} · {f.sections || ''}</div>
                  </div>
                </div>
              ))}
            </div>
          </Expandable>
        )}

        {personMO && personMO.similar_criminals && personMO.similar_criminals.length > 0 && (
          <Expandable title="SIMILAR OFFENDERS (MO)" accent="#a855f7">
            <div className="divide-y divide-[var(--border-primary)/50]">
              {personMO.similar_criminals.map((s: any) => (
                <button key={s.criminal_id} onClick={() => openPerson(s.criminal_id)} className="w-full py-2 flex items-center gap-2 hover:bg-[var(--bg-elevated)]/40 rounded cursor-pointer text-left">
                  <div className="flex-1 min-w-0">
                    <div className="text-[10px] font-semibold text-[var(--text-primary)]">{s.full_name}</div>
                    <div className="text-[8.5px] text-[var(--text-muted)]">{s.match_level} similarity ({s.similarity_percent}%)</div>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                </button>
              ))}
            </div>
            <PotentialNote />
          </Expandable>
        )}

        {personMO && personMO.matching_cases && personMO.matching_cases.length > 0 && (
          <Expandable title={`POTENTIAL RELATED CASES (${personMO.matching_cases.length})`} accent="#f59e0b">
            <div className="divide-y divide-[var(--border-primary)/50]">
              {personMO.matching_cases.map((c: any) => (
                <button key={c.case_id} onClick={() => openCase(c.case_id)} className="w-full py-2 flex items-center gap-2 hover:bg-[var(--bg-elevated)]/40 rounded cursor-pointer text-left">
                  <div className="flex-1 min-w-0">
                    <div className="text-[10px] font-semibold text-[var(--text-primary)]">{c.case_number}</div>
                    <div className="text-[8.5px] text-[var(--text-muted)]">{c.category} · {c.district} · {c.match_level} ({c.similarity_percent}%)</div>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                </button>
              ))}
            </div>
            <PotentialNote />
          </Expandable>
        )}

        {(person.ai_recommendations || []).length > 0 && (
          <Expandable title="INVESTIGATION RECOMMENDATIONS" accent="#1E6FD9">
            <ul className="space-y-1.5">
              {(person.ai_recommendations || []).map((rec: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-[10px] text-[var(--text-secondary)]">
                  <span className="text-[#1E6FD9] mt-0.5">•</span> {rec}
                </li>
              ))}
            </ul>
          </Expandable>
        )}
      </div>
    );
  };

  // ── Case detail ────────────────────────────────────────────────
  const renderCase = () => {
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => setView('results')} className="inline-flex items-center gap-1.5 text-[10px] font-mono uppercase text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer">
            <ArrowLeft className="w-3.5 h-3.5" /> Back
          </button>
          <span className="text-[10px] font-mono text-[var(--text-primary)]">Case Detail</span>
        </div>

        <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 p-4">
          <div className="flex items-center gap-2">
            <Briefcase className="w-4 h-4 text-[#7c5cff]" />
            <span className="text-sm font-mono font-bold text-[var(--text-primary)]">{caseInfo?.id || 'Case'}</span>
          </div>
          <p className="text-[10px] text-[var(--text-muted)] mt-1">
            Investigating similar cases and possible connections…
          </p>
          <div className="flex flex-wrap gap-2 mt-3">
            <button onClick={() => navigate('crime_cases', caseInfo?.id)} className="px-2.5 py-1 rounded border border-[var(--border-primary)] text-[9px] font-mono uppercase text-[#7c5cff] hover:bg-[#7c5cff]/10 transition-colors cursor-pointer">
              Open Case
            </button>
            <button onClick={() => navigate('investigation', caseInfo?.id)} className="px-2.5 py-1 rounded border border-[var(--border-primary)] text-[9px] font-mono uppercase text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer">
              Investigation
            </button>
          </div>
        </div>

        {!caseMatches ? (
          <CardSkeleton />
        ) : caseMatches.error ? (
          <div className="p-6 text-center border border-dashed border-[var(--border-primary)] rounded-lg">
            <p className="text-xs text-amber-300">{caseMatches.error}</p>
          </div>
        ) : (
          <>
            {caseMatches.matching_cases && caseMatches.matching_cases.length > 0 ? (
              <Expandable title={`SIMILAR CASES (${caseMatches.matching_cases.length})`} accent="#f59e0b">
                <div className="divide-y divide-[var(--border-primary)/50]">
                  {caseMatches.matching_cases.map((c: any) => (
                    <div key={c.case_id} className="py-2.5">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px] font-semibold text-[var(--text-primary)]">{c.case_number}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[7.5px] font-mono uppercase ${
                          c.match_level === 'high' ? 'bg-red-950/40 text-red-400 border border-red-900/40'
                          : c.match_level === 'medium' ? 'bg-orange-950/40 text-orange-400 border border-orange-900/40'
                          : 'bg-yellow-950/40 text-yellow-400 border border-yellow-900/40'
                        }`}>{c.match_level}</span>
                      </div>
                      <div className="text-[9px] font-mono text-[var(--text-muted)] mt-0.5">{c.category} · {c.district} · {c.similarity_percent}% similarity</div>
                      {c.matching_factors && c.matching_factors.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {c.matching_factors.slice(0, 4).map((f: string, i: number) => (
                            <span key={i} className="px-1.5 py-0.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-primary)] text-[7.5px] font-mono text-[#22c55e]">{f}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <PotentialNote />
              </Expandable>
            ) : (
              <div className="p-4 text-center border border-dashed border-[var(--border-primary)] rounded-lg">
                <p className="text-[10px] text-[var(--text-muted)]">No sufficiently similar cases found in the database.</p>
              </div>
            )}

            {caseMatches.matching_suspects && caseMatches.matching_suspects.length > 0 && (
              <Expandable title={`POTENTIAL SUSPECTS (${caseMatches.matching_suspects.length})`} accent="#a855f7">
                <div className="divide-y divide-[var(--border-primary)/50]">
                  {caseMatches.matching_suspects.map((s: any) => (
                    <button key={s.criminal_id} onClick={() => openPerson(s.criminal_id)} className="w-full py-2 flex items-center gap-2 hover:bg-[var(--bg-elevated)]/40 rounded cursor-pointer text-left">
                      <div className="flex-1 min-w-0">
                        <div className="text-[10px] font-semibold text-[var(--text-primary)]">{s.full_name}</div>
                        <div className="text-[8.5px] text-[var(--text-muted)]">{s.match_level} · {s.similarity_percent}% · {s.gang_affiliation || 'no gang'}</div>
                      </div>
                      <ChevronRight className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                    </button>
                  ))}
                </div>
                <PotentialNote />
              </Expandable>
            )}
          </>
        )}

        {caseInfo && caseInfo.fromSearch && (
          <div className="text-[9px] font-mono text-[var(--text-muted)] flex items-center gap-1.5">
            <ShieldAlert className="w-3 h-3 text-amber-400" />
            Use "Open Case" for full case detail, timeline and evidence.
          </div>
        )}
      </div>
    );
  };

  const renderBody = () => {
    switch (view) {
      case 'results': return renderResults();
      case 'person': return renderPerson();
      case 'case': return renderCase();
      default: return renderLanding();
    }
  };

  return (
    <div className="min-h-[84vh] pb-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-[var(--border-muted)] pb-3 mb-4">
        <div>
          <h2 className="text-md font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
            <Fingerprint className="w-5 h-5 text-[#1E6FD9]" />
            Investigation Hub
          </h2>
          <p className="text-[9.5px] font-mono text-[var(--text-muted)] mt-0.5">
            UNIFIED ENTRY POINT — SEARCH / IMAGE / NATURAL QUERY → PERSON → CASES → MO → CONNECTIONS
          </p>
        </div>
        <button
          onClick={() => setNlOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#a855f7]/40 text-[9px] font-mono uppercase tracking-wider text-[#a855f7] hover:bg-[#a855f7]/10 transition-colors cursor-pointer"
        >
          <Sparkles className="w-3.5 h-3.5" /> Ask AI / ಕನ್ನಡ
        </button>
      </div>

      {/* Search bar always visible when in non-landing states */}
      {view !== 'landing' && <div className="mb-4">{renderSearchBar(false)}</div>}

      {renderBody()}

      {/* NL / Kannada Query Modal */}
      {nlOpen && (
        <NlModal
          onClose={() => setNlOpen(false)}
          onSubmit={submitNL}
          loading={nlLoading}
          error={nlError}
          value={nlQuery}
          setValue={setNlQuery}
          interpretation={interpretation}
          setInterpretation={setInterpretation}
        />
      )}

      {/* Image Search Modal */}
      {imageOpen && (
        <ImageModal
          onClose={() => setImageOpen(false)}
          loading={imageLoading}
          state={imageState}
        />
      )}
    </div>
  );
};

const Expandable: React.FC<{ title: string; accent?: string; children: React.ReactNode }> = ({ title, accent = '#1E6FD9', children }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-[var(--bg-elevated)]/30 transition-colors cursor-pointer text-left"
      >
        <span style={{ color: accent }}><ChevronDown className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`} /></span>
        <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-[var(--text-primary)]">{title}</span>
      </button>
      {open && <div className="px-4 pb-4 pt-1 border-t border-[var(--border-primary)]">{children}</div>}
    </div>
  );
};

const PotentialNote: React.FC = () => (
  <p className="mt-2 text-[8.5px] font-mono text-[var(--text-muted)] flex items-start gap-1">
    <ShieldAlert className="w-3 h-3 shrink-0 text-amber-400 mt-0.5" />
    Potential connection / similar pattern detected. Requires verification. Similarity does not prove guilt or a confirmed criminal association.
  </p>
);

const NlModal: React.FC<{
  onClose: () => void;
  onSubmit: () => void;
  loading: boolean;
  error: string | null;
  value: string;
  setValue: (v: string) => void;
  interpretation: InvestigationInterpretation | null;
  setInterpretation: (v: InvestigationInterpretation | null) => void;
}> = ({ onClose, onSubmit, loading, error, value, setValue, interpretation, setInterpretation }) => {
  const examples = [
    'Find murders in Bengaluru Urban involving a cut to the neck',
    'Show cases similar to this murder',
    'Find criminals connected to this FIR',
    'ಬೆಂಗಳೂರು ಅರ್ಬನ್‌ನಲ್ಲಿ ಕುತ್ತಿಗೆ ಕತ್ತರಿಸಿ ನಡೆದ ಕೊಲೆ ಪ್ರಕರಣಗಳನ್ನು ತೋರಿಸಿ',
    'Kempegowda Nagar station alli similar cases yavudu?',
  ];
  return (
    <div className="fixed inset-0 z-[400] flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full sm:max-w-lg max-h-[85vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl border border-[var(--border-primary)] bg-[var(--bg-elevated)] p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-[#a855f7]" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-[var(--text-primary)]">Natural-Language / ಕನ್ನಡ Query</span>
          </div>
          <button onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer" aria-label="Close"><X className="w-4 h-4" /></button>
        </div>

        <textarea
          value={value}
          onChange={(e) => { setValue(e.target.value); setInterpretation(null); }}
          rows={3}
          placeholder="Describe what you know… English / ಕನ್ನಡ / Mixed"
          className="w-full p-3 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] text-[var(--text-primary)] text-xs outline-none focus:border-[#a855f7] placeholder:text-[var(--text-muted)] resize-none"
        />
        {error && <p className="text-[9px] font-mono text-amber-400 mt-1">{error}</p>}

        {interpretation && (
          <div className="mt-3 p-3 rounded-lg border border-[#a855f7]/30 bg-[#a855f7]/5">
            <div className="text-[8.5px] font-mono uppercase text-[#a855f7] mb-1">Interpreted ({interpretation.detected_language}) · {interpretation.confidence} confidence</div>
            <div className="flex flex-wrap gap-1.5">
              {interpretation.person_name && <Chip label={`Person: ${interpretation.person_name}`} />}
              {interpretation.case_number && <Chip label={`Case: ${interpretation.case_number}`} />}
              {interpretation.fir_number && <Chip label={`FIR: ${interpretation.fir_number}`} />}
              {interpretation.district && <Chip label={`District: ${interpretation.district}`} />}
              {interpretation.station && <Chip label={`Station: ${interpretation.station}`} />}
              {interpretation.crime_type && <Chip label={`Crime: ${interpretation.crime_type}`} />}
              {interpretation.mo_keywords.map((k, i) => <Chip key={i} label={`MO: ${k}`} />)}
              {interpretation.date_range_days && <Chip label={`Last ${interpretation.date_range_days}d`} />}
            </div>
            {interpretation.notes.map((n, i) => <p key={i} className="text-[8.5px] text-amber-300 mt-1">{n}</p>)}
            <button onClick={onSubmit} className="mt-2 inline-flex items-center gap-1.5 text-[9px] font-mono uppercase text-[#a855f7] hover:underline cursor-pointer">
              <Search className="w-3 h-3" /> Search interpreted query
            </button>
          </div>
        )}

        <div className="mt-3">
          <div className="text-[8.5px] font-mono uppercase text-[var(--text-muted)] mb-1.5">Examples</div>
          <div className="flex flex-col gap-1">
            {examples.map((ex) => (
              <button key={ex} onClick={() => { setValue(ex); setInterpretation(null); }} className="text-left text-[9.5px] font-mono text-[var(--text-secondary)] hover:text-[#a855f7] transition-colors cursor-pointer px-2 py-1 rounded hover:bg-[#a855f7]/5">
                {ex}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={onSubmit}
          disabled={loading || !value.trim()}
          className="mt-4 w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#a855f7] text-[var(--text-primary)] text-xs font-semibold hover:opacity-90 disabled:opacity-40 transition-opacity cursor-pointer"
        >
          {loading ? 'Interpreting…' : <>
            <MessageSquare className="w-3.5 h-3.5" /> Interpret & Search
          </>}
        </button>

        <p className="mt-3 text-[8.5px] font-mono text-[var(--text-muted)] flex items-start gap-1">
          <ShieldAlert className="w-3 h-3 shrink-0 text-amber-400 mt-0.5" />
          Every result comes from the authorized database. If insufficient evidence exists, the system will say so — it never invents records.
        </p>
      </div>
    </div>
  );
};

const Chip: React.FC<{ label: string }> = ({ label }) => (
  <span className="px-1.5 py-0.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-primary)] text-[8px] font-mono text-[var(--text-secondary)]">{label}</span>
);

const ImageModal: React.FC<{
  onClose: () => void;
  loading: boolean;
  state: InvestigationImageSearchResponse | null;
}> = ({ onClose, loading, state }) => {
  const [file, setFile] = useState<File | null>(null);
  return (
    <div className="fixed inset-0 z-[400] flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full sm:max-w-lg max-h-[85vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl border border-[var(--border-primary)] bg-[var(--bg-elevated)] p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Camera className="w-4 h-4 text-[#1E6FD9]" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-[var(--text-primary)]">Image Investigation</span>
          </div>
          <button onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer" aria-label="Close"><X className="w-4 h-4" /></button>
        </div>

        {loading ? (
          <div className="py-10 text-center">
            <div className="w-10 h-10 mx-auto mb-3 border-2 border-[#1E6FD9] border-t-transparent rounded-full animate-spin" />
            <p className="text-[10px] font-mono text-[var(--text-muted)]">Checking image matching capability…</p>
          </div>
        ) : (
          <>
            <div className="rounded-lg border border-dashed border-[var(--border-primary)] p-6 text-center">
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="hidden"
                id="invest-image"
              />
              <label htmlFor="invest-image" className="cursor-pointer inline-flex flex-col items-center gap-2">
                <Boxes className="w-8 h-8 text-[var(--text-muted)]" />
                <span className="text-[10px] text-[var(--text-secondary)]">Tap to select a suspect photo</span>
                {file && <span className="text-[9px] text-[#1E6FD9]">{file.name}</span>}
              </label>
            </div>

            {state && (
              <div className="mt-4 p-3 rounded-lg border border-amber-500/30 bg-amber-500/5">
                <div className="flex items-center gap-2 text-amber-300">
                  <ShieldAlert className="w-4 h-4" />
                  <span className="text-[10px] font-mono font-bold uppercase">{state.status}</span>
                </div>
                <p className="text-[10px] text-[var(--text-secondary)] mt-2 leading-relaxed">{state.message}</p>
                <p className="text-[9px] font-mono text-[var(--text-muted)] mt-2">{state.safe_fallback}</p>
              </div>
            )}

            {file && (
              <button
                onClick={() => alert('Image matching is unavailable (honest fallback). Search by name or identifier instead.')}
                className="mt-4 w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#1E6FD9] text-[var(--text-primary)] text-xs font-semibold hover:opacity-90 transition-opacity cursor-pointer"
              >
                <ScanFace className="w-3.5 h-3.5" /> Attempt Matching
              </button>
            )}

            <div className="flex flex-wrap gap-1.5 mt-3">
              <span className="px-2 py-1 rounded bg-[var(--bg-tertiary)] border border-[var(--border-primary)] text-[8px] font-mono text-[var(--text-muted)]">Safe fallback: search by name</span>
              <span className="px-2 py-1 rounded bg-[var(--bg-tertiary)] border border-[var(--border-primary)] text-[8px] font-mono text-[var(--text-muted)]">FIR / case number</span>
              <span className="px-2 py-1 rounded bg-[var(--bg-tertiary)] border border-[var(--border-primary)] text-[8px] font-mono text-[var(--text-muted)]">station / district</span>
            </div>

            <p className="mt-3 text-[8.5px] font-mono text-[var(--text-muted)] flex items-start gap-1">
              <ShieldAlert className="w-3 h-3 shrink-0 text-amber-400 mt-0.5" />
              The UI will never claim "100% match". Identity is verified only through the authorized person records workflow.
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default InvestigationHub;
