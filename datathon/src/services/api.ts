const DEFAULT_API_BASE_URL = '/api/v1';
import type { UserRole } from '../store/authStore';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

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

export const mapBackendRoleToUiRole = (role: string): UserRole => {
  switch (role) {
    case 'investigator':
      return 'IO';
    case 'policymaker':
      return 'SP';
    case 'inspector':
      return 'INSPECTOR';
    case 'forensic':
      return 'FORENSIC';
    case 'viewer':
      return 'VIEWER';
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
    return payload.detail || payload.message || payload.error?.message || response.statusText;
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

export async function listCriminals(q?: string, page = 1, pageSize = 100) {
  return apiRequest<PaginatedResponse<CriminalRecord>>(`/criminals${buildQueryString({ q, page, page_size: pageSize })}`);
}

export async function getCriminal(criminalId: string) {
  return apiRequest<any>(`/criminals/${criminalId}`);
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
  attachments: Array<{ name: string; size: number }>;
  ai_risk_score: number;
  ai_analysis_reasons: string[];
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

export async function getCrimeCases(q?: string, status?: string, page = 1, pageSize = 20) {
  return apiRequest<PaginatedResponse<CrimeCaseDetailRecord>>(`/crime-cases${buildQueryString({ q, status, page, page_size: pageSize })}`);
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

export async function listVictims(q?: string, page = 1, pageSize = 100) {
  return apiRequest<PaginatedResponse<VictimRecord>>(`/victims${buildQueryString({ q, page, page_size: pageSize })}`);
}

export async function getVictim(victimId: string) {
  return apiRequest<any>(`/victims/${victimId}`);
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
  return apiRequest<any>(`/investigation/chat`, {
    method: 'POST',
    body: JSON.stringify({ case_id: caseId, message, session_id: sessionId ?? null }),
  });
}
