/**
 * Deterministic parsing of the Network Analysis combined keyword search box
 * (issue #226).
 *
 * Given a free-text query such as `Theft Bengaluru` or `Theft + Bengaluru`, the
 * parser maps tokens that match (exactly or by first-word prefix) a known crime
 * type or district onto the corresponding structured filter, and treats
 * everything else as a criminal / suspect name term. This is a dictionary-based
 * mapping, deliberately NOT an NLP system — unknown terms simply fall through
 * to the name filter.
 */

export interface CombinedSearchResult {
  criminalName?: string;
  crimeTypes: string[];
  districts: string[];
  /** A bare 4-digit year token, e.g. `2025` in `Theft Bengaluru 2025`. */
  year?: string;
}

/** Split on whitespace, '+' and ',' so `Theft + Bengaluru` and `Theft,Bengaluru`
 *  behave identically. */
export function splitSearchTokens(query: string): string[] {
  return query
    .split(/[\s+,]+/)
    .map((token) => token.trim())
    .filter(Boolean);
}

/**
 * Resolve a free-text token to a known configured label.
 *
 * Two deterministic, dictionary-based rules (issue #226, NOT NLP):
 *  1. The token may equal the full label case-insensitively, e.g. `Theft &
 *     Burglaries`; or
 *  2. The token may be a prefix (min 3 chars) of the label's first word, so
 *     `Theft` resolves to `Theft & Burglaries` and `Bengaluru` to
 *     `Bengaluru Urban`.
 */
function matchKnownLabel(token: string, index: Map<string, string>): string | null {
  const lower = token.toLowerCase();
  if (index.has(lower)) {
    return index.get(lower) ?? null;
  }
  if (lower.length < 3) {
    return null;
  }
  for (const [key, label] of index) {
    const firstWord = key.split(/[&,]+/)[0].trim();
    if (firstWord.length >= 3 && firstWord.startsWith(lower)) {
      return label;
    }
  }
  return null;
}

export function parseCombinedSearch(
  query: string,
  knownCrimeTypes: string[],
  knownDistricts: string[]
): CombinedSearchResult {
  const trimmed = query.trim();
  const crimeTypeIndex = new Map(knownCrimeTypes.map((c) => [c.trim().toLowerCase(), c.trim()]));
  const districtIndex = new Map(knownDistricts.map((d) => [d.trim().toLowerCase(), d.trim()]));

  // A verbatim whole-query match (e.g. the full label `Theft & Burglaries`)
  // maps directly and leaves nothing for the name filter.
  if (trimmed) {
    const wholeCrime = crimeTypeIndex.get(trimmed.toLowerCase());
    const wholeDistrict = districtIndex.get(trimmed.toLowerCase());
    if (wholeCrime) {
      return { criminalName: undefined, crimeTypes: [wholeCrime], districts: [], year: undefined };
    }
    if (wholeDistrict) {
      return { criminalName: undefined, crimeTypes: [], districts: [wholeDistrict], year: undefined };
    }
    // A bare year (`2025`) is a time-window query, not a suspect's name.
    if (/^\d{4}$/.test(trimmed)) {
      return { criminalName: undefined, crimeTypes: [], districts: [], year: trimmed };
    }
  }

  const crimeTypes: string[] = [];
  const districts: string[] = [];
  const nameTerms: string[] = [];
  let year: string | undefined;
  const tokens = splitSearchTokens(trimmed);

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];

    // A 4-digit year token narrows the date window instead of the name filter,
    // so `Theft Bengaluru 2025` cannot silently target suspect "2025".
    if (/^\d{4}$/.test(token)) {
      if (!year) year = token;
      continue;
    }

    // Re-join `A & B` sequences so splittable multi-word labels stay intact.
    if (token === '&' && i > 0 && i < tokens.length - 1) {
      const combinedLabel = `${tokens[i - 1]} & ${tokens[i + 1]}`;
      const combinedCrime = matchKnownLabel(combinedLabel, crimeTypeIndex);
      const combinedDistrict = matchKnownLabel(combinedLabel, districtIndex);
      if (combinedCrime || combinedDistrict) {
        if (combinedCrime && !crimeTypes.includes(combinedCrime)) crimeTypes.push(combinedCrime);
        if (combinedDistrict && !districts.includes(combinedDistrict)) districts.push(combinedDistrict);
        i += 1;
        continue;
      }
    }

    const crime = matchKnownLabel(token, crimeTypeIndex);
    const district = matchKnownLabel(token, districtIndex);
    if (crime) {
      if (!crimeTypes.includes(crime)) crimeTypes.push(crime);
    } else if (district) {
      if (!districts.includes(district)) districts.push(district);
    } else {
      nameTerms.push(token);
    }
  }

  const criminalName = nameTerms.join(' ').trim();
  return {
    criminalName: criminalName || undefined,
    crimeTypes,
    districts,
    year: year || undefined,
  };
}

