import React, { useEffect, useState } from 'react';
import CriminalGraph3D from '../components/network/CriminalGraph3D';
import type { GraphNode } from '../components/network/CriminalGraph3D';
import NodeDetailPanel from '../components/network/NodeDetailPanel';
import { Share2, Network as NetIcon, Layers } from 'lucide-react';
import { downloadSecureDossier } from '../utils/downloader';
import { useAuditStore } from '../store/auditStore';
import { useAuthStore } from '../store/authStore';
import { getNetworkPerson } from '../services/api';

export const Network: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: Array<{ source: string; target: string; relationship: string; }> } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();

  useEffect(() => {
    let isMounted = true;
    const personId = user?.badgeId ?? 'SCRB-7740';

    void getNetworkPerson(personId)
      .then((response) => {
        if (isMounted) {
          setGraphData({ nodes: response.nodes, links: response.edges });
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
  }, [user?.badgeId]);

  const handleExportMatrix = () => {
    const matrixData = {
      relationType: 'Criminal Link Association Matrix',
      totalNodes: graphData?.nodes.length ?? 0,
      totalEdges: graphData?.links.length ?? 0,
      activeSuspects: graphData?.nodes.filter((node) => node.category === 'suspect').map((node) => node.name) ?? [],
      relationEdges: graphData?.links.map((link) => ({
        from: link.source,
        to: link.target,
        relation: link.relationship,
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
    <div className="h-[84vh] flex flex-col gap-4 p-1 md:p-3 select-none bg-[var(--bg-primary)]">
      
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-[var(--border-muted)] pb-3">
        <div>
          <h2 className="text-md font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
            <NetIcon className="w-5 h-5 text-[#6C43CC] animate-pulse" />
            Crime Association Net Analysis
          </h2>
          <p className="text-[9.5px] font-mono text-[var(--text-muted)] mt-0.5">
            THREE.JS FORCE-DIRECTED SUSPECT CORRELATIONS & INTERSTATE NETWORK DOSSIERS
          </p>
          {loadError && <p className="mt-1 text-[9px] font-mono text-amber-400 uppercase tracking-wider">{loadError}</p>}
        </div>

        {/* Global actions */}
        <div className="flex items-center gap-2 text-[9px] font-mono uppercase">
          <button
            onClick={handleExportMatrix}
            className="px-2.5 py-1.5 bg-[var(--bg-tertiary)] hover:bg-[#1E6FD9]/15 border border-[#1e6fd9]/25 hover:border-[#1E6FD9]/50 text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-btn transition-colors cursor-pointer flex items-center gap-1.5"
          >
            <Share2 className="w-3.5 h-3.5" />
            Share Link Matrix
          </button>
        </div>
      </div>

      {/* Main Graph Grid splitting */}
      <div className="flex-1 w-full grid grid-cols-1 lg:grid-cols-12 gap-5 overflow-hidden">
        {/* Left Side: ThreeJS Scene (9 cols on lg) */}
        <div className="lg:col-span-8 h-full min-h-[400px]">
          {graphData ? (
            <CriminalGraph3D onNodeSelect={setSelectedNode} graphData={graphData} />
          ) : (
            <div className="h-full flex items-center justify-center bg-[var(--bg-surface)] rounded-card border border-border-color text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-wider">
              {loadError ? 'Backend network unavailable' : 'Loading backend network telemetry...'}
            </div>
          )}
        </div>

        {/* Right Side: Dossier Details card (4 cols on lg) */}
        <div className="lg:col-span-4 h-full bg-secondary-bg/25 border border-border-color rounded-card overflow-hidden">
          {selectedNode ? (
            <NodeDetailPanel 
              node={selectedNode} 
              onClose={() => setSelectedNode(null)} 
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center p-6 text-center text-xs font-mono text-[var(--text-muted)] uppercase border border-dashed border-[var(--border-primary)]/40 rounded-card">
              <Layers className="w-10 h-10 mb-3 text-[var(--text-disabled)]" />
              <span>{graphData ? 'Select suspect node pin inside 3D relations workspace to unlock dossiers telemetry' : 'Loading backend network telemetry...'}</span>
            </div>
          )}
        </div>
      </div>

    </div>
  );
};
export default Network;


