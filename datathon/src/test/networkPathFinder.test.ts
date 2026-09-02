import { beforeEach, describe, expect, it, vi } from 'vitest';
import { findNetworkPath } from '../services/api';
import { buildNetworkPathHighlight, computeFocusSubgraph } from '../utils/networkSearch';
import type { NetworkPathResponse } from '../services/api';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

const EMPTY_PATH: NetworkPathResponse = {
  found: false,
  distance: 0,
  nodes: [],
  relationships: [],
  message: 'none',
};

describe('findNetworkPath request building (issue #230)', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(new Response(JSON.stringify(EMPTY_PATH), { status: 200 }));
  });

  it('sends source_id, target_id and max_hops with no filters', async () => {
    await findNetworkPath('A1', 'B2', 3);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v2/network/path?source_id=A1&target_id=B2&max_hops=3');
  });

  it('honors the requested max-hop limit', async () => {
    await findNetworkPath('A1', 'B9', 5);
    expect(fetchMock.mock.calls[0][0]).toContain('max_hops=5');
  });

  it('carries the active issue #226 filters into the request', async () => {
    await findNetworkPath('A1', 'B2', 3, {
      criminalName: 'Ramu Swamy',
      crimeTypes: ['Theft & Burglaries', 'Narcotics'],
      districts: ['Bengaluru Urban'],
      policeStations: ['KR Puram'],
      firNumbers: ['FIR-2026-001'],
      victimName: 'Anita',
      dateFrom: '2026-01-01',
      dateTo: '2026-12-31',
    });
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain('criminal_name=Ramu+Swamy');
    expect(url).toContain('crime_type=Theft+%26+Burglaries%2CNarcotics');
    expect(url).toContain('district=Bengaluru+Urban');
    expect(url).toContain('police_station=KR+Puram');
    expect(url).toContain('fir_number=FIR-2026-001');
    expect(url).toContain('victim_name=Anita');
    expect(url).toContain('date_from=2026-01-01');
    expect(url).toContain('date_to=2026-12-31');
  });

  it('drops empty filter values from the query string', async () => {
    await findNetworkPath('A1', 'B2', 3, {
      criminalName: '',
      crimeTypes: [],
      victimName: undefined,
    });
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v2/network/path?source_id=A1&target_id=B2&max_hops=3');
  });
});

describe('buildNetworkPathHighlight (issue #230)', () => {
  it('returns null when no response exists', () => {
    expect(buildNetworkPathHighlight(null)).toBeNull();
  });

  it('returns null when no connection was found', () => {
    expect(buildNetworkPathHighlight(EMPTY_PATH)).toBeNull();
  });

  it('extracts node ids and canonicalizes undirected edge keys', () => {
    const response: NetworkPathResponse = {
      found: true,
      distance: 2,
      nodes: [
        { id: 'A1', name: 'Alice', category: 'suspect' },
        { id: 'B2', name: 'Bob', category: 'victim' },
        { id: 'C3', name: 'Constable', category: 'officer' },
      ],
      relationships: [
        { source_id: 'A1', target_id: 'B2', relationship_type: 'shared_fir', relationship: '', fir_numbers: ['FIR-1'], case_numbers: [], crime_types: [], districts: [], stations: [], dates: [], roles: {} },
        // reversed order on the wire must collapse to the same undirected key
        { source_id: 'C3', target_id: 'B2', relationship_type: 'shared_fir', relationship: '', fir_numbers: ['FIR-2'], case_numbers: [], crime_types: [], districts: [], stations: [], dates: [], roles: {} },
      ],
      message: 'found',
    };
    const highlight = buildNetworkPathHighlight(response);
    expect(highlight).not.toBeNull();
    expect(highlight?.nodeIds).toEqual(['A1', 'B2', 'C3']);
    expect(highlight?.linkKeys).toEqual(['A1~B2', 'B2~C3']);
  });
});

describe('computeFocusSubgraph (issue #230)', () => {
  const nodes = [
    { id: 'A', name: 'A' },
    { id: 'B', name: 'B' },
    { id: 'C', name: 'C' },
    { id: 'D', name: 'D' },
  ];
  const links = [
    { source: 'A', target: 'B' },
    { source: 'B', target: 'C' },
    { source: 'C', target: 'D' },
  ];
  const graph = { nodes, links };

  it('includes only the center node at zero hops', () => {
    const sub = computeFocusSubgraph(graph, 'B', 0);
    expect(sub.nodes.map((n) => n.id)).toEqual(['B']);
    expect(sub.links).toEqual([]);
  });

  it('includes direct neighbors and their edges at one hop', () => {
    const sub = computeFocusSubgraph(graph, 'B', 1);
    expect(new Set(sub.nodes.map((n) => n.id))).toEqual(new Set(['A', 'B', 'C']));
    expect(sub.links).toHaveLength(2);
    // node D (2 hops away) must be excluded
    expect(sub.nodes.map((n) => n.id)).not.toContain('D');
  });

  it('reaches the second ring at two hops', () => {
    const sub = computeFocusSubgraph(graph, 'B', 2);
    expect(new Set(sub.nodes.map((n) => n.id))).toEqual(new Set(['A', 'B', 'C', 'D']));
    expect(sub.links).toHaveLength(3);
  });

  it('treats edges as undirected', () => {
    const sub = computeFocusSubgraph(graph, 'D', 1);
    expect(new Set(sub.nodes.map((n) => n.id))).toEqual(new Set(['C', 'D']));
  });

  it('returns an empty subgraph for an unknown center node', () => {
    const sub = computeFocusSubgraph(graph, 'ZZZ', 3);
    expect(sub.nodes).toEqual([]);
    expect(sub.links).toEqual([]);
  });
});