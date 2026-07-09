const DEFAULT_API_BASE_URL = '/api/v1';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

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
}

export interface AnomalyRecord {
  case_id: string;
  label: string;
  score: number;
  reason: string;
}

export interface AnomaliesResponse {
  anomalies: AnomalyRecord[];
}

export interface NetworkNode {
  id: string;
  name: string;
  category: 'suspect' | 'offender' | 'location' | 'victim';
  riskScore: number;
  details: string;
  casesCount: number;
  phone?: string;
}

export interface NetworkEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface NetworkResponse {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export interface ChatQueryResponse {
  answer: string;
  data: Array<Record<string, unknown>>;
  sources: string[];
  chart_suggestion: string | null;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

const hasWindow = typeof window !== 'undefined';

export const getStoredTokens = (): AuthTokens => ({
  accessToken: hasWindow ? window.localStorage.getItem(ACCESS_TOKEN_KEY) ?? '' : '',
  refreshToken: hasWindow ? window.localStorage.getItem(REFRESH_TOKEN_KEY) ?? '' : '',
});

export const setStoredTokens = (tokens: AuthTokens) => {
  if (!hasWindow) {
    return;
  }

  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
};

export const clearStoredTokens = () => {
  if (!hasWindow) {
    return;
  }

  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
};

export const mapBackendRoleToUiRole = (role: string): 'SCRB' | 'IO' | 'SP' => {
  switch (role) {
    case 'investigator':
      return 'IO';
    case 'policymaker':
      return 'SP';
    case 'admin':
    case 'crime_analyst':
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
    return payload.detail || payload.message || response.statusText;
  } catch {
    return response.statusText;
  }
};

async function apiRequest<T>(path: string, options: RequestInit = {}, includeAuth = true): Promise<T> {
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
  return apiRequest<{ message: string }>('/auth/logout', {
    method: 'POST',
  });
}

export async function getMe() {
  return apiRequest<BackendUser>('/auth/me');
}

export async function getDashboardSummary() {
  return apiRequest<DashboardSummary>('/dashboard/summary');
}

export async function getCrimeTrends() {
  return apiRequest<TrendPoint[]>('/dashboard/crime-trends');
}

export async function getCategoryBreakdown() {
  return apiRequest<CategoryPoint[]>('/dashboard/category-breakdown');
}

export async function getDistrictComparison() {
  return apiRequest<DistrictComparisonPoint[]>('/dashboard/district-comparison');
}

export async function getRiskScores(window = 'next_7d', districtId?: string) {
  return apiRequest<RiskScoresResponse>(`/ai/predictions/risk-scores${buildQueryString({ window, district_id: districtId })}`);
}

export async function getHotspots(districtId?: string) {
  return apiRequest<HotspotsResponse>(`/ai/hotspots${buildQueryString({ district_id: districtId })}`);
}

export async function getAnomalies() {
  return apiRequest<AnomaliesResponse>('/ai/predictions/anomalies');
}

export async function getNetworkPerson(personId: string, depth = 1) {
  return apiRequest<NetworkResponse>(`/ai/network/person/${encodeURIComponent(personId)}${buildQueryString({ depth })}`);
}

export async function chatQuery(message: string, sessionId?: string) {
  return apiRequest<ChatQueryResponse>('/ai/chat/query', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId ?? null }),
  });
}

export async function listCrimes(page = 1, pageSize = 100) {
  return apiRequest<PaginatedResponse<CrimeCaseRecord>>(`/crimes${buildQueryString({ page, page_size: pageSize })}`);
}

export async function listCriminals(page = 1, pageSize = 100) {
  return apiRequest<PaginatedResponse<CriminalRecord>>(`/criminals${buildQueryString({ page, page_size: pageSize })}`);
}

export async function getOffenderDossiers() {
  return apiRequest<OffenderDossiersResponse>('/ai/offenders/dossiers');
}
