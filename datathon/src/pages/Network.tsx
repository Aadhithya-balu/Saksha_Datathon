import React, { useEffect, useState, useCallback } from 'react';
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
  Globe
} from 'lucide-react';
import { downloadSecureDossier } from '../utils/downloader';
import { useAuditStore } from '../store/auditStore';
import { useAuthStore } from '../store/authStore';
import { getFullNetworkGraph, getNetworkPerson } from '../services/api';
import type { ProvenanceSummary } from '../services/api';

export const Network: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedLink, setSelectedLink] = useState<GraphLink | null>(null);
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: GraphLink[] } | null>(null);
  const [provenanceSummary, setProvenanceSummary] = useState<ProvenanceSummary | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  
  // Filter state (Issue #159)
  const [viewScope, setViewScope] = useState<'person' | 'full'>('full');
  const [provenanceFilter, setProvenanceFilter] = useState<string>('ALL');
  const [excludeDemo, setExcludeDemo] = useState<boolean>(false);

  const { user } = useAuthStore();
  const { addLog } = useAuditStore();

  const fetchGraph = useCallback(() => {
    let isMounted = true;
    const filterArg = provenanceFilter === 'ALL' ? undefined : provenanceFilter;

    const request = viewScope === 'person' 
      ? getNetworkPerson(user?.badgeId ?? 'SCRB-7740', 2, filterArg, excludeDemo)
      : getFullNetworkGraph(undefined, undefined, filterArg, excludeDemo);

    request
      .then((response) => {
        if (isMounted) {
          setGraphData({ nodes: response.nodes, links: response.edges });
          if (response.provenance_summary) {
            setProvenanceSummary(response.provenance_summary);
          }
          setLoadError(null);
        }
      })
      .catch((error) => {
        if (isMounted) {
          setLoadError(error instanceof Error ? error.message : 'Failed to load network data');
          setGraphData(null);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [user?.badgeId, viewScope, provenanceFilter, excludeDemo]);

  useEffect(() => {
    return fetchGraph();
  }, [fetchGraph]);

  const handleNodeSelect = (node: GraphNode) => {
    setSelectedNode(node);
    setSelectedLink(null);
  };

  const handleLinkSelect = (link: GraphLink) => {
    setSelectedLink(link);
    setSelectedNode(null);
  };

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

    downloadSecureDossier(
      'Suspect Connection Matrix', 
      matrixData, 
      user ? `CONFIDENTIAL - ${user.badgeId}` : 'CONFIDENTIAL - STATE POLICE'
    );

    if (user) {
      addLog(
        user.name,
        user.badgeId,
        'EXPORT',
        'Exported backend suspect relationship linkage association matrix (JSON)'
      );
    }
  };

  return (
    <div className="h-[86vh] flex flex-col gap-3 p-1 md:p-3 select-none bg-[var(--bg-primary)]">
      
      {/* Title Header & Provenance Toolbar */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 border-b border-[var(--border-muted)] pb-2.5">
        <div>
          <h2 className="text-md font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
            <NetIcon className="w-5 h-5 text-[#6C43CC] animate-pulse" />
            Crime Association Net Analysis
          </h2>
          <p className="text-[9.5px] font-mono text-[var(--text-muted)] mt-0.5">
            VERIFIED DATABASE FACTS • ANALYTICAL LEADS • PROVENANCE TRACEABILITY
          </p>
          {loadError && <p className="mt-1 text-[9px] font-mono text-amber-400 uppercase tracking-wider">{loadError}</p>}
        </div>

        {/* Global actions & Scope Toggles */}
        <div className="flex flex-wrap items-center gap-2 text-[9px] font-mono uppercase">
          {/* Scope Toggle */}
          <div className="flex rounded bg-[var(--bg-tertiary)] border border-[var(--border-muted)] p-0.5">
            <button
              onClick={() => setViewScope('full')}
              className={`px-2 py-1 rounded text-[8.5px] cursor-pointer flex items-center gap-1 ${
                viewScope === 'full' 
                  ? 'bg-[var(--accent-blue)] text-white font-bold' 
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <Globe className="w-3 h-3" />
              All Network
            </button>
            <button
              onClick={() => setViewScope('person')}
              className={`px-2 py-1 rounded text-[8.5px] cursor-pointer flex items-center gap-1 ${
                viewScope === 'person' 
                  ? 'bg-[var(--accent-blue)] text-white font-bold' 
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <Layers className="w-3 h-3" />
              Officer Focus
            </button>
          </div>

          <button
            onClick={handleExportMatrix}
            className="px-2.5 py-1.5 bg-[var(--bg-tertiary)] hover:bg-[#1E6FD9]/15 border border-[#1e6fd9]/25 hover:border-[#1E6FD9]/50 text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-btn transition-colors cursor-pointer flex items-center gap-1.5"
          >
            <Share2 className="w-3.5 h-3.5" />
            Share Matrix
          </button>
        </div>
      </div>

      {/* Provenance Filter Bar & Summary Metric Badges (Issue #159) */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-2 rounded-card bg-[var(--bg-tertiary)]/60 border border-[var(--border-muted)] font-mono text-[9px]">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[8px] uppercase tracking-wider text-[var(--text-muted)] flex items-center gap-1 mr-1">
            <Filter className="w-3 h-3 text-[var(--accent-blue)]" />
            Provenance Filter:
          </span>
          <button
            onClick={() => setProvenanceFilter('ALL')}
            className={`px-2 py-1 rounded border transition-colors cursor-pointer ${
              provenanceFilter === 'ALL'
                ? 'bg-[var(--accent-blue)]/20 border-[var(--accent-blue)] text-[var(--accent-blue)] font-bold'
                : 'border-[var(--border-muted)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            All ({provenanceSummary?.total_edges ?? graphData?.links.length ?? 0})
          </button>
          <button
            onClick={() => setProvenanceFilter('VERIFIED')}
            className={`px-2 py-1 rounded border transition-colors cursor-pointer flex items-center gap-1 ${
              provenanceFilter === 'VERIFIED'
                ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400 font-bold'
                : 'border-[var(--border-muted)] text-[var(--text-secondary)] hover:text-emerald-400'
            }`}
          >
            <ShieldCheck className="w-2.5 h-2.5" />
            Verified Facts ({provenanceSummary?.verified_relationships ?? 0})
          </button>
          <button
            onClick={() => setProvenanceFilter('ANALYTICAL_INFERENCE')}
            className={`px-2 py-1 rounded border transition-colors cursor-pointer flex items-center gap-1 ${
              provenanceFilter === 'ANALYTICAL_INFERENCE'
                ? 'bg-amber-500/20 border-amber-500 text-amber-400 font-bold'
                : 'border-[var(--border-muted)] text-[var(--text-secondary)] hover:text-amber-400'
            }`}
          >
            <GitCommit className="w-2.5 h-2.5" />
            Analytical Leads ({provenanceSummary?.analytical_relationships ?? 0})
          </button>
          
          <label className="flex items-center gap-1.5 ml-2 text-[8px] cursor-pointer text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
            <input
              type="checkbox"
              checked={excludeDemo}
              onChange={(e) => setExcludeDemo(e.target.checked)}
              className="accent-[var(--accent-blue)] rounded cursor-pointer"
            />
            <span>Exclude Demo Records</span>
          </label>
        </div>

        {/* Demo banner indicator if present */}
        {graphData && graphData.nodes.some((n) => n.isSeed) && !excludeDemo && (
          <div className="flex items-center gap-1.5 text-[8px] text-[var(--accent-purple)]">
            <Database className="w-3 h-3" />
            <span>Seed Demo Grounded</span>
          </div>
        )}
      </div>

      {/* Main Graph Grid splitting */}
      <div className="flex-1 w-full grid grid-cols-1 lg:grid-cols-12 gap-4 overflow-hidden min-h-0">
        {/* Left Side: ThreeJS Scene (8 cols on lg) */}
        <div className="lg:col-span-8 h-full min-h-[380px]">
          {graphData ? (
            <CriminalGraph3D 
              onNodeSelect={handleNodeSelect} 
              onLinkSelect={handleLinkSelect}
              graphData={graphData} 
            />
          ) : (
            <div className="h-full flex items-center justify-center bg-[var(--bg-surface)] rounded-card border border-border-color text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-wider">
              {loadError ? 'Backend network unavailable' : 'Loading backend network telemetry...'}
            </div>
          )}
        </div>

        {/* Right Side: Dossier Details / Link Inspector card (4 cols on lg) */}
        <div className="lg:col-span-4 h-full bg-secondary-bg/25 border border-border-color rounded-card overflow-hidden">
          {selectedNode ? (
            <NodeDetailPanel 
              node={selectedNode} 
              links={graphData?.links ?? []}
              nodes={graphData?.nodes ?? []}
              onClose={() => setSelectedNode(null)} 
            />
          ) : selectedLink ? (
            <EdgeDetailPanel
              link={selectedLink}
              nodes={graphData?.nodes ?? []}
              onClose={() => setSelectedLink(null)}
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center p-6 text-center text-xs font-mono text-[var(--text-muted)] uppercase border border-dashed border-[var(--border-primary)]/40 rounded-card">
              <Layers className="w-10 h-10 mb-3 text-[var(--text-disabled)]" />
              <span>Select an entity pin or link line inside the 3D graph to inspect dossiers and evidence provenance telemetry</span>
            </div>
          )}
        </div>
      </div>

    </div>
  );
};
export default Network;



