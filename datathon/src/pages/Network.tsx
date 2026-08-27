import React, { useEffect, useState, useCallback, useRef } from 'react';
import CriminalGraph3D from '../components/network/CriminalGraph3D';
import type { GraphNode, GraphLink } from '../components/network/CriminalGraph3D';
import NodeDetailPanel from '../components/network/NodeDetailPanel';
import EdgeDetailPanel from '../components/network/EdgeDetailPanel';
import { 
  Share2, 
  Network as NetIcon, 
  Layers, 
  Database, 
  Filter, 
  ShieldCheck, 
  GitCommit, 
  Globe,
  AlertTriangle,
  BarChart3,
  Info,
  Search,
  X,
  User,
  MapPin,
  FileText,
  Shield,
  ChevronDown,
  Loader2,
  Focus,
  RefreshCw
} from 'lucide-react';
import { downloadSecureDossier } from '../utils/downloader';
import { useAuditStore } from '../store/auditStore';
import { useAuthStore } from '../store/authStore';
import { getFullNetworkGraph, getNetworkPerson, getNetworkCase, searchNetworkEntities } from '../services/api';
import type { ProvenanceSummary, NetworkSearchResult } from '../services/api';

const TYPE_ICONS: Record<string, React.ReactNode> = {
  criminal: <User className="w-3 h-3 text-[var(--accent-coral)]" />,
  victim: <User className="w-3 h-3 text-[var(--accent-amber)]" />,
  officer: <Shield className="w-3 h-3 text-[var(--accent-teal)]" />,
  case: <FileText className="w-3 h-3 text-[var(--accent-blue)]" />,
  location: <MapPin className="w-3 h-3 text-[var(--accent-purple)]" />,
};

const TYPE_COLORS: Record<string, string> = {
  criminal: 'var(--accent-coral)',
  victim: 'var(--accent-amber)',
  officer: 'var(--accent-teal)',
  case: 'var(--accent-blue)',
  location: 'var(--accent-purple)',
};

