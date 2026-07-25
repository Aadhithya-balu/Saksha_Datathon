import React, { useState } from 'react';
import { useNetwork } from '../../hooks/useNetwork';
import GraphExplorerToolbar from '../../components/network/GraphExplorerToolbar';
import CriminalGraph3D from '../../components/network/CriminalGraph3D';
import type { GraphNode } from '../../components/network/CriminalGraph3D';
import NodeDetailPanel from '../../components/network/NodeDetailPanel';
import ShortestPathPanel from '../../components/network/ShortestPathPanel';
import GangNetworkView from '../../components/network/GangNetworkView';
import LinkAnalysisPanel from '../../components/network/LinkAnalysisPanel';
import NetworkTimelineSlider from '../../components/network/NetworkTimelineSlider';
import AIGraphInsightsModal from '../../components/network/AIGraphInsightsModal';
import { downloadSecureDossier } from '../../utils/downloader';
import { useAuditStore } from '../../store/auditStore';
import { useAuthStore } from '../../store/authStore';
import { Network as NetIcon, Layers } from 'lucide-react';
import { CardSkeleton } from '../../components/ui/Skeleton';

export const NetworkPageWorkspace: React.FC = () => {
  const {
    activeView,
    setActiveView,
    categoryFilter,
    setCategoryFilter,
    minRisk,
    setMinRisk,
    graphData,
    isNeo4jBacked,
    loading,
    error,
    selectedNode,
    setSelectedNode,
    gangs,
    selectedGang,
    setSelectedGang,
    pathResult,
    pathLoading,
    runShortestPath,
    linkAnalysis,
    insights,
    handleNeo4jSync,
  } = useNetwork();

  const [searchQuery, setSearchQuery] = useState<string>('');
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();

  const handleExportMatrix = () => {
    const matrixData = {
      relationType: 'Criminal Link Association Matrix',
      totalNodes: graphData?.nodes.length ?? 0,
      totalEdges: graphData?.links.length ?? 0,
      isNeo4jBacked,
      activeSuspects: graphData?.nodes.filter((node) => node.category === 'suspect').map((node) => node.name) ?? [],
      relationEdges:
        graphData?.links.map((link) => ({
          from: link.source,
          to: link.target,
          relation: link.relationship,
        })) ?? [],
    };

    downloadSecureDossier(
      'Suspect Connection Matrix',
      matrixData,
      user ? `CONFIDENTIAL - ${user.badgeId}` : 'CONFIDENTIAL - STATE POLICE'
    );

    if (user) {
      addLog(user.name, user.badgeId, 'EXPORT', 'Exported suspect relationship linkage association matrix (JSON)');
    }
  };

  return (
    <div className="min-h-[85vh] lg:h-[85vh] flex flex-col gap-3 p-1 md:p-3 select-none bg-[var(--bg-primary)] font-mono">
      {/* Title & Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-[var(--border-muted)] pb-2">
        <div>
          <h2 className="text-md font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
            <NetIcon className="w-5 h-5 text-[#6C43CC] animate-pulse" />
            Graph-Based Criminal Intelligence & Relationship Analysis
          </h2>
          <p className="text-[9.5px] text-[var(--text-muted)] mt-0.5">
            NEO4J CYPHER GRAPH DB • THREE.JS FORCE DIRECTED NETWORK • SHORTEST PATH • GANG SYNDICATES • LINK CENTRALITY
          </p>
        </div>
      </div>

      {/* Global Explorer Navigation & Filter Toolbar */}
      <GraphExplorerToolbar
        activeView={activeView}
        setActiveView={setActiveView}
        categoryFilter={categoryFilter}
        setCategoryFilter={setCategoryFilter}
        minRisk={minRisk}
        setMinRisk={setMinRisk}
        isNeo4jBacked={isNeo4jBacked}
        onExportMatrix={handleExportMatrix}
        onNeo4jSync={handleNeo4jSync}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
      />

      {/* Workspace Display Area */}
      <div className="flex-1 w-full overflow-y-auto lg:overflow-hidden">
        {activeView === '3d_explorer' && (
          <div className="h-full grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Left 8 cols: 3D Scene */}
            <div className="lg:col-span-8 h-full min-h-[400px]">
              {graphData ? (
                <CriminalGraph3D onNodeSelect={setSelectedNode} graphData={graphData} />
              ) : (
                <div className="h-full flex items-center justify-center bg-[var(--bg-surface)] rounded-card border border-[var(--border-secondary)]">
                  {loading ? (
                    <div className="w-full p-6"><CardSkeleton /></div>
                  ) : (
                    <span className="text-xs text-[var(--text-muted)] uppercase">{error || 'Graph data unavailable'}</span>
                  )}
                </div>
              )}
            </div>
            {/* Right 4 cols: Node Detail Panel */}
            <div className="lg:col-span-4 h-full bg-secondary-bg/25 border border-border-color rounded-card overflow-hidden">
              {selectedNode ? (
                <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
              ) : (
                <div className="h-full flex flex-col items-center justify-center p-6 text-center text-xs text-[var(--text-muted)] uppercase border border-dashed border-[var(--border-primary)]/40 rounded-card">
                  <Layers className="w-10 h-10 mb-3 text-[var(--text-disabled)]" />
                  <span>Select suspect node inside 3D relations workspace to unlock dossiers telemetry</span>
                </div>
              )}
            </div>
          </div>
        )}

        {activeView === 'shortest_path' && (
          <div className="h-full grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-8 h-full">
              <ShortestPathPanel
                nodes={graphData?.nodes || []}
                onCalculatePath={runShortestPath}
                pathResult={pathResult}
                loading={pathLoading}
                onSelectNodeIn3D={setSelectedNode}
              />
            </div>
            <div className="lg:col-span-4 h-full bg-secondary-bg/25 border border-border-color rounded-card overflow-hidden">
              {selectedNode ? (
                <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
              ) : (
                <div className="h-full flex flex-col items-center justify-center p-6 text-center text-xs text-[var(--text-muted)] uppercase border border-dashed border-[var(--border-primary)]/40 rounded-card">
                  <Layers className="w-10 h-10 mb-3 text-[var(--text-disabled)]" />
                  <span>Select any path node to inspect dossier details</span>
                </div>
              )}
            </div>
          </div>
        )}

        {activeView === 'gangs' && (
          <GangNetworkView
            gangs={gangs}
            selectedGang={selectedGang}
            onSelectGang={setSelectedGang}
            onSelectMemberIn3D={setSelectedNode}
          />
        )}

        {activeView === 'link_analysis' && <LinkAnalysisPanel data={linkAnalysis} loading={loading} />}

        {activeView === 'timeline' && (
          <div className="h-full flex flex-col gap-3">
            <NetworkTimelineSlider />
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-0">
              <div className="lg:col-span-8 h-full min-h-[350px]">
                {graphData && <CriminalGraph3D onNodeSelect={setSelectedNode} graphData={graphData} />}
              </div>
              <div className="lg:col-span-4 h-full bg-secondary-bg/25 border border-border-color rounded-card overflow-hidden">
                {selectedNode ? (
                  <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
                ) : (
                  <div className="h-full flex flex-col items-center justify-center p-6 text-center text-xs text-[var(--text-muted)] uppercase border border-dashed border-[var(--border-primary)]/40 rounded-card">
                    <Layers className="w-10 h-10 mb-3 text-[var(--text-disabled)]" />
                    <span>Scrub timeline slider to inspect temporal graph changes</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeView === 'ai_insights' && (
          <AIGraphInsightsModal insights={insights} onSelectNodeIn3D={setSelectedNode} />
        )}
      </div>
    </div>
  );
};

export default NetworkPageWorkspace;
