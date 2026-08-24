import { useState, useEffect, useCallback } from 'react';
import {
  getFullNetworkGraph,
  getGangNetworks,
  calculateShortestPath,
  getLinkAnalysis,
  getAIGraphInsights,
  triggerNeo4jSync,
} from '../services/api';
import type {
  GangNetworkSummary,
  ShortestPathResult,
  LinkAnalysisData,
  AIGraphInsightData,
} from '../services/api';
import type { GraphNode, GraphLink } from '../components/network/CriminalGraph3D';

export type NetworkWorkspaceView = '3d_explorer' | 'shortest_path' | 'gangs' | 'link_analysis' | 'timeline' | 'ai_insights';

export function useNetwork() {
  const [activeView, setActiveView] = useState<NetworkWorkspaceView>('3d_explorer');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [minRisk, setMinRisk] = useState<number>(0);
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: GraphLink[] } | null>(null);
  const [isNeo4jBacked, setIsNeo4jBacked] = useState<boolean>(false);
  // Gap 132.4: provenance transparency about demo-seeded records.
  const [seedNodeCount, setSeedNodeCount] = useState<number>(0);
  const [datasetScope, setDatasetScope] = useState<string>('live_records');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Gang Networks state
  const [gangs, setGangs] = useState<GangNetworkSummary[]>([]);
  const [selectedGang, setSelectedGang] = useState<GangNetworkSummary | null>(null);

  // Shortest Path state
  const [sourceNodeId, setSourceNodeId] = useState<string>('');
  const [targetNodeId, setTargetNodeId] = useState<string>('');
  const [pathResult, setPathResult] = useState<ShortestPathResult | null>(null);
  const [pathLoading, setPathLoading] = useState<boolean>(false);

  // Link Analysis state
  const [linkAnalysis, setLinkAnalysis] = useState<LinkAnalysisData | null>(null);

  // AI Insights state
  const [insights, setInsights] = useState<AIGraphInsightData[]>([]);

  // Timeline state
  const [timelineDateRange, setTimelineDateRange] = useState<[string, string]>(['2025-01-01', '2026-12-31']);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // Load Main Graph
  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const cat = categoryFilter === 'all' ? undefined : categoryFilter;
      const res = await getFullNetworkGraph(cat, minRisk);
      setGraphData({
        nodes: res.nodes as GraphNode[],
        links: res.edges as GraphLink[],
      });
      setIsNeo4jBacked(res.is_neo4j_backed);
      setSeedNodeCount(res.seed_node_count ?? 0);
      setDatasetScope(res.dataset_scope ?? 'live_records');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch graph data');
    } finally {
      setLoading(false);
    }
  }, [categoryFilter, minRisk]);

  useEffect(() => {
    void loadGraph();
  }, [loadGraph]);

  // Load Gangs
  const loadGangs = useCallback(async () => {
    try {
      const data = await getGangNetworks();
      setGangs(data);
      if (data.length > 0 && !selectedGang) {
        setSelectedGang(data[0]);
      }
    } catch {
      // Fallback handled in UI
    }
  }, [selectedGang]);

  // Run Shortest Path
  const runShortestPath = async (src: string, tgt: string) => {
    if (!src || !tgt) return;
    setPathLoading(true);
    try {
      const res = await calculateShortestPath(src, tgt);
      setPathResult(res);
    } catch (err) {
      setPathResult({
        found: false,
        distance: 0,
        path_nodes: [],
        path_edges: [],
        explanation: err instanceof Error ? err.message : 'Path calculation failed.',
      });
    } finally {
      setPathLoading(false);
    }
  };

  // Run Link Analysis
  const loadLinkAnalysis = useCallback(async () => {
    try {
      const res = await getLinkAnalysis();
      setLinkAnalysis(res);
    } catch {
      // Handled silently
    }
  }, []);

  // Load AI Insights
  const loadInsights = useCallback(async () => {
    try {
      const res = await getAIGraphInsights();
      setInsights(res);
    } catch {
      // Handled silently
    }
  }, []);

  // Trigger Neo4j Sync
  const handleNeo4jSync = async () => {
    try {
      await triggerNeo4jSync();
      await loadGraph();
    } catch {
      // Ignored
    }
  };

  useEffect(() => {
    void loadGangs();
    void loadLinkAnalysis();
    void loadInsights();
  }, [loadGangs, loadLinkAnalysis, loadInsights]);

  return {
    activeView,
    setActiveView,
    categoryFilter,
    setCategoryFilter,
    minRisk,
    setMinRisk,
    graphData,
    isNeo4jBacked,
    seedNodeCount,
    datasetScope,
    loading,
    error,
    selectedNode,
    setSelectedNode,
    gangs,
    selectedGang,
    setSelectedGang,
    sourceNodeId,
    setSourceNodeId,
    targetNodeId,
    setTargetNodeId,
    pathResult,
    pathLoading,
    runShortestPath,
    linkAnalysis,
    insights,
    timelineDateRange,
    setTimelineDateRange,
    reloadGraph: loadGraph,
    handleNeo4jSync,
  };
}