export const Network: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedLink, setSelectedLink] = useState<GraphLink | null>(null);
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: GraphLink[] } | null>(null);
  const [provenanceSummary, setProvenanceSummary] = useState<ProvenanceSummary | null>(null);
  const [entityCounts, setEntityCounts] = useState<Record<string, number>>({});
  const [graphWarnings, setGraphWarnings] = useState<string[]>([]);
  const [confidenceSummary, setConfidenceSummary] = useState<Record<string, number>>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  
  const [viewScope, setViewScope] = useState<'person' | 'full'>('full');
  const [provenanceFilter, setProvenanceFilter] = useState<string>('ALL');
  const [excludeDemo, setExcludeDemo] = useState<boolean>(false);
  const [graphDepth, setGraphDepth] = useState<number>(1);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<NetworkSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [focusedEntity, setFocusedEntity] = useState<NetworkSearchResult | null>(null);
  const [focusing, setFocusing] = useState(false);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);

  const { user } = useAuthStore();
  const { addLog } = useAuditStore();

  const applyResponse = useCallback((response: any) => {
    setGraphData({ nodes: response.nodes, links: response.edges });
    if (response.provenance_summary) setProvenanceSummary(response.provenance_summary);
    if (response.entity_counts) setEntityCounts(response.entity_counts);
    if (response.warnings) setGraphWarnings(response.warnings);
    if (response.confidence_summary) setConfidenceSummary(response.confidence_summary);
    setLoadError(null);
  }, []);

  const fetchFocusedGraph = useCallback(async (entity: NetworkSearchResult, depth: number) => {
    setLoadError(null);
    setFocusing(true);
    try {
      let response;
      if (entity.type === 'criminal' || entity.type === 'victim' || entity.type === 'officer') {
        response = await getNetworkPerson(entity.id, depth, provenanceFilter === 'ALL' ? undefined : provenanceFilter, excludeDemo);
      } else if (entity.type === 'case') {
        response = await getNetworkCase(entity.id, provenanceFilter === 'ALL' ? undefined : provenanceFilter, excludeDemo);
      } else {
        response = await getFullNetworkGraph(undefined, undefined, provenanceFilter === 'ALL' ? undefined : provenanceFilter, excludeDemo);
      }
      applyResponse(response);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Failed to load focused graph');
    } finally {
      setFocusing(false);
    }
  }, [provenanceFilter, excludeDemo, applyResponse]);

  const fetchGraph = useCallback(() => {
    let isMounted = true;
    const filterArg = provenanceFilter === 'ALL' ? undefined : provenanceFilter;

    if (focusedEntity) {
      fetchFocusedGraph(focusedEntity, graphDepth);
      return () => { isMounted = false; };
    }

    const request = viewScope === 'person' 
      ? getNetworkPerson(user?.badgeId ?? 'SCRB-7740', graphDepth, filterArg, excludeDemo)
      : getFullNetworkGraph(undefined, undefined, filterArg, excludeDemo);

    request
      .then((response) => { if (isMounted) applyResponse(response); })
      .catch((error) => {
        if (isMounted) {
          setLoadError(error instanceof Error ? error.message : 'Failed to load network data');
          setGraphData(null);
        }
      });

    return () => { isMounted = false; };
  }, [user?.badgeId, viewScope, provenanceFilter, excludeDemo, graphDepth, focusedEntity, fetchFocusedGraph, applyResponse]);

  useEffect(() => { return fetchGraph(); }, [fetchGraph]);

  useEffect(() => {
    if (searchQuery.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await searchNetworkEntities(searchQuery.trim());
        setSearchResults(res.results);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => { if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current); };
  }, [searchQuery]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) setShowSearch(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleSelectSearchResult = (result: NetworkSearchResult) => {
    setFocusedEntity(result);
    setSearchQuery(result.name);
    setShowSearch(false);
    setSearchResults([]);
    setGraphDepth(1);
    setViewScope('full');
    fetchFocusedGraph(result, 1);
    if (user) {
      addLog(user.name, user.badgeId, 'SEARCH', `Focused graph on ${result.type}: ${result.name}`);
    }
  };

  const handleExpandNetwork = () => {
    const newDepth = Math.min(graphDepth + 1, 4);
    setGraphDepth(newDepth);
    if (focusedEntity) {
      fetchFocusedGraph(focusedEntity, newDepth);
    }
  };

  const handleResetView = () => {
    setFocusedEntity(null);
    setGraphDepth(1);
    setSearchQuery('');
    setViewScope('full');
  };

  const handleNodeSelect = (node: GraphNode) => { setSelectedNode(node); setSelectedLink(null); };
  const handleLinkSelect = (link: GraphLink) => { setSelectedLink(link); setSelectedNode(null); };

  const handleExportMatrix = () => {
    const matrixData = {
      relationType: 'Criminal Link Association Matrix',
      totalNodes: graphData?.nodes.length ?? 0,
      totalEdges: graphData?.links.length ?? 0,
      provenanceSummary: provenanceSummary,
      activeSuspects: graphData?.nodes.filter((node) => node.category === 'suspect').map((node) => node.name) ?? [],
      relationEdges: graphData?.links.map((link) => ({
        from: typeof link.source === 'object' ? (link.source as any).id : link.source,
        to: typeof link.target === 'object' ? (link.target as any).id : link.target,
        relation: link.relationship,
        provenance: link.provenance,
        status: link.verification_status,
        confidence: link.confidence,
      })) ?? []
    };
    downloadSecureDossier('Suspect Connection Matrix', matrixData, user ? `CONFIDENTIAL - ${user.badgeId}` : 'CONFIDENTIAL - STATE POLICE');
    if (user) addLog(user.name, user.badgeId, 'EXPORT', 'Exported suspect relationship matrix (JSON)');
  };

  return (
    <div className="flex flex-col gap-3 p-1 md:p-3 select-none bg-[var(--bg-primary)]" style={{ minHeight: '86vh', height: 'auto' }}>
      
      {/* Title Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 border-b border-[var(--border-muted)] pb-2.5">
        <div>
          <h2 className="text-md font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
            <NetIcon className="w-5 h-5 text-[#6C43CC] animate-pulse" />
            Crime Association Net Analysis
          </h2>
          <p className="text-[9.5px] font-mono text-[var(--text-muted)] mt-0.5">
            SEARCH • SELECT • FOCUS • INSPECT • EXPAND
          </p>
          {loadError && <p className="mt-1 text-[9px] font-mono text-amber-400 uppercase tracking-wider">{loadError}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[9px] font-mono uppercase">
          <button onClick={handleExportMatrix}
            className="px-2.5 py-1.5 bg-[var(--bg-tertiary)] hover:bg-[#1E6FD9]/15 border border-[#1e6fd9]/25 hover:border-[#1E6FD9]/50 text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-btn transition-colors cursor-pointer flex items-center gap-1.5">
            <Share2 className="w-3.5 h-3.5" /> Share Matrix
          </button>
        </div>
      </div>

      {/* Search Bar + Controls Row */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Search */}
        <div ref={searchRef} className="relative flex-1 min-w-[240px] max-w-md">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setShowSearch(true); }}
              onFocus={() => { if (searchResults.length > 0) setShowSearch(true); }}
              placeholder="Search criminal, FIR, case, station, district..."
              className="w-full rounded border border-[var(--border-color)] bg-[var(--bg-secondary)] py-1.5 pl-8 pr-8 text-[11px] font-mono text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-blue)] focus:outline-none"
            />
            {searching && <Loader2 className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-[var(--accent-blue)] animate-spin" />}
            {searchQuery && !searching && (
              <button onClick={() => { setSearchQuery(''); setSearchResults([]); setShowSearch(false); }}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)]">
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Search Results Dropdown */}
          {showSearch && searchResults.length > 0 && (
            <div className="absolute z-50 top-full left-0 right-0 mt-1 rounded border border-[var(--border-color)] bg-[var(--bg-secondary)] shadow-lg max-h-64 overflow-y-auto">
              {searchResults.map((r) => (
                <button key={r.id} onClick={() => handleSelectSearchResult(r)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-[var(--bg-tertiary)] transition-colors border-b border-[var(--border-color)] last:border-0">
                  <span className="shrink-0">{TYPE_ICONS[r.type]}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] font-mono text-[var(--text-primary)] truncate">{r.name}</div>
                    <div className="text-[9px] font-mono text-[var(--text-secondary)] truncate">{r.detail}</div>
                  </div>
                  <span className="shrink-0 text-[8px] font-mono uppercase px-1.5 py-0.5 rounded" style={{ backgroundColor: `${TYPE_COLORS[r.type]}20`, color: TYPE_COLORS[r.type], border: `1px solid ${TYPE_COLORS[r.type]}40` }}>
                    {r.type}
                  </span>
                </button>
              ))}
            </div>
          )}
          {showSearch && searchQuery.length >= 2 && !searching && searchResults.length === 0 && (
            <div className="absolute z-50 top-full left-0 right-0 mt-1 rounded border border-[var(--border-color)] bg-[var(--bg-secondary)] shadow-lg p-3 text-center text-[10px] font-mono text-[var(--text-muted)]">
              No matching records found
            </div>
          )}
        </div>

        {/* Graph Controls */}
        <div className="flex items-center gap-1.5">
          {focusedEntity && (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded border border-[var(--accent-blue)]/30 bg-[var(--accent-blue)]/10 text-[9px] font-mono text-[var(--accent-blue)]">
              {focusing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Focus className="w-3 h-3" />}
              <span className="truncate max-w-[100px]">{focusedEntity.name}</span>
              <span className="text-[var(--text-muted)]">depth:{graphDepth}</span>
            </div>
          )}

          {focusedEntity && graphDepth < 4 && (
            <button onClick={handleExpandNetwork}
              className="px-2 py-1 rounded border border-[var(--accent-teal)]/30 bg-[var(--accent-teal)]/10 text-[9px] font-mono text-[var(--accent-teal)] hover:bg-[var(--accent-teal)]/20 transition-colors cursor-pointer flex items-center gap-1">
              <ChevronDown className="w-3 h-3" /> Expand
            </button>
          )}

          {focusedEntity && (
            <button onClick={handleResetView}
              className="px-2 py-1 rounded border border-[var(--border-muted)] text-[9px] font-mono text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer flex items-center gap-1">
              <RefreshCw className="w-3 h-3" /> Reset
            </button>
          )}

          {!focusedEntity && (
            <div className="flex rounded bg-[var(--bg-tertiary)] border border-[var(--border-muted)] p-0.5">
              <button onClick={() => setViewScope('full')}
                className={`px-2 py-1 rounded text-[8.5px] cursor-pointer flex items-center gap-1 ${viewScope === 'full' ? 'bg-[var(--accent-blue)] text-white font-bold' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}>
                <Globe className="w-3 h-3" /> All
              </button>
              <button onClick={() => setViewScope('person')}
                className={`px-2 py-1 rounded text-[8.5px] cursor-pointer flex items-center gap-1 ${viewScope === 'person' ? 'bg-[var(--accent-blue)] text-white font-bold' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}>
                <Layers className="w-3 h-3" /> Officer
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Provenance Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-2 rounded-card bg-[var(--bg-tertiary)]/60 border border-[var(--border-muted)] font-mono text-[9px]">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[8px] uppercase tracking-wider text-[var(--text-muted)] flex items-center gap-1 mr-1">
            <Filter className="w-3 h-3 text-[var(--accent-blue)]" /> Provenance:
          </span>
          <button onClick={() => setProvenanceFilter('ALL')}
            className={`px-2 py-1 rounded border transition-colors cursor-pointer ${provenanceFilter === 'ALL' ? 'bg-[var(--accent-blue)]/20 border-[var(--accent-blue)] text-[var(--accent-blue)] font-bold' : 'border-[var(--border-muted)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}>
            All ({provenanceSummary?.total_edges ?? graphData?.links.length ?? 0})
          </button>
          <button onClick={() => setProvenanceFilter('VERIFIED')}
            className={`px-2 py-1 rounded border transition-colors cursor-pointer flex items-center gap-1 ${provenanceFilter === 'VERIFIED' ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400 font-bold' : 'border-[var(--border-muted)] text-[var(--text-secondary)] hover:text-emerald-400'}`}>
            <ShieldCheck className="w-2.5 h-2.5" /> Verified ({provenanceSummary?.verified_relationships ?? 0})
          </button>
          <button onClick={() => setProvenanceFilter('ANALYTICAL_INFERENCE')}
            className={`px-2 py-1 rounded border transition-colors cursor-pointer flex items-center gap-1 ${provenanceFilter === 'ANALYTICAL_INFERENCE' ? 'bg-amber-500/20 border-amber-500 text-amber-400 font-bold' : 'border-[var(--border-muted)] text-[var(--text-secondary)] hover:text-amber-400'}`}>
            <GitCommit className="w-2.5 h-2.5" /> Analytical ({provenanceSummary?.analytical_relationships ?? 0})
          </button>
          <label className="flex items-center gap-1.5 ml-2 text-[8px] cursor-pointer text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
            <input type="checkbox" checked={excludeDemo} onChange={(e) => setExcludeDemo(e.target.checked)}
              className="accent-[var(--accent-blue)] rounded cursor-pointer" />
            <span>Exclude Demo</span>
          </label>
        </div>
        {graphData && graphData.nodes.some((n) => n.isSeed) && !excludeDemo && (
          <div className="flex items-center gap-1.5 text-[8px] text-[var(--accent-purple)]">
            <Database className="w-3 h-3" /> <span>Seed Demo Grounded</span>
          </div>
        )}
      </div>

      {/* Graph Metadata */}
      {graphData && (Object.keys(entityCounts).length > 0 || Object.keys(confidenceSummary).length > 0) && (
        <div className="flex flex-wrap items-start gap-3 p-2 rounded-card bg-[var(--bg-tertiary)]/60 border border-[var(--border-muted)] font-mono text-[9px]">
          {Object.keys(entityCounts).length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[8px] uppercase tracking-wider text-[var(--text-muted)] flex items-center gap-1">
                <BarChart3 className="w-3 h-3 text-[var(--accent-blue)]" /> Entities:
              </span>
              {Object.entries(entityCounts).map(([type, count]) => (
                <span key={type} className="px-1.5 py-0.5 rounded bg-[var(--accent-blue)]/10 border border-[var(--accent-blue)]/20 text-[var(--accent-blue)]">
                  {type}: {count}
                </span>
              ))}
            </div>
          )}
          {Object.keys(confidenceSummary).length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[8px] uppercase tracking-wider text-[var(--text-muted)] flex items-center gap-1">
                <Info className="w-3 h-3 text-[var(--accent-purple)]" /> Confidence:
              </span>
              {Object.entries(confidenceSummary).map(([level, count]) => {
                const color = level === 'HIGH' ? 'var(--accent-teal)' : level === 'MEDIUM' ? 'var(--accent-amber)' : 'var(--text-secondary)';
                return (
                  <span key={level} className="px-1.5 py-0.5 rounded border text-[9px]" style={{ backgroundColor: `${color}15`, borderColor: `${color}30`, color }}>
                    {level}: {count}
                  </span>
                );
              })}
            </div>
          )}
          {graphWarnings.length > 0 && (
            <div className="flex items-start gap-2 flex-wrap w-full mt-1">
              {graphWarnings.map((w, i) => (
                <span key={i} className="px-2 py-1 rounded bg-[var(--accent-amber)]/10 border border-[var(--accent-amber)]/30 text-[var(--accent-amber)] text-[8px] leading-tight">
                  <AlertTriangle className="w-2.5 h-2.5 inline mr-1" />{w}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Main Graph Grid */}
      <div className="flex-1 w-full grid grid-cols-1 lg:grid-cols-12 gap-4" style={{ minHeight: '500px' }}>
        <div className="lg:col-span-8" style={{ minHeight: '500px' }}>
          {loadError && !graphData ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center max-w-md">
                <AlertTriangle className="w-10 h-10 text-[var(--accent-coral)] mx-auto mb-3" />
                <p className="text-sm text-[var(--text-primary)] font-semibold mb-1">
                  Network Intelligence Unavailable
                </p>
                <p className="text-xs text-[var(--text-secondary)] mb-3">{loadError}</p>
                <button onClick={() => fetchGraph()} className="px-4 py-1.5 bg-[var(--accent-blue)] text-white text-xs rounded-btn hover:opacity-90 transition-opacity">
                  Retry
                </button>
              </div>
            </div>
          ) : graphData && graphData.nodes.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center max-w-sm">
                <AlertTriangle className="w-8 h-8 text-[var(--accent-amber)] mx-auto mb-2" />
                <p className="text-xs text-[var(--text-primary)] font-semibold mb-1">
                  {focusedEntity ? `No relationships found for "${focusedEntity.name}"` : 'No network records available'}
                </p>
                <p className="text-[10px] text-[var(--text-muted)] mb-3">
                  {focusedEntity
                    ? 'Try expanding the network depth or searching for a different entity.'
                    : 'Add linked FIR/case data or sync PostgreSQL into Neo4j to build the relationship graph.'
                  }
                </p>
                {focusedEntity ? (
                  <div className="flex gap-2 justify-center">
                    {graphDepth < 4 && (
                      <button onClick={handleExpandNetwork}
                        className="px-3 py-1.5 bg-[var(--accent-teal)]/15 text-[var(--accent-teal)] text-[10px] rounded-btn hover:bg-[var(--accent-teal)]/25 transition-colors border border-[var(--accent-teal)]/30">
                        Expand Depth
                      </button>
                    )}
                    <button onClick={handleResetView}
                      className="px-3 py-1.5 bg-[var(--bg-tertiary)] text-[var(--text-secondary)] text-[10px] rounded-btn hover:text-[var(--text-primary)] transition-colors border border-[var(--border-muted)]">
                      Full Graph
                    </button>
                  </div>
                ) : (
                  <button onClick={() => fetchGraph()} className="px-4 py-1.5 bg-[var(--accent-blue)] text-white text-[10px] rounded-btn hover:opacity-90 transition-opacity">
                    Load Full Graph
                  </button>
                )}
              </div>
            </div>
          ) : graphData ? (
            <CriminalGraph3D onNodeSelect={handleNodeSelect} onLinkSelect={handleLinkSelect} graphData={graphData} />
          ) : graphData && graphData.nodes.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center p-8 bg-[var(--bg-surface)] rounded-card border border-border-color text-center font-mono select-none">
              <NetIcon className="w-10 h-10 mb-3 text-[var(--text-disabled)]" />
              <p className="text-xs font-bold text-[var(--text-secondary)] uppercase">No Network Relationships Found</p>
              <p className="text-[10px] text-[var(--text-muted)] mt-1 max-w-sm">No criminal network entities match the currently active provenance filters and criteria.</p>
              <button onClick={() => { setProvenanceFilter('ALL'); setExcludeDemo(false); }} className="mt-3 px-3 py-1.5 rounded text-[10px] uppercase font-bold border border-[var(--accent-blue)]/30 text-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/10">
                Reset Filters
              </button>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center bg-[var(--bg-surface)] rounded-card border border-border-color text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-wider">
              {loadError ? (
                <div className="text-center p-6 space-y-2">
                  <AlertTriangle className="w-8 h-8 mx-auto text-[var(--accent-amber)]" />
                  <p className="text-xs font-bold text-[var(--text-primary)]">
                    {loadError.toLowerCase().includes('unauthorized') || loadError.includes('401') || loadError.includes('403')
                      ? 'Access Unauthorized'
                      : 'Network Intelligence Unavailable'}
                  </p>
                  <p className="text-[10px] text-[var(--text-secondary)] max-w-sm">{loadError}</p>
                  <button onClick={() => fetchGraph()} className="mt-2 px-3 py-1.5 rounded font-bold text-[10px] uppercase border border-[var(--accent-blue)]/30 text-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/10 cursor-pointer">
                    Retry Connection
                  </button>
                </div>
              ) : 'Loading network telemetry...'}
            </div>
          )}
        </div>
        <div className="lg:col-span-4 bg-secondary-bg/25 border border-border-color rounded-card overflow-auto" style={{ minHeight: '500px' }}>
          {selectedNode ? (
            <NodeDetailPanel 
              node={selectedNode} 
              links={graphData?.links ?? []} 
              nodes={graphData?.nodes ?? []} 
              onClose={() => setSelectedNode(null)} 
              onSelectNode={handleNodeSelect}
              onSelectLink={handleLinkSelect}
            />
          ) : selectedLink ? (
            <EdgeDetailPanel 
              link={selectedLink} 
              nodes={graphData?.nodes ?? []} 
              onClose={() => setSelectedLink(null)} 
              onSelectNode={handleNodeSelect}
            />
          ) : focusedEntity ? (
            <div className="h-full flex flex-col p-4 text-xs font-mono">
              <div className="flex items-center gap-2 mb-3">
                {TYPE_ICONS[focusedEntity.type]}
                <span className="text-[11px] font-bold text-[var(--text-primary)]">{focusedEntity.name}</span>
              </div>
              <div className="space-y-2 text-[10px] text-[var(--text-secondary)]">
                <div><span className="text-[var(--text-muted)]">Type:</span> <span className="uppercase">{focusedEntity.type}</span></div>
                <div><span className="text-[var(--text-muted)]">Detail:</span> {focusedEntity.detail}</div>
                {focusedEntity.status && (
                  <div><span className="text-[var(--text-muted)]">Status:</span> <span className="capitalize">{focusedEntity.status.replace(/_/g, ' ')}</span></div>
                )}
                {focusedEntity.risk_score !== undefined && (
                  <div><span className="text-[var(--text-muted)]">Risk Score:</span> <span style={{ color: focusedEntity.risk_score >= 80 ? 'var(--accent-coral)' : focusedEntity.risk_score >= 50 ? 'var(--accent-amber)' : 'var(--accent-teal)' }}>{focusedEntity.risk_score.toFixed(1)}%</span></div>
                )}
                <div className="pt-1 border-t border-[var(--border-color)] space-y-1">
                  <div><span className="text-[var(--text-muted)]">Graph Depth:</span> {graphDepth} / 4</div>
                  <div><span className="text-[var(--text-muted)]">Nodes:</span> {graphData?.nodes.length ?? 0}</div>
                  <div><span className="text-[var(--text-muted)]">Edges:</span> {graphData?.links.length ?? 0}</div>
                </div>
              </div>
              <div className="mt-4 space-y-2">
                {graphDepth < 4 && (
                  <button onClick={handleExpandNetwork}
                    disabled={focusing}
                    className="w-full px-3 py-2 rounded border border-[var(--accent-teal)]/30 bg-[var(--accent-teal)]/10 text-[10px] font-bold text-[var(--accent-teal)] hover:bg-[var(--accent-teal)]/20 transition-colors uppercase disabled:opacity-50">
                    {focusing ? 'Loading...' : `Expand Network (depth ${graphDepth + 1})`}
                  </button>
                )}
                <button onClick={handleResetView}
                  className="w-full px-3 py-2 rounded border border-[var(--border-muted)] text-[10px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors uppercase">
                  Reset to Full Graph
                </button>
              </div>
              <p className="mt-4 text-[9px] text-[var(--text-muted)]">
                Click nodes in the graph to inspect details. Use Expand to load deeper relationships.
              </p>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center p-6 text-center text-xs font-mono text-[var(--text-muted)] uppercase border border-dashed border-[var(--border-primary)]/40 rounded-card">
              <Search className="w-10 h-10 mb-3 text-[var(--text-disabled)]" />
              <span className="text-[10px]">Search for an entity or select a node to begin investigation</span>
              <span className="mt-2 text-[9px] text-[var(--text-disabled)]">Search by name, FIR number, case ID, station, or district</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default Network;
