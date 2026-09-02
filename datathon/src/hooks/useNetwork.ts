import { useState, useEffect, useCallback } from 'react';
import {
  getFullNetworkGraph,
  getGangNetworks,
  calculateShortestPath,
  getLinkAnalysis,
  getAIGraphInsights,
  findNetworkPath,
  triggerNeo4jSync,
  type NetworkFilterParams,
  type NetworkPathResponse,
} from '../services/api';
import type {
  GangNetworkSummary,
  ShortestPathResult,
  LinkAnalysisData,
  AIGraphInsightData,
} from '../services/api';
import type { GraphNode, GraphLink } from '../components/network/CriminalGraph3D';

export type NetworkWorkspaceView = '3d_explorer' | 'shortest_path' | 'path_finder' | 'gangs' | 'link_analysis' | 'timeline' | 'ai_insights';

export function useNetwork() {
  const [activeView, setActiveView] = useState<NetworkWorkspaceView>('3d_explorer');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [minRisk, setMinRisk] = useState<number>(0);
  // Issue #226: multi-parameter case filters (applied server-side).
  const [networkFilters, setNetworkFilters] = useState<NetworkFilterParams>({});
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

  // Investigative Path Finder state (issue #230)
  const [pathSource, setPathSource] = useState<GraphNode | null>(null);
  const [pathTarget, setPathTarget] = useState<GraphNode | null>(null);
  const [pathMaxHops, setPathMaxHops] = useState<number>(3);
  const [connectionPath, setConnectionPath] = useState<NetworkPathResponse | null>(null);
  const [connectionLoading, setConnectionLoading] = useState<boolean>(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Link Analysis state
  const [linkAnalysis, setLinkAnalysis] = useState<LinkAnalysisData | null>(null);

  // AI Insights state
  const [insights, setInsights] = useState<AIGraphInsightData[]>([]);

  // Timeline state
  const [timelineDateRange, setTimelineDateRange] = useState<[string, string]>(['2025-01-01', '2026-12-31']);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // The timeline slider is a date window over the dataset. Until the user moves
  // it, it sits on the full window and adds no restriction to the queries (so
  // the default graph keeps matching the old no-date behaviour).
  const isTimelineActive = !(
    timelineDateRange[0] === '2025-01-01' && timelineDateRange[1] === '2026-12-31'
  );

  // Issue #226 filters + the active timeline window (timeline loses to explicit
  // network-filter dates, which are more precise).
  const effectiveFilters = useCallback(
    (base: NetworkFilterParams): NetworkFilterParams => {
      if (base.dateFrom || base.dateTo || !isTimelineActive) return base;
      return { ...base, dateFrom: timelineDateRange[0], dateTo: timelineDateRange[1] };
    },
    [timelineDateRange, isTimelineActive]
  );

  // Load Main Graph
  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const cat = categoryFilter === 'all' ? undefined : categoryFilter;
      const res = await getFullNetworkGraph(cat, minRisk, undefined, false, effectiveFilters(networkFilters));
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
  }, [categoryFilter, minRisk, effectiveFilters, networkFilters]);

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

  // Investigative Path Finder (issue #230): evidence-backed connection search.
  // Always carries the current issue #226 filters so a path can never leak a
  // relationship the investigator excluded.
  const runConnectionSearch = useCallback(async () => {
    setConnectionError(null);
    if (!pathSource || !pathTarget) {
      setConnectionError('Please select both source and target entities.');
      return;
    }
    if (pathSource.id === pathTarget.id) {
      setConnectionError('Please select two different entities.');
      return;
    }
    setConnectionLoading(true);
    try {
      const res = await findNetworkPath(pathSource.id, pathTarget.id, pathMaxHops, effectiveFilters(networkFilters));
      setConnectionPath(res);
    } catch (err) {
      setConnectionPath(null);
      setConnectionError(
        err instanceof Error && err.message ? err.message : 'Unable to find the connection. Please try again.'
      );
    } finally {
      setConnectionLoading(false);
    }
  }, [pathSource, pathTarget, pathMaxHops, effectiveFilters, networkFilters]);

  const clearConnectionPath = useCallback(() => {
    setConnectionPath(null);
    setConnectionError(null);
  }, []);

  // Invalidate a stale path as soon as the filtered network or the active
  // timeline window changes: the previous result was computed against a
  // different dataset and must not remain shown.
  useEffect(() => {
    setConnectionPath(null);
    setConnectionError(null);
    setPathSource(null);
    setPathTarget(null);
  }, [networkFilters, timelineDateRange]);

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
    networkFilters,
    setNetworkFilters,
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
    pathSource,
    setPathSource,
    pathTarget,
    setPathTarget,
    pathMaxHops,
    setPathMaxHops,
    connectionPath,
    connectionLoading,
    connectionError,
    runConnectionSearch,
    clearConnectionPath,
    linkAnalysis,
    insights,
    timelineDateRange,
    setTimelineDateRange,
    reloadGraph: loadGraph,
    handleNeo4jSync,
  };
}
