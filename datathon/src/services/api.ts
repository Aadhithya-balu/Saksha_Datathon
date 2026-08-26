import type { UserRole } from '../store/authStore';

const DEFAULT_API_BASE_URL = '/api/v2';
const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.toString().trim();
const normalizedConfiguredApiBaseUrl = configuredApiBaseUrl && configuredApiBaseUrl !== ''
  ? configuredApiBaseUrl.replace(/\/+$/, '')
  : undefined;

export const API_BASE_URL = normalizedConfiguredApiBaseUrl ?? DEFAULT_API_BASE_URL;

export let isEmulatorActive = false;

export function setEmulatorActive(active: boolean) {
  if (isEmulatorActive !== active) {
    isEmulatorActive = active;
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('emulator-status-changed', { detail: active }));
    }
  }
}

const ACCESS_TOKEN_KEY = 'saksha_access_token';
const REFRESH_TOKEN_KEY = 'saksha_refresh_token';

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}


export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  results: T[];
}

export interface CrimeCaseRecord {
  id: string;
  case_number: string;
  category_id: string;
  location_id: string;
  occurred_at: string;
  reported_at: string;
  description: string | null;
  mo_tags: string | null;
  status: string;
  created_at: string;
}

export interface CriminalRecord {
  id: string;
  full_name: string;
  aliases: string | null;
  date_of_birth: string | null;
  gender: string | null;
  address: string | null;
  identifying_marks: string | null;
  mo_summary: string | null;
  status: string;
  created_at: string;
}

export interface OffenderDossier {
  id: string;
  name: string;
  alias: string;
  age: number;
  gender: string;
  classification: 'A-CATEGORY' | 'B-CATEGORY' | 'WATCHLIST';
  activeDistricts: string[];
  status: 'ACTIVE' | 'INCARCERATED' | 'UNDER_SURVEILLANCE';
  riskScore: number;
  gangAffiliation: string;
  mugshotDesc: string;
}

export interface OffenderDossiersResponse {
  offenders: OffenderDossier[];
}
export interface BackendUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  district: string | null;
  station: string | null;
  is_active: boolean;
  role: string;
  created_at: string;
}

export interface DashboardSummary {
  total_crimes: number;
  open_crimes: number;
  total_firs: number;
  total_criminals: number;
  resolution_rate_percent: number;
}

export interface TrendPoint {
  date: string;
  count: number;
}

export interface CategoryPoint {
  category: string;
  count: number;
}

export interface DistrictComparisonPoint {
  district: string;
  count: number;
}

export interface RiskScorePoint {
  district: string;
  risk_score: number;
  confidence?: number;
}

export interface RiskScoresResponse {
  district_id: string | null;
  window: string;
  grid_predictions: RiskScorePoint[];
  model_version: string;
  /** Authoritative status metadata (issue 9) — 'ML' | 'FALLBACK' | 'UNAVAILABLE' | ... */
  prediction_mode?: string;
  risk_model_loaded?: boolean | null;
  data_provenance?: string;
}

export interface HotspotPoint {
  district_id: string;
  name: string;
  lat: number;
  lng: number;
  score: number;
  category: string;
  trend: string;
}

export interface HotspotsResponse {
  hotspots: HotspotPoint[];
  hour?: number | null;
  /** Authoritative status metadata (issue 9). */
  analysis_mode?: string;
  data_provenance?: string;
  statistics?: {
    method?: string;
    locations_assessed?: number;
    incidents_assessed?: number;
    [key: string]: unknown;
  };
}

export interface StationSummary {
  district: string;
  station: string;
  lat: number;
  lng: number;
  total_cases: number;
  recent_30d: number;
  prior_30d: number;
  open_cases: number;
  top_category: string;
  top_category_count: number;
  trend: 'up' | 'down' | 'stable';
  last_incident_at: string | null;
  risk_score: number;
}

export interface StationsSummaryResponse {
  stations: StationSummary[];
  count: number;
  source: string;
}

export interface RedZone {
  district: string;
  category: string;
  current_count: number;
  baseline_count: number;
  spike_ratio: number;
  severity: 'high' | 'critical';
  stations: string[];
  window: string;
}

export interface RedZonesResponse {
  generated_at: string;
  thresholds: { min_current: number; ratio_threshold: number };
  red_zones: RedZone[];
}

export interface RedZoneNotifyResponse {
  status: string;
  zones_detected: number;
  created: number;
  skipped: number;
  broadcast_by: string;
}

export interface AnomalyRecord {
  case_id: string;
  case_uuid?: string;
  case_number?: string;
  district?: string | null;
  station?: string | null;
  category?: string | null;
  filed_at?: string | null;
  label: string;
  score: number;
  reason: string;
}

export interface AnomaliesResponse {
  anomalies: AnomalyRecord[];
}

export type NetworkNodeCategory = 'suspect' | 'offender' | 'case' | 'location' | 'victim' | 'gang' | 'vehicle' | 'weapon' | 'officer';

export interface NetworkNode {
  id: string;
  name: string;
  category: NetworkNodeCategory;
  riskScore: number;
  details: string;
  casesCount: number;
  phone?: string | null;
  gangAffiliation?: string | null;
  status?: string | null;
  district?: string | null;
  date?: string | null;
  lat?: number | null;
  lng?: number | null;
  extra?: Record<string, any>;
  /** True when the record originates from the bundled demo seed dataset (gap 132.4). */
  isSeed?: boolean;
}

export interface RelationshipEvidenceItem {
  record_type?: string;
  record_id?: string;
  record_number?: string;
  details?: string;
  timestamp?: string | null;
  sections?: string;
  factors?: string[];
}

export interface NetworkEdge {
  source: string;
  target: string;
  relationship: string;
  weight?: number;
  first_seen?: string | null;
  last_seen?: string | null;
  provenance?: 'DIRECT_DATABASE' | 'ANALYTICAL_INFERENCE' | 'DEMO_SEED' | 'MIXED' | 'UNKNOWN' | string;
  verification_status?: 'VERIFIED' | 'POTENTIAL' | 'UNVERIFIED' | 'DEMO' | string;
  relationship_type?: string;
  evidence?: RelationshipEvidenceItem[];
  confidence?: number | null;
  confidence_level?: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN' | string;
  is_demo_derived?: boolean;
  operational_warning?: string | null;
}

export interface ProvenanceSummary {
  total_nodes: number;
  total_edges: number;
  verified_relationships: number;
  analytical_relationships: number;
  potential_relationships: number;
  demo_relationships: number;
  mixed_relationships: number;
  unknown_relationships: number;
}

export interface NetworkResponse {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export interface NetworkGraphResponse {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  total_nodes: number;
  total_edges: number;
  is_neo4j_backed: boolean;
  seed_node_count?: number;
  dataset_scope?: 'live_records' | 'contains_seed_demo_records' | string;
  provenance_summary?: ProvenanceSummary;
  entity_counts?: Record<string, number>;
  warnings?: string[];
  confidence_summary?: Record<string, number>;
}

export interface GangHierarchyMember {
  id: string;
  name: string;
  role: string;
  rank_level: number;
  riskScore: number;
  status: string;
  casesCount: number;
  isSeed?: boolean;
}

export interface GangNetworkSummary {
  gang_id: string;
  name: string;
  leader_name: string;
  leader_id?: string | null;
  active_members: number;
  risk_level: string;
  territory: string;
  primary_racket: string;
  members: GangHierarchyMember[];
  relationships: NetworkEdge[];
  is_demo_derived?: boolean;
}

export interface ShortestPathResult {
  found: boolean;
  distance: number;
  path_nodes: NetworkNode[];
  path_edges: NetworkEdge[];
  explanation: string;
}

export interface CentralityMetric {
  node_id: string;
  node_name: string;
  category: string;
  degree_centrality: number;
  betweenness_score: number;
  is_bridge_node: boolean;
  riskScore: number;
}

export interface LinkAnalysisData {
  graph_density: number;
  total_clusters: number;
  top_broker_nodes: CentralityMetric[];
  high_impact_nodes: CentralityMetric[];
  bridge_nodes: CentralityMetric[];
}

export interface AIGraphInsightData {
  id: string;
  insight_type: string;
  title: string;
  description: string;
  threat_level: string;
  target_node_ids: string[];
  recommendation: string;
  timestamp: string;
}

export interface ChatCitation {
  source: string;
  title: string;
  score: number;
}

export interface ChatQueryResponse {
  answer: string;
  data: Array<Record<string, unknown>>;
  sources: string[];
  chart_suggestion: string | null;
  citations?: ChatCitation[];
  summary?: string;
  entities?: string[];
  classification?: string;
  engine?: string | null;
}

/* --- Persistent AI chat history --- */

export interface ChatHistoryMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  classification?: string | null;
  sources?: string[] | null;
  citations?: ChatCitation[] | null;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  is_temporary: boolean;
  message_count: number;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: ChatHistoryMessage[];
  total_messages: number;
}