/** True when any of the search-derived or structured filters are active. */
export function hasActiveNetworkFilters(filters: {
  criminalName?: string;
  crimeTypes?: string[];
  districts?: string[];
  policeStations?: string[];
  firNumbers?: string[];
  victimName?: string;
  dateFrom?: string;
  dateTo?: string;
}): boolean {
  return Boolean(
    filters.criminalName ||
      (filters.crimeTypes?.length ?? 0) > 0 ||
      (filters.districts?.length ?? 0) > 0 ||
      (filters.policeStations?.length ?? 0) > 0 ||
      (filters.firNumbers?.length ?? 0) > 0 ||
      filters.victimName ||
      filters.dateFrom ||
      filters.dateTo
  );
}

/** Minimal structural shapes for path-highlighting / focus-subgraph helpers. */
export interface GraphEntityLike {
  id: string;
  name: string;
}
export interface GraphEdgeLike {
  source: string | { id: string };
  target: string | { id: string };
}
export interface NetworkPathHighlight {
  nodeIds: string[];
  linkKeys: string[];
}

export function edgeEndpointId(endpoint: string | { id: string }): string {
  return typeof endpoint === 'object' ? endpoint.id : endpoint;
}

/**
 * Issue #230: normalize a connection-path response into graph highlight inputs.
 * Path edges are undirected — two entities sharing an FIR — so every link key is
 * the canonical `min~max` pair regardless of the response's source/target order.
 */
export function buildNetworkPathHighlight(
  response: import('../services/api').NetworkPathResponse | null
): NetworkPathHighlight | null {
  if (!response || !response.found) return null;
  return {
    nodeIds: response.nodes.map((n) => n.id),
    linkKeys: (response.relationships ?? []).map((r) =>
      [String(r.source_id), String(r.target_id)].sort().join('~')
    ),
  };
}

/**
 * Issue #230 (focus mode): restrict a graph to the subgraph reachable within
 * `hops` undirected steps of `nodeId`. Zero/negative hops yields just the center
 * node; a hop count above the graph diameter returns the full graph.
 */
export function computeFocusSubgraph<TNode extends GraphEntityLike, TLink extends GraphEdgeLike>(
  graph: { nodes: TNode[]; links: TLink[] },
  nodeId: string,
  hops: number
): { nodes: TNode[]; links: TLink[] } {
  const keep = new Set<string>([nodeId]);
  for (let hop = 0; hop < Math.max(0, hops); hop++) {
    const additions: string[] = [];
    for (const link of graph.links) {
      const sId = edgeEndpointId(link.source);
      const tId = edgeEndpointId(link.target);
      if (keep.has(sId) && !keep.has(tId)) additions.push(tId);
      else if (keep.has(tId) && !keep.has(sId)) additions.push(sId);
    }
    additions.forEach((id) => keep.add(id));
    if (additions.length === 0) break;
  }
  return {
    nodes: graph.nodes.filter((n) => keep.has(n.id)),
    links: graph.links.filter(
      (l) => keep.has(edgeEndpointId(l.source)) && keep.has(edgeEndpointId(l.target))
    ),
  };
}