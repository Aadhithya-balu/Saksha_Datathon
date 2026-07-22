import React from 'react';
import type { LinkAnalysisData, CentralityMetric } from '../../services/api';
import { BarChart3, Activity, ShieldAlert, Cpu, Award } from 'lucide-react';

interface LinkAnalysisPanelProps {
  data: LinkAnalysisData | null;
  loading: boolean;
}

export const LinkAnalysisPanel: React.FC<LinkAnalysisPanelProps> = ({ data, loading }) => {
  if (loading || !data) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 bg-[#080E1B] border border-white/10 rounded-card text-xs font-mono text-[#6A7A96] uppercase">
        <Cpu className="w-8 h-8 animate-spin text-[#3B82F6] mb-3" />
        <span>Calculating network graph centralities & broker node metrics...</span>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col gap-4 p-4 bg-[#080E1B] border border-white/10 rounded-card font-mono overflow-y-auto">
      {/* Header */}
      <div className="border-b border-white/10 pb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-md font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-purple-400 animate-pulse" />
            Network Topology & Centrality Link Analysis
          </h3>
          <p className="text-[10px] text-[#6A7A96] mt-1">
            DEGREE CENTRALITY, BETWEENNESS BROKER SCORES, AND HIGH-IMPACT BRIDGE NODES
          </p>
        </div>

        {/* Top Stats */}
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 bg-[#050912] rounded border border-white/10 text-center">
            <div className="text-[9px] text-[#8A99AD] uppercase">Graph Density</div>
            <div className="text-xs font-bold text-purple-400">{data.graph_density}</div>
          </div>
          <div className="px-3 py-1.5 bg-[#050912] rounded border border-white/10 text-center">
            <div className="text-[9px] text-[#8A99AD] uppercase">Syndicate Clusters</div>
            <div className="text-xs font-bold text-amber-400">{data.total_clusters}</div>
          </div>
        </div>
      </div>

      {/* Main Grid: Broker Nodes vs High-Impact Nodes */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1">
        {/* Top Broker Nodes (Betweenness) */}
        <div className="bg-[#050912] p-4 rounded-card border border-white/10 space-y-3">
          <div className="flex items-center justify-between border-b border-white/5 pb-2">
            <h4 className="text-xs font-bold text-white uppercase flex items-center gap-2">
              <Activity className="w-4 h-4 text-purple-400" />
              Top Broker Nodes (Betweenness Centrality)
            </h4>
            <span className="text-[9px] text-[#6A7A96]">Key intermediaries</span>
          </div>

          <div className="space-y-2.5">
            {data.top_broker_nodes.map((node: CentralityMetric) => (
              <div key={node.node_id} className="p-3 bg-[#0d1627] border border-white/5 rounded-card flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-white uppercase">{node.node_name}</div>
                  <div className="text-[10px] text-[#6A7A96] uppercase">{node.category} • Risk {node.riskScore}</div>
                </div>
                <div className="text-right font-bold">
                  <div className="text-xs text-purple-400">{node.betweenness_score}</div>
                  <div className="text-[9px] text-[#8A99AD]">Betweenness</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* High Impact Degree Nodes */}
        <div className="bg-[#050912] p-4 rounded-card border border-white/10 space-y-3">
          <div className="flex items-center justify-between border-b border-white/5 pb-2">
            <h4 className="text-xs font-bold text-white uppercase flex items-center gap-2">
              <Award className="w-4 h-4 text-amber-400" />
              High Impact Hub Nodes (Degree Centrality)
            </h4>
            <span className="text-[9px] text-[#6A7A96]">Most connected</span>
          </div>

          <div className="space-y-2.5">
            {data.high_impact_nodes.map((node: CentralityMetric) => (
              <div key={node.node_id} className="p-3 bg-[#0d1627] border border-white/5 rounded-card flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-white uppercase">{node.node_name}</div>
                  <div className="text-[10px] text-[#6A7A96] uppercase">{node.category} • Risk {node.riskScore}</div>
                </div>
                <div className="text-right font-bold">
                  <div className="text-xs text-amber-400">{node.degree_centrality}</div>
                  <div className="text-[9px] text-[#8A99AD]">Degree</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bridge Nodes Warning Banner */}
      {data.bridge_nodes.length > 0 && (
        <div className="bg-rose-950/20 border border-rose-500/30 p-3 rounded-card flex items-center gap-3">
          <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0" />
          <div className="text-[10px] text-[#A8B4CC]">
            <strong className="text-rose-300 uppercase">Bridge Connection Alert: </strong>
            {data.bridge_nodes.length} bridge nodes identified (e.g.{' '}
            {data.bridge_nodes.slice(0, 3).map((b) => b.node_name).join(', ')}) linking distinct criminal gangs across jurisdictions.
          </div>
        </div>
      )}
    </div>
  );
};

export default LinkAnalysisPanel;