export interface ConversationListResponse {
  items: ConversationSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateConversationPayload {
  title?: string;
  temporary?: boolean;
  messages?: Array<{
    role: 'user' | 'assistant';
    content: string;
    classification?: string;
    sources?: string[];
    citations?: ChatCitation[];
  }>;
}

export interface ReportRecord {
  id: string;
  template: string;
  district: string | null;
  status: string;
  format: string;
  file_url: string | null;
  created_at: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

const hasWindow = typeof window !== 'undefined';

// Security: tokens are kept in sessionStorage (per-tab, cleared when the
// browser tab closes) rather than localStorage (indefinite persistence).
// This shrinks the XSS theft window. The Bearer-token architecture keeps the
// API immune to CSRF, so no cookie-based auth is used.
export const getStoredTokens = (): AuthTokens => ({
  accessToken: hasWindow ? window.sessionStorage.getItem(ACCESS_TOKEN_KEY) ?? '' : '',
  refreshToken: hasWindow ? window.sessionStorage.getItem(REFRESH_TOKEN_KEY) ?? '' : '',
});

export const setStoredTokens = (tokens: AuthTokens) => {
  if (!hasWindow) {
    return;
  }

  window.sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
  window.sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
};

export const clearStoredTokens = () => {
  if (!hasWindow) {
    return;
  }

  window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  window.sessionStorage.removeItem(REFRESH_TOKEN_KEY);
};

export const mapBackendRoleToUiRole = (role: string): UserRole => {
  switch (role) {
    case 'admin':
      return 'ADMIN';
    case 'crime_analyst':
      return 'SCRB';
    case 'investigator':
      return 'IO';
    case 'inspector':
      return 'INSPECTOR';
    case 'policymaker':
      return 'SP';
    case 'forensic':
      return 'FORENSIC';
    case 'viewer':
      return 'VIEWER';
    default:
      return 'SCRB';
  }
};

const buildQueryString = (params?: Record<string, string | number | boolean | null | undefined>) => {
  if (!params) {
    return '';
  }

  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === '') {
      return;
    }

    searchParams.set(key, String(value));
  });

  const query = searchParams.toString();
  return query ? `?${query}` : '';
};

const readErrorMessage = async (response: Response) => {
  try {
    const payload = await response.json();
    if (payload?.error?.message) return String(payload.error.message);
    const detail = payload?.detail;
    if (!detail) return payload?.message || response.statusText;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((err: any) => {
        const field = err.loc && err.loc.length > 1 ? err.loc.slice(1).join('.') : '';
        return `${field ? `Field '${field}': ` : ''}${err.msg || 'Invalid value'}`;
      }).join('; ');
    }
    if (typeof detail === 'object') return JSON.stringify(detail);
    return String(detail);
  } catch {
    return response.statusText;
  }
};

export async function apiRequest<T>(path: string, options: RequestInit = {}, includeAuth = true): Promise<T> {
  const { accessToken } = getStoredTokens();

  const headers = new Headers(options.headers ?? {});

  if (includeAuth && accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && !path.startsWith('/auth/')) {
    clearStoredTokens();
    window.dispatchEvent(new CustomEvent('auth:session-expired'));
    throw new Error('Session expired. Please log in again.');
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
export async function login(username: string, password: string) {
  return apiRequest<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  }, false);
}

export async function logout() {
  // Send the refresh token so the backend can revoke it server-side
  // (rotation denylist) before the client discards its copy.
  const { refreshToken } = getStoredTokens();
  try {
    return await apiRequest<{ message: string }>('/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken || null }),
    });
  } finally {
    clearStoredTokens();
  }
}

