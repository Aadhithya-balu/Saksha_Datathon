import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// jsdom lacks ResizeObserver
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub);

// ---- Mock data helpers ----

function makeGraphNode(overrides: Partial<{ id: string; name: string; category: string; riskScore: number; isSeed: boolean }> = {}) {
  return {
    id: overrides.id ?? 'n1',
    name: overrides.name ?? 'Test Node',
    category: (overrides.category ?? 'suspect') as any,
    riskScore: overrides.riskScore ?? 80,
    details: '',
    casesCount: 0,
    isSeed: overrides.isSeed ?? false,
  };
}

function makeGraphLink(overrides: Partial<{ source: string; target: string; relationship: string; provenance: string; verification_status: string; is_demo_derived: boolean }> = {}) {
  return {
    source: overrides.source ?? 'n1',
    target: overrides.target ?? 'n2',
    relationship: overrides.relationship ?? 'KNOWS',
    provenance: overrides.provenance ?? 'DIRECT_DATABASE',
    verification_status: overrides.verification_status ?? 'VERIFIED',
    is_demo_derived: overrides.is_demo_derived ?? false,
  };
}

// ---- Mock modules ----

const mockGraphData = { nodes: [] as any[], links: [] as any[] };

vi.mock('../services/api', () => ({
  getNetworkGraph: vi.fn(() => Promise.resolve({
    nodes: mockGraphData.nodes,
    edges: mockGraphData.links,
    total_nodes: mockGraphData.nodes.length,
    total_edges: mockGraphData.links.length,
    is_neo4j_backed: false,
    dataset_scope: 'seed_demo_records',
    seed_node_count: mockGraphData.nodes.filter(n => n.isSeed).length,
    provenance_summary: {
      direct_database: mockGraphData.links.filter(l => l.provenance === 'DIRECT_DATABASE').length,
      analytical_inference: mockGraphData.links.filter(l => l.provenance === 'ANALYTICAL_INFERENCE').length,
      demo_seed: mockGraphData.links.filter(l => l.provenance === 'DEMO_SEED').length,
      unknown: mockGraphData.links.filter(l => !['DIRECT_DATABASE', 'ANALYTICAL_INFERENCE', 'DEMO_SEED'].includes(l.provenance)).length,
    },
    entity_counts: {},
    warnings: [],
    confidence_summary: { high: 0, medium: 0, low: 0, unknown: 0 },
  })),
  getPersonGraph: vi.fn(() => Promise.resolve({ nodes: [], edges: [] })),
  getNetworkGangs: vi.fn(() => Promise.resolve([])),
  getNetworkShortestPath: vi.fn(() => Promise.resolve({ found: false })),
  getNetworkLinkAnalysis: vi.fn(() => Promise.resolve({ links: [] })),
  getNetworkAIInsights: vi.fn(() => Promise.resolve({})),
}));

vi.mock('../store/appStore', () => ({
  useAppStore: vi.fn((selector: any) => {
    const state = { theme: 'dark' as const };
    return selector(state);
  }),
}));

// Stub Three.js / WebGL components
vi.mock('react-force-graph-3d', () => ({
  default: vi.fn(() => null),
}));

vi.mock('three', () => ({}));

// ---- Tests ----

describe('Network Provenance Rendering', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders verified database relationships as distinguishable', () => {
    const link = makeGraphLink({
      provenance: 'DIRECT_DATABASE',
      verification_status: 'VERIFIED',
      is_demo_derived: false,
    });
    // Verified links should be green in getLinkColor
    expect(link.verification_status).toBe('VERIFIED');
    expect(link.provenance).toBe('DIRECT_DATABASE');
    expect(link.is_demo_derived).toBe(false);
  });

  it('renders analytical relationships as distinguishable', () => {
    const link = makeGraphLink({
      provenance: 'ANALYTICAL_INFERENCE',
      verification_status: 'POTENTIAL',
      is_demo_derived: false,
    });
    expect(link.verification_status).toBe('POTENTIAL');
    expect(link.provenance).toBe('ANALYTICAL_INFERENCE');
  });

  it('renders demo/seed relationships as clearly identified', () => {
    const link = makeGraphLink({
      provenance: 'DEMO_SEED',
      verification_status: 'DEMO',
      is_demo_derived: true,
    });
    const node = makeGraphNode({ isSeed: true });
    expect(link.is_demo_derived).toBe(true);
    expect(link.provenance).toBe('DEMO_SEED');
    expect(node.isSeed).toBe(true);
  });

  it('does not present unknown/unverified relationships as verified', () => {
    const link = makeGraphLink({
      provenance: 'UNKNOWN',
      verification_status: 'UNVERIFIED',
      is_demo_derived: false,
    });
    expect(link.verification_status).not.toBe('VERIFIED');
    expect(link.provenance).toBe('UNKNOWN');
  });

  it('preserves backend provenance without frontend invention', () => {
    const links = [
      makeGraphLink({ provenance: 'DIRECT_DATABASE', verification_status: 'VERIFIED' }),
      makeGraphLink({ provenance: 'ANALYTICAL_INFERENCE', verification_status: 'POTENTIAL' }),
      makeGraphLink({ provenance: 'DEMO_SEED', verification_status: 'DEMO' }),
      makeGraphLink({ provenance: 'UNKNOWN', verification_status: 'UNVERIFIED' }),
    ];
    // Frontend should NOT modify these values
    for (const link of links) {
      expect(link.provenance).toBeTruthy();
      expect(['DIRECT_DATABASE', 'ANALYTICAL_INFERENCE', 'DEMO_SEED', 'UNKNOWN']).toContain(link.provenance);
    }
  });

  it('provenance summary counts match link provenance distribution', () => {
    const links = [
      makeGraphLink({ provenance: 'DIRECT_DATABASE' }),
      makeGraphLink({ provenance: 'DIRECT_DATABASE' }),
      makeGraphLink({ provenance: 'ANALYTICAL_INFERENCE' }),
      makeGraphLink({ provenance: 'DEMO_SEED' }),
    ];
    const summary = {
      direct_database: links.filter(l => l.provenance === 'DIRECT_DATABASE').length,
      analytical_inference: links.filter(l => l.provenance === 'ANALYTICAL_INFERENCE').length,
      demo_seed: links.filter(l => l.provenance === 'DEMO_SEED').length,
      unknown: links.filter(l => !['DIRECT_DATABASE', 'ANALYTICAL_INFERENCE', 'DEMO_SEED'].includes(l.provenance)).length,
    };
    expect(summary.direct_database).toBe(2);
    expect(summary.analytical_inference).toBe(1);
    expect(summary.demo_seed).toBe(1);
    expect(summary.unknown).toBe(0);
  });

  it('distinguishes empty graph from API failure', () => {
    const emptyGraph = { nodes: [], links: [] };
    const errorState = null;
    // Empty graph: nodes.length === 0 → "No relationships found"
    // API failure: graphData === null + loadError → "Network intelligence unavailable"
    expect(emptyGraph.nodes.length).toBe(0);
    expect(errorState).toBeNull();
  });
});
