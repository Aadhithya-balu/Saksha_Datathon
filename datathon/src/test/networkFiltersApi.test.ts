import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getFullNetworkGraph } from '../services/api';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

describe('getFullNetworkGraph filter query building (issue #226)', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ nodes: [], edges: [] }), { status: 200 }));
  });

  it('omits query string when no filters are provided', async () => {
    await getFullNetworkGraph();
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v2/network/graph');
  });

  it('passes base (category / risk) filters with snake_case keys', async () => {
    await getFullNetworkGraph('suspect', 40);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v2/network/graph?category_filter=suspect&min_risk=40');
  });

  it('joins array filters into comma-separated client params', async () => {
    await getFullNetworkGraph(undefined, undefined, undefined, false, {
      crimeTypes: ['Theft & Burglaries', 'Narcotics'],
      districts: ['Bengaluru Urban'],
      policeStations: ['KR Puram', 'Whitefield'],
    });
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain('crime_type=Theft+%26+Burglaries%2CNarcotics');
    expect(url).toContain('district=Bengaluru+Urban');
    expect(url).toContain('police_station=KR+Puram%2CWhitefield');
  });

  it('passes name, case and date filter params', async () => {
    await getFullNetworkGraph(undefined, undefined, undefined, false, {
      criminalName: 'Ramu Swamy',
      firNumbers: ['FIR-2026-001'],
      victimName: 'Anita',
      dateFrom: '2026-01-01',
      dateTo: '2026-12-31',
    });
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain('criminal_name=Ramu+Swamy');
    expect(url).toContain('fir_number=FIR-2026-001');
    expect(url).toContain('victim_name=Anita');
    expect(url).toContain('date_from=2026-01-01');
    expect(url).toContain('date_to=2026-12-31');
  });

  it('drops empty arrays and empty strings from the query', async () => {
    await getFullNetworkGraph(undefined, undefined, undefined, false, {
      criminalName: '',
      crimeTypes: [],
      districts: undefined,
    });
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v2/network/graph?exclude_demo=false');
  });
});