export async function refreshSession(refreshToken: string) {
  return apiRequest<LoginResponse>('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  }, false);
}

export async function getMe() {
  return apiRequest<BackendUser>('/auth/me');
}

export async function updateProfile(payload: {
  full_name?: string;
  email?: string;
  district?: string;
  station?: string;
}) {
  return apiRequest<BackendUser>('/auth/profile', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function changePassword(oldPassword: string, newPassword: string) {
  return apiRequest<{ message: string }>('/auth/change-password', {
    method: 'PUT',
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
}

export interface DashboardFilters {
  date_from?: string;
  date_to?: string;
  district?: string;
  category_id?: string;
  officer_id?: string;
  priority?: string;
  status?: string;
}

export interface OfficerStats {
  total_officers: number;
  active_officers: number;
  on_duty: number;
  off_duty: number;
  investigating_officers: number;
}

export interface EvidenceStats {
  collected: number;
  pending: number;
  verified: number;
  rejected: number;
}

export interface RecentIncident {
  case_number: string;
  crime_type: string;
  location: string;
  time: string | null;
  status: string;
  priority: string;
}

export interface ForecastPoint {
  day: string;
  value: number;
  type: 'historical' | 'predicted' | 'today';
  color: number;
  hexColor: string;
}

export interface ForecastResponse {
  next_day_forecast: number;
  next_week_forecast: number;
  expected_change_percent: number;
  trend_direction: 'up' | 'down' | 'stable';
  series: ForecastPoint[];
}

export interface RiskPredictionResponse {
  crime_risk_percent: number;
  threat_level: 'Low' | 'Medium' | 'High' | 'Critical';
  trend: 'increasing' | 'decreasing' | 'stable';
  confidence_score: number;
  prediction_time: string;
}

export async function getDashboardSummary(filters?: DashboardFilters) {
  return apiRequest<DashboardSummary>(`/dashboard/summary${buildQueryString(filters as any)}`);
}

export async function getCrimeTrends(filters?: DashboardFilters) {
  return apiRequest<TrendPoint[]>(`/dashboard/crime-trends${buildQueryString(filters as any)}`);
}

export async function getCategoryBreakdown(filters?: DashboardFilters) {
  return apiRequest<CategoryPoint[]>(`/dashboard/category-breakdown${buildQueryString(filters as any)}`);
}

export async function getDistrictComparison(filters?: DashboardFilters) {
  return apiRequest<DistrictComparisonPoint[]>(`/dashboard/district-comparison${buildQueryString(filters as any)}`);
}

export async function getOfficerStats() {
  return apiRequest<OfficerStats>('/dashboard/officer-stats');
}

export async function getEvidenceStats() {
  return apiRequest<EvidenceStats>('/dashboard/evidence-stats');
}

export async function getRecentIncidents() {
  return apiRequest<RecentIncident[]>('/dashboard/recent-incidents');
}

export async function getForecast() {
  return apiRequest<ForecastResponse>('/dashboard/forecast');
}

export async function getRiskPrediction() {
  return apiRequest<RiskPredictionResponse>('/dashboard/risk-prediction');
}

export async function getRiskScores(window = 'next_7d', districtId?: string) {
  return apiRequest<RiskScoresResponse>(`/ai/predictions/risk-scores${buildQueryString({ window, district_id: districtId })}`);
}

export async function getHotspots(districtId?: string, hour?: number) {
  return apiRequest<HotspotsResponse>(`/ai/hotspots${buildQueryString({ district_id: districtId, hour })}`);
}

export async function getAnomalies() {
  return apiRequest<AnomaliesResponse>('/ai/predictions/anomalies');
}

export async function getStationsSummary(params?: { district?: string; q?: string }) {
  return apiRequest<StationsSummaryResponse>(`/stations/summary${buildQueryString({ district: params?.district, q: params?.q })}`);
}

export async function getRedZones(minCurrent = 3, ratioThreshold = 1.5) {
  return apiRequest<RedZonesResponse>(`/alerts/red-zones${buildQueryString({ min_current: minCurrent, ratio_threshold: ratioThreshold })}`);
}

export async function broadcastRedZones(minCurrent = 3, ratioThreshold = 1.5) {
  return apiRequest<RedZoneNotifyResponse>(`/alerts/red-zones/notify${buildQueryString({ min_current: minCurrent, ratio_threshold: ratioThreshold })}`, { method: 'POST' });
}

export async function getNetworkPerson(
  personId: string,
  depth = 1,
  provenanceFilter?: string,
  excludeDemo?: boolean
) {
  return apiRequest<NetworkGraphResponse>(
    `/network/person/${encodeURIComponent(personId)}${buildQueryString({
      depth,
      provenance_filter: provenanceFilter,
      exclude_demo: excludeDemo,
    })}`
  );
}

export interface NetworkSearchResult {
  id: string;
  type: 'criminal' | 'victim' | 'officer' | 'case' | 'location';
  name: string;
  detail: string;
  status?: string;
  risk_score?: number;
}

export async function searchNetworkEntities(query: string, limit = 20) {
  return apiRequest<{ results: NetworkSearchResult[]; query: string; total: number }>(
    `/network/search${buildQueryString({ q: query, limit })}`
  );
}

export async function getNetworkCase(
  caseId: string,
  provenanceFilter?: string,
  excludeDemo?: boolean
) {
  return apiRequest<NetworkGraphResponse>(
    `/network/case/${encodeURIComponent(caseId)}${buildQueryString({
      provenance_filter: provenanceFilter,
      exclude_demo: excludeDemo,
    })}`
  );
}

export async function getFullNetworkGraph(
  categoryFilter?: string,
  minRisk?: number,
  provenanceFilter?: string,
  excludeDemo?: boolean
) {
  return apiRequest<NetworkGraphResponse>(
    `/network/graph${buildQueryString({
      category_filter: categoryFilter,
      min_risk: minRisk,
      provenance_filter: provenanceFilter,
      exclude_demo: excludeDemo,
    })}`
  );
}

export async function getGangNetworks() {
  return apiRequest<GangNetworkSummary[]>('/network/gangs');
}

export async function calculateShortestPath(sourceId: string, targetId: string, maxDepth = 5) {
  return apiRequest<ShortestPathResult>('/network/shortest-path', {
    method: 'POST',
    body: JSON.stringify({ source_id: sourceId, target_id: targetId, max_depth: maxDepth }),
  });
}

export async function getLinkAnalysis() {
  return apiRequest<LinkAnalysisData>('/network/link-analysis', {
    method: 'POST',
  });
}

export async function getAIGraphInsights() {
  return apiRequest<AIGraphInsightData[]>('/network/insights');
}

export async function triggerNeo4jSync() {
  return apiRequest<{ status: string; message: string; neo4j_active: boolean }>('/network/sync-neo4j', {
    method: 'POST',
  });
}

export async function chatQuery(message: string, sessionId?: string, options?: { conversationId?: string | null; persist?: boolean }) {
  return apiRequest<ChatQueryResponse>('/ai/chat/query', {
    method: 'POST',
    body: JSON.stringify({
      message,
      session_id: sessionId ?? null,
      conversation_id: options?.conversationId ?? null,
      persist: options?.persist ?? true,
    }),
  });
}

/** Optional entity scoping for AI chat answers (selected via the chat UI). */
export interface ChatContextOptions {
  firId?: string;
  criminalId?: string;
  evidenceId?: string;
  caseId?: string;
}

export interface ChatStreamChunk {
  type: 'status' | 'token' | 'final' | 'error' | 'meta' | 'notice';
  content: any;
}

export interface ChatStreamOptions {
  conversationId?: string | null;
  persist?: boolean;
}

export async function* chatQueryStream(
  message: string,
  sessionId?: string,
  options?: ChatStreamOptions,
): AsyncGenerator<ChatStreamChunk, void, unknown> {
  const { accessToken: token } = getStoredTokens();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}/ai/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message,
      session_id: sessionId ?? null,
      stream: true,
      conversation_id: options?.conversationId ?? null,
      persist: options?.persist ?? true,
    }),
  });

  if (!response.ok) {
    const errText = await response.text().catch(() => 'Unknown error');
    throw new Error(`Chat API error ${response.status}: ${errText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('Response body is not readable');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const chunk: ChatStreamChunk = JSON.parse(trimmed);
        yield chunk;
      } catch {
        // skip malformed lines
      }
    }
  }

  if (buffer.trim()) {
    try {
      const chunk: ChatStreamChunk = JSON.parse(buffer.trim());
      yield chunk;
    } catch {
      // ignore
    }
  }
}

/* --- Conversation history management --- */

export async function listConversations(params?: { q?: string; limit?: number; offset?: number }) {
  return apiRequest<ConversationListResponse>(`/ai/chat-history/conversations${buildQueryString(params)}`);
}

export async function getConversation(id: string, params?: { limit?: number; offset?: number }) {
  return apiRequest<ConversationDetail>(`/ai/chat-history/conversations/${id}${buildQueryString(params)}`);
}

export async function createConversation(payload: CreateConversationPayload = {}) {
  return apiRequest<ConversationDetail>('/ai/chat-history/conversations', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateConversation(
  id: string,
  payload: { title?: string; is_temporary?: boolean },
) {
  return apiRequest<ConversationSummary>(`/ai/chat-history/conversations/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteConversation(id: string) {
  return apiRequest<void>(`/ai/chat-history/conversations/${id}`, { method: 'DELETE' });
}

export async function deleteAllConversations() {
  return apiRequest<{ deleted: number }>('/ai/chat-history/conversations', { method: 'DELETE' });
}

export async function appendConversationMessage(
  id: string,
  payload: {
    role: 'user' | 'assistant';
    content: string;
    classification?: string;
    sources?: string[];
    citations?: ChatCitation[];
  },
) {
  return apiRequest<ChatHistoryMessage>(`/ai/chat-history/conversations/${id}/messages`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function listCrimes(page = 1, pageSize = 100) {
  return apiRequest<PaginatedResponse<CrimeCaseRecord>>(`/crimes${buildQueryString({ page, page_size: pageSize })}`);
}

export async function listCriminals(q?: string, page = 1, pageSize = 100) {
  return apiRequest<PaginatedResponse<CriminalRecord>>(`/criminals${buildQueryString({ q, page, page_size: pageSize })}`);
}

export async function getCriminal(criminalId: string) {
  return apiRequest<CriminalRecord & {
    firs: Array<{ id: string; fir_number: string; complainant_name: string; status: string; filed_at: string | null; sections: string | null; crime_case_id: string | null; crime_case_number: string | null }>;
    ai_risk: { risk_score: number; risk_band: string; confidence: number; top_factors: string[] };
    ai_repeat: { will_reoffend: boolean; probability: number; risk_factors: string[] };
    ai_similar: { similar: Array<{ criminal_id: string; name: string; similarity: number; rank: number; matching_factors: string[]; match_level: string }> };
    ai_recommendations: string[];
    network: { nodes: NetworkNode[]; edges: NetworkEdge[] };
    neo4j_node_id: string | null;
    gang_affiliation: string | null;
    image_url: string | null;
  }>(`/criminals/${criminalId}`);
}

export async function getOffenderDossiers() {
  return apiRequest<OffenderDossiersResponse>('/ai/offenders/dossiers');
}

export async function listReports(page = 1, pageSize = 100) {
  return apiRequest<PaginatedResponse<ReportRecord>>(`/reports${buildQueryString({ page, page_size: pageSize })}`);
}

// --- Crime Case Management Types & Routes ---

export interface InvestigationNote {
  id: string;
  officer_name: string;
  officer_badge: string;
  created_at: string;
  content: string;
}

export interface TimelineEvent {
  timestamp: string;
  event: string;
  actor: string | null;
}

export interface AIRecommendation {
  type: string;
  title: string;
  description: string;
}

export interface CrimeCaseDetailRecord extends CrimeCaseRecord {
  priority: string;
  progress: number;
  assigned_officer_id: string | null;
  assigned_officer?: {
    id: string;
    badge_number: string;
    rank: string | null;
    full_name: string;
  } | null;
  notes: InvestigationNote[];
  timeline: TimelineEvent[];
  firs: Array<{
    id: string;
    fir_number: string;
    complainant_name: string;
    sections: string | null;
    status: string;
    filed_at: string;
  }>;
  ai_recommendations: AIRecommendation[];
}

export interface OfficerWithUserRecord {
  id: string;
  user_id: string;
  badge_number: string;
  rank: string | null;
  district: string;
  station: string;
  created_at: string;
  full_name: string;
}

// FIR Lifecycle Management additions
export interface FIRRecord {
  id: string;
  fir_number: string;
  crime_case_id: string;
  investigating_officer_id: string | null;
  complainant_name: string;
  complainant_contact: string | null;
  sections: string | null;
  narrative: string | null;
  status: 'registered' | 'in_progress' | 'closed';
  filed_at: string;
  created_at: string;
  attachments?: Array<{ name: string; size: number }>;
}

export interface FIRDetailRecord extends FIRRecord {
  crime_case: CrimeCaseRecord | null;
  investigating_officer: OfficerRecord | null;
  criminals: CriminalRecord[];
  victims: VictimRecord[];
  evidence: FIDEvidenceRecord[];
  attachments: Array<{ name: string; size: number }>;
  ai_risk_score: number;
  ai_analysis_reasons: string[];
}

/** Evidence item embedded in a FIR detail response (mirrors backend EvidenceOut). */
export interface FIDEvidenceRecord {
  id: string;
  case_id: string;
  title: string;
  evidence_type: string;
  description: string | null;
  status: string;
  created_by: string | null;
  assigned_to: string | null;
  storage_path: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface OfficerRecord {
  id: string;
  user_id: string;
  badge_number: string;
  rank: string | null;
  district: string;
  station: string;
  created_at: string;
}

export interface VictimRecord {
  id: string;
  full_name: string;
  contact_number: string | null;
  address: string | null;
  gender: string | null;
  age: number | null;
  statement: string | null;
  created_at: string;
}

export interface CrimeCategoryRecord {
  id: string;
  name: string;
  section_code: string | null;
  severity: string | null;
}

export interface LocationSimpleRecord {
  id: string;
  district: string;
  station: string;
  pincode: string | null;
}

export interface FIRListQueryParams {
  status?: string;
  section?: string;
  search?: string;
  district?: string;
  officer_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

export interface CrimeCaseListFilters {
  category_id?: string;
  district?: string;
  priority?: string;
}

export async function getCrimeCases(
  q?: string,
  status?: string,
  page = 1,
  pageSize = 20,
  filters?: CrimeCaseListFilters,
) {
  return apiRequest<PaginatedResponse<CrimeCaseDetailRecord>>(
    `/crime-cases${buildQueryString({
      q,
      status,
      page,
      page_size: pageSize,
      ...(filters ?? {}),
    })}`,
  );
}

export async function getCrimeCase(caseId: string) {
  return apiRequest<CrimeCaseDetailRecord>(`/crime-cases/${caseId}`);
}

export async function createCrimeCase(payload: Omit<CrimeCaseRecord, 'id' | 'reported_at' | 'created_at'>) {
  return apiRequest<CrimeCaseRecord>('/crime-cases', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateCrimeCase(caseId: string, payload: Partial<CrimeCaseRecord> & { priority?: string; progress?: number; assigned_officer_id?: string | null }) {
  return apiRequest<CrimeCaseRecord>(`/crime-cases/${caseId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteCrimeCase(caseId: string) {
  return apiRequest<{ message: string }>(`/crime-cases/${caseId}`, {
    method: 'DELETE',
  });
}

export async function listFIRs(params?: FIRListQueryParams) {
  return apiRequest<PaginatedResponse<FIRRecord>>(`/firs${buildQueryString(params as any)}`);
}

export async function getFIR(firId: string) {
  return apiRequest<FIRDetailRecord>(`/firs/${firId}`);
}

export async function createFIR(data: {
  fir_number: string;
  crime_case_id: string;
  investigating_officer_id?: string | null;
  complainant_name: string;
  complainant_contact?: string | null;
  sections?: string | null;
  narrative?: string | null;
  status?: string;
  criminal_ids?: string[];
  victim_ids?: string[];
  attachments?: Array<{ name: string; size: number }>;
}) {
  return apiRequest<FIRRecord>('/firs', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateFIR(firId: string, data: {
  investigating_officer_id?: string | null;
  status?: string | null;
  narrative?: string | null;
  sections?: string | null;
  complainant_name?: string | null;
  complainant_contact?: string | null;
  criminal_ids?: string[] | null;
  victim_ids?: string[] | null;
  attachments?: Array<{ name: string; size: number }> | null;
}) {
  return apiRequest<FIRRecord>(`/firs/${firId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteFIR(firId: string) {
  return apiRequest<{ message: string }>(`/firs/${firId}`, {
    method: 'DELETE',
  });
}

export async function addInvestigationNote(caseId: string, content: string) {
  return apiRequest<{ message: string; content: string }>(`/crime-cases/${caseId}/notes`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

export async function deleteInvestigationNote(caseId: string, noteId: string) {
  return apiRequest<{ message: string }>(`/crime-cases/${caseId}/notes/${noteId}`, {
    method: 'DELETE',
  });
}

export async function linkFIRs(caseId: string, firIds: string[]) {
  return apiRequest<{ message: string }>(`/crime-cases/${caseId}/link-firs`, {
    method: 'POST',
    body: JSON.stringify({ fir_ids: firIds }),
  });
}

export async function getUnassignedOfficers() {
  return apiRequest<OfficerWithUserRecord[]>('/crime-cases/unassigned-officers');
}

export async function getUnlinkedFIRs() {
  return apiRequest<Array<{ id: string; fir_number: string; crime_case_id: string; complainant_name: string; sections: string | null; status: string; filed_at: string }>>('/crime-cases/unlinked-firs');
}

export async function getCrimeCategories() {
  return apiRequest<CrimeCategoryRecord[]>('/crime-cases/categories');
}

export async function getLocationsList() {
  return apiRequest<LocationSimpleRecord[]>('/crime-cases/locations');
}

export async function listOfficers(page = 1, pageSize = 100) {
  return apiRequest<PaginatedResponse<OfficerRecord>>(`/officers${buildQueryString({ page, page_size: pageSize })}`);
}

// Issue #107: person image upload helpers
export async function uploadCriminalImage(criminalId: string, file: File) {
  const form = new FormData();
  form.append('file', file);
  return apiRequest<{ image_url: string }>(`/criminals/${criminalId}/image`, { method: 'POST', body: form });
}

export async function uploadVictimImage(victimId: string, file: File) {
  const form = new FormData();
  form.append('file', file);
  return apiRequest<{ image_url: string }>(`/victims/${victimId}/image`, { method: 'POST', body: form });
}

export async function uploadOfficerImage(officerId: string, file: File) {
  const form = new FormData();
  form.append('file', file);
  return apiRequest<{ image_url: string }>(`/officers/${officerId}/image`, { method: 'POST', body: form });
}

export async function listVictims(q?: string, page = 1, pageSize = 100) {
  return apiRequest<PaginatedResponse<VictimRecord>>(`/victims${buildQueryString({ q, page, page_size: pageSize })}`);
}

export async function getVictim(victimId: string) {
  return apiRequest<VictimRecord & {
    firs: Array<{ id: string; fir_number: string; status: string; filed_at: string | null }>;
    image_url: string | null;
  }>(`/victims/${victimId}`);
}

// ── Unified Investigation Interface ──

export interface InvestigationOfficer {
  id: string;
  badge_number: string;
  rank: string | null;
  full_name: string;
  district: string;
  station: string;
}

export interface InvestigationCase {
  id: string;
  case_number: string;
  description: string | null;
  mo_tags: string | null;
  status: string;
  priority: string;
  progress: number;
  occurred_at: string;
  reported_at: string;
  created_at: string;
  assigned_officer: InvestigationOfficer | null;
}

export interface InvestigationFIR {
  id: string;
  fir_number: string;
  complainant_name: string;
  complainant_contact: string | null;
  sections: string | null;
  status: string;
  filed_at: string;
  narrative: string | null;
  criminals: Array<{ id: string; full_name: string; aliases: string | null; status: string }>;
  victims: Array<{ id: string; full_name: string; contact_number: string | null; gender: string | null; age: number | null; statement: string | null }>;
}

export interface InvestigationCriminal {
  id: string;
  full_name: string;
  aliases: string | null;
  gender: string | null;
  date_of_birth: string | null;
  identifying_marks: string | null;
  mo_summary: string | null;
  status: string;
  risk_score: number;
  linked_fir_count: number;
}

export interface InvestigationEvidence {
  id: string;
  evidence_type: string;
  description: string | null;
  file_url: string | null;
  collected_by: string | null;
  chain_of_custody: string | null;
  created_at: string;
}

export interface InvestigationTimelineEvent {
  timestamp: string;
  event: string;
  actor: string | null;
  category: string;
}

export interface InvestigationAIRecommendation {
  type: string;
  title: string;
  description: string;
  priority: string;
}

export interface InvestigationHistoryEntry {
  timestamp: string;
  action: string;
  resource_type: string;
  details: string | null;
  officer_name: string | null;
  officer_badge: string | null;
}

export interface InvestigationData {
  case: InvestigationCase;
  firs: InvestigationFIR[];
  criminals: InvestigationCriminal[];
  evidence: InvestigationEvidence[];
  timeline: InvestigationTimelineEvent[];
  ai_recommendations: InvestigationAIRecommendation[];
  history: InvestigationHistoryEntry[];
}

export async function getInvestigation(caseId: string) {
  return apiRequest<InvestigationData>(`/investigation/${caseId}`);
}

export async function getInvestigationTimeline(caseId: string) {
  return apiRequest<InvestigationTimelineEvent[]>(`/investigation/${caseId}/timeline`);
}

export async function getInvestigationHistory(caseId: string) {
  return apiRequest<InvestigationHistoryEntry[]>(`/investigation/${caseId}/history`);
}

export async function investigationChat(caseId: string, message: string, sessionId?: string) {
  return apiRequest<{ answer: string; sources: string[]; citations?: ChatCitation[] }>(`/investigation/chat`, {
    method: 'POST',
    body: JSON.stringify({ case_id: caseId, message, session_id: sessionId ?? null }),
  });
}

// ── Notification Types & Routes ──

export interface NotificationRecord {
  id: string;
  user_id: string | null;
  sender_id: string | null;
  sender_name: string | null;
  sender_badge: string | null;
  recipient_name: string | null;
  subject: string;
  notification_type: string;
  category: string;
  title: string;
  message: string;
  severity: string;
  priority: string;
  status: string;
  resource_type: string | null;
  resource_id: string | null;
  related_case_number: string | null;
  related_fir_number: string | null;
  is_read: boolean;
  is_dismissed: boolean;
  is_broadcast: boolean;
  parent_id: string | null;
  attachment_url: string | null;
  created_at: string;
  read_at: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

export interface NotificationCount {
  total: number;
  unread: number;
  critical: number;
}

export interface NotificationListResponse {
  total: number;
  page: number;
  page_size: number;
  unread_count: number;
  results: NotificationRecord[];
}

export interface NotificationDashboardSummary {
  unread_count: number;
  critical_alerts: number;
  today_messages: number;
  pending_acknowledgements: number;
  investigation_requests: number;
  broadcast_messages: number;
}

export interface ActivityEvent {
  id: string;
  timestamp: string;
  event_type: string;
  title: string;
  description: string;
  actor: string | null;
  actor_badge: string | null;
  resource_type: string;
  resource_id: string | null;
  severity: string;
}

export interface ActivityFeedResponse {
  total: number;
  results: ActivityEvent[];
}

export interface ServiceStatus {
  name: string;
  status: string;
  latency_ms: number;
  last_check: string;
  details: string | null;
}

export interface SystemHealthResponse {
  overall: string;
  services: ServiceStatus[];
  uptime_hours: number;
  last_updated: string;
}

export async function getNotifications(
  page = 1,
  pageSize = 20,
  unreadOnly = false,
  notificationType?: string,
  severity?: string,
  priority?: string,
  category?: string,
  status?: string,
  senderId?: string,
  search?: string,
) {
  return apiRequest<NotificationListResponse>(`/notifications${buildQueryString({
    page,
    page_size: pageSize,
    unread_only: unreadOnly,
    notification_type: notificationType,
    severity,
    priority,
    category,
    status,
    sender_id: senderId,
    search,
  } as any)}`);
}

export async function getNotificationCount() {
  return apiRequest<NotificationCount>('/notifications/count');
}

export async function getRecentNotifications(limit = 5) {
  return apiRequest<NotificationRecord[]>(`/notifications/recent${buildQueryString({ limit })}`);
}

export async function getNotificationDashboard() {
  return apiRequest<NotificationDashboardSummary>('/notifications/dashboard');
}

export async function createNotification(payload: {
  recipient_id?: string | null;
  subject: string;
  notification_type?: string;
  category?: string;
  title: string;
  message: string;
  priority?: string;
  severity?: string;
  related_case_number?: string | null;
  related_fir_number?: string | null;
  is_broadcast?: boolean;
  attachment_url?: string | null;
}) {
  return apiRequest<NotificationRecord>('/notifications', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function markNotificationRead(notificationId: string) {
  return apiRequest<{ success: boolean; message: string }>(`/notifications/${notificationId}/read`, { method: 'PUT' });
}

export async function markAllNotificationsRead() {
  return apiRequest<{ success: boolean; message: string }>('/notifications/read-all', { method: 'PUT' });
}

export async function acknowledgeNotification(notificationId: string) {
  return apiRequest<{ success: boolean; message: string }>(`/notifications/${notificationId}/acknowledge`, { method: 'PUT' });
}

export async function resolveNotification(notificationId: string) {
  return apiRequest<{ success: boolean; message: string }>(`/notifications/${notificationId}/resolve`, { method: 'PUT' });
}

export async function dismissNotification(notificationId: string) {
  return apiRequest<{ success: boolean; message: string }>(`/notifications/${notificationId}`, { method: 'DELETE' });
}

export async function getActivityFeed(limit = 50, eventType?: string, resourceType?: string) {
  return apiRequest<ActivityFeedResponse>(`/notifications/activity-feed${buildQueryString({ limit, event_type: eventType, resource_type: resourceType } as any)}`);
}

export async function getLiveTimeline(caseId?: string, limit = 30) {
  return apiRequest<any[]>(`/notifications/live-timeline${buildQueryString({ case_id: caseId, limit })}`);
}

export interface ModelInfo {
  model_name: string;
  risk_algorithm: string;
  forecast_algorithm: string;
  version: string;
  trained_on: string | null;
  training_rows: number;
  risk_metrics: Record<string, any>;
  forecast_metrics: Record<string, any>;
  risk_model_loaded: boolean;
  forecast_model_loaded: boolean;
}

export async function getModelInfo() {
  return apiRequest<ModelInfo>('/ai/predictions/model-info');
}

/** Admin-triggered risk model retrain (backend POST /ai/predictions/train). */
export async function trainRiskModels() {
  return apiRequest<{ status: string; retrained_by: string; metrics: Record<string, unknown> }>(
    '/ai/predictions/train',
    { method: 'POST' },
  );
}

// ── Season Breakdown ────────────────────────────────────────────────────────

export interface SeasonData {
  season: string;
  count: number;
  percentage: number;
  top_district: string;
}

export interface SeasonBreakdownResponse {
  seasons: SeasonData[];
  total_cases: number;
  karnataka_climate_note?: string;
}

export async function getSeasonBreakdown() {
  return apiRequest<SeasonBreakdownResponse>('/dashboard/season-breakdown');
}

// ── Sociological Insights ───────────────────────────────────────────────────

export interface AgeGroupData {
  group: string;
  count: number;
  percentage: number;
}

export interface GenderData {
  gender: string;
  count: number;
  percentage: number;
}

export interface DemographicAnalysis {
  age_groups: AgeGroupData[];
  gender_distribution: GenderData[];
  total_victims: number;
}

export interface UrbanRuralData {
  type: string;
  label: string;
  count: number;
  percentage: number;
  color: string;
  classification_status?: 'AVAILABLE' | 'DATA_UNAVAILABLE';
}

export interface DistrictDensity {
  district: string;
  canonical_district?: string | null;
  match_method?: string;
  mapping_status?: 'MATCHED' | 'UNMAPPED';
  crime_count: number;
  crime_per_lakh: number | null;
  crime_per_sqkm: number | null;
  population_lakhs: number | null;
  area_sq_km: number | null;
  type: string | null;
}

export interface UrbanRuralAnalysis {
  urban_rural_distribution: UrbanRuralData[];
  unmapped_districts?: string[];
  district_crime_density: DistrictDensity[];
  total_crimes: number;
}

export interface CorrelationDetail {
  coefficient: number | null;
  sample_size: number;
  excluded_missing?: number;
  status: string;
}

export interface DistrictOverlay {
  district: string;
  canonical_district?: string | null;
  mapping_status?: 'MATCHED' | 'UNMAPPED';
  match_method?: string;
  limitation?: string;
  crime_count: number;
  population_lakhs: number | null;
  area_sq_km: number | null;
  population_density: number | null;
  crime_per_lakh: number | null;
  crime_per_sqkm: number | null;
  data_status?: Record<string, 'AVAILABLE' | 'DATA_UNAVAILABLE'>;
  urbanization_type: string | null;
  literacy_rate: number | null;
  sex_ratio: number | null;
  avg_income_lakhs: number | null;
  unemployment_rate: number | null;
  risk_index?: number | null;
  source_period?: number | null;
  period_label?: string | null;
  record_completeness_pct?: number;
  correlation_flags: string[];
}

export interface SocioeconomicAnalysis {
  districts: DistrictOverlay[];
  correlations: {
    literacy_vs_crime: number | null;
    income_vs_crime: number | null;
    unemployment_vs_crime: number | null;
  };
  correlation_details?: Record<string, CorrelationDetail>;
  unmapped_districts?: string[];
  provenance?: {
    dataset_name: string;
    version: string;
    origin: string;
    source_key: string | null;
  };
  dataset?: {
    version: string;
    file?: string;
    demo_data?: boolean;
    notes?: string[];
    indicators?: unknown[];
    partial_records?: Array<{ district: string; available_indicators: number; total_indicators: number }>;
    duplicate_district_keys?: string[];
    records_missing_period?: string[];
    data_years?: number[];
  } | null;
  insights: Array<{
    type: string;
    title: string;
    description: string;
  }>;
}

export interface ScatterPoint {
  district: string;
  canonical_district?: string | null;
  match_method?: string;
  mapping_status?: 'MATCHED' | 'UNMAPPED';
  limitation?: string;
  crime_count: number;
  crime_per_lakh: number | null;
  population_density: number | null;
  urbanization_type: string | null;
  color: string;
}

export interface TemporalDemographic {
  hourly_distribution: Array<{ hour: string; count: number; percentage: number }>;
  day_of_week_distribution: Array<{ day: string; count: number; percentage: number }>;
  monthly_trend: Array<{ month: string; count: number }>;
  night_crime_percentage: number;
  weekend_crime_percentage: number;
}

export interface OffenderDemographics {
  age_groups: AgeGroupData[];
  gender_distribution: GenderData[];
  status_distribution: Array<{ status: string; count: number; percentage: number }>;
  total_offenders: number;
}

export async function getSociologicalDemographics() {
  return apiRequest<DemographicAnalysis>('/sociological/demographics');
}

export async function getSociologicalUrbanRural() {
  return apiRequest<UrbanRuralAnalysis>('/sociological/urban-rural');
}

export async function getSociologicalSocioeconomic() {
  return apiRequest<SocioeconomicAnalysis>('/sociological/socioeconomic');
}

export async function getSociologicalPopulationCorrelation() {
  return apiRequest<{ scatter: ScatterPoint[]; total_districts: number }>('/sociological/population-correlation');
}

export async function getSociologicalTemporal() {
  return apiRequest<TemporalDemographic>('/sociological/temporal-demographics');
}

/** Hour x day-of-week incident matrix (issue #143 gap 131.3). */
export interface TemporalMatrixCell {
  day: string;
  count: number;
  percentage: number;
  expected: number;
  std_residual: number;
}

export interface TemporalMatrixRow {
  hour: number;
  label: string;
  total: number;
  cells: TemporalMatrixCell[];
}

export interface TemporalMatrixPeak {
  hour: number;
  day: string;
  count: number;
  std_residual: number;
}

export interface TemporalMatrixResponse {
  filters: { district: string | null; location_id: string | null };
  days: string[];
  matrix: TemporalMatrixRow[];
  grand_total: number;
  hour_totals: Array<{ hour: number; count: number }>;
  day_totals: Array<{ day: string; count: number }>;
  peaks: TemporalMatrixPeak[];
  busiest_hour: number | null;
  night_share_pct: number;
  weekend_share_pct: number;
}

export async function getSociologicalTemporalMatrix(params?: { district?: string; location_id?: string }) {
  const query = new URLSearchParams();
  if (params?.district) query.set('district', params.district);
  if (params?.location_id) query.set('location_id', params.location_id);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return apiRequest<TemporalMatrixResponse>(`/sociological/temporal-matrix${suffix}`);
}

export async function getSociologicalOffenderDemographics() {
  return apiRequest<OffenderDemographics>('/sociological/offender-demographics');
}

// ── Strategic Intelligence ──────────────────────────────────────────────────

export interface StrategicBriefing {
  generated_at: string;
  summary: {
    total_crimes: number;
    recent_crimes_30d: number;
    weekly_crimes: number;
    open_cases: number;
    high_priority_cases: number;
    resolution_rate: number;
    crime_trend_change: number;
    total_firs: number;
    total_criminals: number;
    at_large_criminals: number;
    total_victims: number;
    total_officers: number;
    total_evidence: number;
    pending_evidence: number;
    unread_notifications: number;
  };
  top_categories: Array<{ category: string; count: number }>;
  districts_at_risk: Array<{
    district: string;
    crime_count: number;
    risk_level: string;
    trend: string;
    factors: string[];
  }>;
  monthly_trend: Array<{ month: string; count: number }>;
  emerging_trends: Array<{
    category: string;
    recent_count: number;
    historical_count: number;
    change_percentage: number;
    direction: string;
  }>;
  deployment_suggestions: Array<{
    priority: string;
    action: string;
    reason: string;
    district: string;
    resource_type: string;
  }>;
  top_criminals: Array<{
    id: string;
    name: string;
    status: string;
    aliases: string | null;
    risk_factors: string | null;
  }>;
  recent_firs: Array<{
    id: string;
    fir_number: string;
    complainant: string;
    status: string;
    filed_at: string | null;
  }>;
}

export interface DailySummary {
  date: string;
  today_crimes: number;
  yesterday_crimes: number;
  trend: string;
  today_firs: number;
  open_cases: number;
  at_large_criminals: number;
  categories_today: Array<{ category: string; count: number }>;
  districts_today: Array<{ district: string; count: number }>;
}

export interface ResourceAllocation {
  allocations: Array<{
    district: string;
    crime_share_pct: number;
    crime_count: number;
    allocation_priority: string;
    suggested_patrol_ratio: number;
  }>;
  total_districts: number;
  generated_at: string;
}

export async function getStrategicBriefing() {
  return apiRequest<StrategicBriefing>('/strategic/briefing');
}

export async function getHighRiskDistricts() {
  return apiRequest<any[]>('/strategic/high-risk-districts');
}

export interface EmergingTypology {
  category: string;
  recent_count: number;
  historical_count: number;
  change_percentage: number;
  direction: 'increasing' | 'decreasing' | 'stable';
}

export async function getEmergingTrends() {
  return apiRequest<EmergingTypology[]>('/strategic/emerging-trends');
}

export const getStrategicEmergingTrends = getEmergingTrends;

export async function getResourceAllocation() {
  return apiRequest<ResourceAllocation>('/strategic/resource-allocation');
}

export async function getDailySummary() {
  return apiRequest<DailySummary>('/strategic/daily-summary');
}

// ── Victimology (issue #139 M5) ─────────────────────────────────────────────

export interface VictimologyOverview {
  total_victims: number;
  victims_with_firs: number;
  repeat_victim_count: number;
  repeat_victimization_rate: number | null;
  average_age: number | null;
  gender_distribution: Array<{ gender: string; count: number }>;
  top_risk_districts: Array<{ district: string; victim_count: number; avg_vulnerability: number }>;
}

export interface RepeatVictim {
  id: string;
  name: string;
  fir_count: number;
  districts: string[];
  categories: string[];
  vulnerability_index: number | null;
}

export interface VulnerabilityEntry {
  id: string;
  name: string;
  district: string | null;
  age: number | null;
  gender: string | null;
  fir_count: number;
  vulnerability_index: number;
  risk_factors: string[];
}

export async function getVictimologyOverview() {
  return apiRequest<VictimologyOverview>('/victimology/overview');
}

export async function getRepeatVictims(minFirCount = 2) {
  return apiRequest<{ count: number; repeat_victims: RepeatVictim[] }>(
    `/victimology/repeat-victims?min_fir_count=${minFirCount}`
  );
}

export async function getVulnerabilityIndex() {
  return apiRequest<{ count: number; entries: VulnerabilityEntry[] }>('/victimology/vulnerability-index');
}

// ── Interventions (issue #139 M7) ───────────────────────────────────────────

export type InterventionStatus = 'planned' | 'active' | 'completed' | 'suspended';

export interface InterventionRecord {
  id: string;
  district: string;
  intervention_type: string;
  title: string;
  description: string | null;
  started_at: string;
  ended_at: string | null;
  status: InterventionStatus;
  target_category: string | null;
  created_by_name: string | null;
  notes: string | null;
  created_at: string;
}

export interface InterventionEffectiveness {
  intervention_id: string;
  title: string;
  district: string;
  status: string;
  pre_window: { start: string; end: string; crime_count: number };
  post_window: { start: string; end: string; crime_count: number };
  change_percentage: number | null;
  verdict: 'effective' | 'partially_effective' | 'no_measurable_effect' | 'insufficient_data';
}

export interface InterventionCreateInput {
  district: string;
  intervention_type: string;
  title: string;
  description?: string;
  started_at: string;
  ended_at?: string;
  status?: InterventionStatus;
  target_category?: string;
  notes?: string;
}

export async function listInterventions(params: { district?: string; status?: string } = {}) {
  const search = new URLSearchParams();
  if (params.district) search.set('district', params.district);
  if (params.status) search.set('status', params.status);
  const qs = search.toString();
  return apiRequest<{ count: number; interventions: InterventionRecord[] }>(
    `/interventions${qs ? `?${qs}` : ''}`
  );
}

export async function createIntervention(input: InterventionCreateInput) {
  return apiRequest<InterventionRecord>('/interventions', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function getInterventionEffectiveness(id: string) {
  return apiRequest<InterventionEffectiveness>(`/interventions/${id}/effectiveness`);
}

export async function updateIntervention(id: string, patch: Partial<InterventionCreateInput>) {
  return apiRequest<InterventionRecord>(`/interventions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  });
}

// ── Semantic MO Search + NER (issue #139 M6) ────────────────────────────────

export interface MoSearchResult {
  doc_id: string;
  kind: string;
  title: string;
  similarity: number | null;
  excerpt: string;
  meta: Record<string, unknown>;
}

export async function searchModusOperandi(query: string, k = 8, kinds?: string[]) {
  const search = new URLSearchParams({ q: query, k: String(k) });
  if (kinds?.length) search.set('kinds', kinds.join(','));
  return apiRequest<{
    query: string;
    corpus_size: number;
    embedding_method: string;
    results: MoSearchResult[];
  }>(`/ai/mo/search?${search.toString()}`);
}

export interface ExtractedEntity {
  text: string;
  type: string;
  start: number;
  end: number;
  source: string;
}

export async function extractEntities(text: string) {
  return apiRequest<{
    entity_count: number;
    entities_by_type: Record<string, string[]>;
    entities: ExtractedEntity[];
  }>('/ai/mo/extract-entities', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

export async function extractCaseEntities(caseId: string) {
  return apiRequest<{
    case_id: string;
    case_number: string;
    entity_count: number;
    entities_by_type: Record<string, string[]>;
    entities: ExtractedEntity[];
  }>(`/ai/mo/extract-case/${caseId}`);
}

// ── Recurring MO Pattern Detection (issue #144 gap 132.2) ───────────────────

export interface MOPatternMember {
  kind: 'case' | 'criminal';
  id: string;
  label: string;
  status?: string | null;
  district?: string | null;
}

export interface MOPattern {
  pattern_id: string;
  support: number;
  case_count: number;
  criminal_count: number;
  members: MOPatternMember[];
  shared_tags: string[];
  dominant_category: string | null;
  districts: string[];
  first_occurred: string | null;
  last_occurred: string | null;
  peak_time_window: string | null;
  at_large_members: number;
  threat_score: number;
  example_narrative: string;
}

export interface MOPatternResponse {
  patterns: MOPattern[];
  total_patterns: number;
  method: string;
  min_support: number;
  entities_analysed: { cases: number; criminals: number };
  generated_at: string;
}

export async function getRecurringMOPatterns(minSupport = 2, k = 10) {
  const search = new URLSearchParams({ min_support: String(minSupport), k: String(k) });
  return apiRequest<MOPatternResponse>(`/ai/mo/patterns?${search.toString()}`);
}

export interface MOTagSyncStats {
  cases_scanned: number;
  criminals_scanned: number;
  tags_created: number;
  case_links_created: number;
  criminal_links_created: number;
  already_synced: number;
}

export async function syncMOTags() {
  return apiRequest<MOTagSyncStats>('/ai/mo/sync-tags', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export interface MOMatchingCase {
  case_id: string;
  case_number: string;
  category: string | null;
  district: string | null;
  station: string | null;
  status: string;
  occurred_at: string | null;
  similarity_score: number;
  similarity_percent: number;
  match_level: 'high' | 'medium' | 'low' | 'none';
  confidence: number;
  is_confirmed_relationship?: boolean;
  relationship_label?: string;
  matching_factors: string[];
  divergent_factors: string[];
  insufficient_data: string[];
}

export interface MOMatchingSuspect {
  criminal_id: string;
  full_name: string;
  aliases: string | null;
  status: string;
  gang_affiliation: string | null;
  similarity_score: number;
  similarity_percent: number;
  match_level: 'high' | 'medium' | 'low' | 'none';
  confidence: number;
  is_confirmed_relationship: boolean;
  relationship_label: string;
  matching_factors: string[];
  divergent_factors: string[];
  insufficient_data: string[];
}

export interface MOMatchCaseResponse {
  target_case: {
    case_id: string;
    case_number: string;
    category: string | null;
    district: string | null;
    profile: Record<string, any>;
  };
  matching_cases: MOMatchingCase[];
  matching_suspects: MOMatchingSuspect[];
  total_cases_evaluated: number;
  total_criminals_evaluated: number;
  evaluated_at: string;
  error?: string;
}

export interface MOMatchCriminalResponse {
  target_criminal: {
    criminal_id: string;
    full_name: string;
    status: string;
    profile: Record<string, any>;
  };
  matching_cases: MOMatchingCase[];
  similar_criminals: MOMatchingSuspect[];
  total_cases_evaluated: number;
  total_criminals_evaluated: number;
  evaluated_at: string;
  error?: string;
}

export interface MOCompareResponse {
  entity_a: Record<string, any>;
  entity_b: Record<string, any>;
  similarity_score: number;
  similarity_percent: number;
  match_level: 'high' | 'medium' | 'low' | 'none';
  confidence: number;
  matching_factors: string[];
  divergent_factors: string[];
  insufficient_data: string[];
  dimension_scores: Record<string, number>;
  evaluated_at: string;
  error?: string;
}

export async function getCaseMOMatches(caseId: string, minSimilarity = 0.25, k = 5) {
  const params = new URLSearchParams({ min_similarity: String(minSimilarity), k: String(k) });
  return apiRequest<MOMatchCaseResponse>(`/ai/mo/match/case/${caseId}?${params.toString()}`);
}

export async function getCriminalMOMatches(criminalId: string, minSimilarity = 0.25, k = 5) {
  const params = new URLSearchParams({ min_similarity: String(minSimilarity), k: String(k) });
  return apiRequest<MOMatchCriminalResponse>(`/ai/mo/match/criminal/${criminalId}?${params.toString()}`);
}

export async function compareMOEntities(params: {
  entity_a_id: string;
  entity_a_type: 'case' | 'criminal';
  entity_b_id: string;
  entity_b_type: 'case' | 'criminal';
}) {
  return apiRequest<MOCompareResponse>('/ai/mo/compare', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

// ── Data Import / Legacy Ingestion (issue #139 M1/M2) ───────────────────────

export interface ImportColumnSpec {
  name: string;
  required: boolean;
  type: string;
  choices?: string[];
}

export interface ImportEntitySpec {
  entity_type: string;
  columns: ImportColumnSpec[];
}

export interface ImportProfileInfo {
  profile: string;
  description: string;
  sample_mappings?: Record<string, string>;
}

export interface ImportPreviewReportItem {
  row_number: number;
  errors: string[];
  warnings: string[];
}

export interface ImportAnalysis {
  entity_type: string;
  profile: string;
  filename: string;
  detected_headers: string[];
  column_mapping: Record<string, string>;
  unmapped_headers: string[];
  missing_required_columns: string[];
  total_rows: number;
  sample_mapped_rows: Array<Record<string, unknown>>;
  validation_report: ImportPreviewReportItem[];
  truncated_report: boolean;
  estimated_valid_rows: number;
  estimated_invalid_rows: number;
}

export interface ImportCommitResult {
  job_id: string;
  status: string;
  entity_type: string;
  profile: string;
  filename: string;
  total_rows: number;
  imported_rows: number;
  failed_rows: number;
  validation_report: ImportPreviewReportItem[];
}

export interface ImportJobSummary {
  id: string;
  entity_type: string;
  source_format: string;
  mapping_profile: string;
  filename: string;
  status: string;
  total_rows: number;
  imported_rows: number;
  failed_rows: number;
  created_at: string | null;
  created_by: string | null;
}

export async function getImportEntities() {
  return apiRequest<{ profiles: ImportProfileInfo[]; entities: ImportEntitySpec[]; max_rows: number }>('/data-import/entities');
}

export async function analyzeImportFile(file: File, entityType: string, profile = 'standard') {
  const form = new FormData();
  form.append('file', file);
  form.append('entity_type', entityType);
  form.append('profile', profile);
  return apiRequest<ImportAnalysis>('/data-import/preview', {
    method: 'POST',
    body: form,
  });
}

export async function commitImportFile(
  file: File,
  entityType: string,
  profile = 'standard',
  dryRun = false
) {
  const form = new FormData();
  form.append('file', file);
  form.append('entity_type', entityType);
  form.append('profile', profile);
  if (dryRun) form.append('dry_run', 'true');
  return apiRequest<ImportCommitResult>('/data-import/commit', {
    method: 'POST',
    body: form,
  });
}

export async function listImportJobs(pageSize = 20) {
  return apiRequest<{ total: number; page: number; page_size: number; results: ImportJobSummary[] }>(`/data-import/jobs?page=1&page_size=${pageSize}`);
}

export interface DataQualityReport {
  summary: { total_records: number; by_provenance: Record<string, number> };
  entity_breakdown: Record<string, Record<string, number>>;
  warnings: { type: string; table: string; count: number; message: string; severity: string }[];
  provenance_values: string[];
}

export interface ModelHealthReport {
  hotspot: {
    model: string;
    overall_status: string;
    checks: { valid: boolean; artifact: string; error?: string }[];
    valid_count: number;
    invalid_count: number;
    model_loaded: boolean;
  };
  risk: {
    model: string;
    overall_status: string;
    checks: { valid: boolean; artifact: string; error?: string }[];
    valid_count: number;
    invalid_count: number;
    risk_model_loaded: boolean;
    forecast_model_loaded: boolean;
  };
  overall_status: string;
}

export async function getAdminDataQuality() {
  return apiRequest<DataQualityReport>('/admin/data-quality');
}

export async function getModelHealth() {
  return apiRequest<ModelHealthReport>('/ai/model-health');
}

export async function downloadEvidencePDF(evidenceId: string, filename?: string): Promise<void> {
  const tokens = getStoredTokens();
  const response = await fetch(`${API_BASE_URL}/evidence/${evidenceId}/download?format=pdf`, {
    headers: {
      ...(tokens?.accessToken ? { Authorization: `Bearer ${tokens.accessToken}` } : {}),
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to download evidence PDF (${response.statusText})`);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || `KSP_Evidence_${evidenceId.slice(0, 8)}.pdf`;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 500);
}

