const DEFAULT_API_BASE_URL = '/api/v1';

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

const MOCK_SUMMARY = {
  total_crimes: 12543,
  open_crimes: 4651,
  total_firs: 9322,
  total_criminals: 3412,
  resolution_rate_percent: 62.9
};

const MOCK_TRENDS = [
  { date: '2026-01-01', count: 210 },
  { date: '2026-02-01', count: 185 },
  { date: '2026-03-01', count: 240 },
  { date: '2026-04-01', count: 195 },
  { date: '2026-05-01', count: 280 }
];

const MOCK_CATEGORIES = [
  { category: 'Cybercrime', count: 2450 },
  { category: 'House Breaking', count: 1820 },
  { category: 'Narcotics', count: 1240 },
  { category: 'Robbery', count: 980 },
  { category: 'Fraud', count: 1560 }
];

const MOCK_DISTRICTS = [
  { district: 'Bengaluru Urban', count: 5420 },
  { district: 'Mysuru', count: 1890 },
  { district: 'Belagavi', count: 1200 },
  { district: 'Mangaluru', count: 980 },
  { district: 'Hubballi-Dharwad', count: 1150 }
];

const MOCK_RISK_SCORES = {
  district_id: null,
  window: 'Next 7 Days',
  model_version: 'LSTM-XGBoost Ensemble v2.4',
  grid_predictions: [
    { district: 'Whitefield Sector', risk_score: 91, confidence: 0.88 },
    { district: 'Indiranagar Sector', risk_score: 78, confidence: 0.85 },
    { district: 'Koramangala Sector', risk_score: 64, confidence: 0.81 },
    { district: 'Devaraja Sector', risk_score: 52, confidence: 0.79 }
  ]
};

const MOCK_HOTSPOTS = {
  hotspots: [
    { district_id: 'blr-1', name: 'Indiranagar', lat: 12.9786, lng: 77.6408, score: 92, category: 'Cybercrime', trend: 'up' },
    { district_id: 'blr-2', name: 'Whitefield', lat: 12.9698, lng: 77.7500, score: 88, category: 'Fraud', trend: 'up' },
    { district_id: 'mys-1', name: 'Devaraja Market', lat: 12.3086, lng: 76.6531, score: 75, category: 'House Breaking', trend: 'stable' },
    { district_id: 'mng-1', name: 'Harbor Gate', lat: 12.8700, lng: 74.8800, score: 84, category: 'Narcotics', trend: 'up' }
  ]
};

const MOCK_ANOMALIES = {
  anomalies: [
    { case_id: 'CR-8011/BNG', label: 'Simultaneous logins from distinct locations', score: 0.94, reason: 'Inspector credentials used in Bengaluru and Belagavi within 5 minutes.' },
    { case_id: 'CR-8012/BNG', label: 'Abnormal volume of secure dossier downloads', score: 0.87, reason: 'Officer downloaded 15 dossiers outside shift hours.' }
  ]
};

const MOCK_NETWORK = {
  nodes: [
    { id: 'node-1', name: 'Ramu "Kodaikanal" Swamy', category: 'suspect', riskScore: 92, details: 'Leader of coordinate interstate break-in gang. Suspected in late night residential robberies in Mysuru and Bengaluru.', casesCount: 14, phone: '+91 94420-12891' },
    { id: 'node-2', name: 'Vikram "Vicky" Yadav', category: 'suspect', riskScore: 88, details: 'Underground money mule coordinator. Funnels fraudulent loans through virtual ledger IDs.', casesCount: 8, phone: '+91 98845-09228' },
    { id: 'node-3', name: 'Sayed Ibrahim', category: 'suspect', riskScore: 84, details: 'Logistics provider for narcotics shipments. Connected to Mangaluru Harbor transit lines.', casesCount: 6, phone: '+91 99014-38419' },
    { id: 'node-4', name: 'Karthik Gowda', category: 'offender', riskScore: 71, details: 'Prior conviction for property fraud. Intercepted twice during excise checkpoint violations.', casesCount: 4 },
    { id: 'node-5', name: 'Mohsin Pasha', category: 'offender', riskScore: 65, details: 'Known organizer of illegal sand gravel mining syndicates in Ballari.', casesCount: 5 },
    { id: 'node-6', name: 'Indiranagar Sect-B, Bengaluru', category: 'location', riskScore: 75, details: 'Hotspot of recurring app-based extortion campaigns.', casesCount: 22 },
    { id: 'node-7', name: 'Harbor Gate A, Mangaluru', category: 'location', riskScore: 68, details: 'Seizure point of multiple synthetic drug consignments.', casesCount: 11 },
    { id: 'node-8', name: 'Devaraja Police Limit, Mysuru', category: 'location', riskScore: 50, details: 'Historic zone of lock-break burglaries.', casesCount: 9 },
    { id: 'node-9', name: 'K. S. Narayanan', category: 'victim', riskScore: 10, details: 'Complainant in FIR fraud scan. Swindled of 4.5L via biometric face ID bypass.', casesCount: 1 },
    { id: 'node-10', name: 'Dr. Vinay Murthy', category: 'victim', riskScore: 12, details: 'Home burglary witness in Mysuru break-in.', casesCount: 1 }
  ],
  edges: [
    { source: 'node-1', target: 'node-6', relationship: 'Last active cell location' },
    { source: 'node-1', target: 'node-8', relationship: 'Prior home break-in zone' },
    { source: 'node-1', target: 'node-10', relationship: 'Attacked residential yard' },
    { source: 'node-2', target: 'node-6', relationship: 'Launders app funds' },
    { source: 'node-9', target: 'node-6', relationship: 'Victim resided zone' },
    { source: 'node-3', target: 'node-7', relationship: 'Smuggles chemical contraband' },
    { source: 'node-5', target: 'node-7', relationship: 'Connected cargo clearing agent' },
    { source: 'node-4', target: 'node-8', relationship: 'Excise transit route overlap' },
    { source: 'node-1', target: 'node-4', relationship: 'Known accomplice association' },
    { source: 'node-2', target: 'node-9', relationship: 'Targeted in loan extortions' }
  ]
};

const MOCK_OFFENDERS = {
  offenders: [
    {
      id: 'node-1',
      name: 'Ramu "Kodaikanal" Swamy',
      alias: 'Kodaikanal Ramu',
      age: 42,
      gender: 'MALE',
      classification: 'A-CATEGORY',
      activeDistricts: ['MYSURU', 'BENGALURU'],
      status: 'ACTIVE',
      riskScore: 92,
      gangAffiliation: 'Interstate Lock-Breakers Cell',
      mugshotDesc: 'Height approx 5\'8", scar on left wrist. Active at night. Uses local coordinates projection to map high-value target assets.'
    },
    {
      id: 'node-2',
      name: 'Vikram "Vicky" Yadav',
      alias: 'Vicky',
      age: 36,
      gender: 'MALE',
      classification: 'B-CATEGORY',
      activeDistricts: ['BENGALURU'],
      status: 'UNDER_SURVEILLANCE',
      riskScore: 88,
      gangAffiliation: 'Cyber Ledger Mules Network',
      mugshotDesc: 'Height approx 5\'10", tattoo of wings on right arm. Funnels app-based extortions.'
    },
    {
      id: 'node-3',
      name: 'Sayed Ibrahim',
      alias: 'Sayed',
      age: 40,
      gender: 'MALE',
      classification: 'WATCHLIST',
      activeDistricts: ['MANGALURU'],
      status: 'ACTIVE',
      riskScore: 84,
      gangAffiliation: 'Coastal Drug Logistics Node',
      mugshotDesc: 'Height approx 5\'9", mole on left cheek. Coordinates transit shipments at Mangaluru Harbor.'
    }
  ]
};

const MOCK_CRIMES = {
  total: 2,
  page: 1,
  page_size: 100,
  results: [
    { id: 'cr-1', case_number: 'FIR-2026-0091', category_id: 'Cybercrime', location_id: 'Indiranagar', occurred_at: '2026-05-10T14:30:00Z', reported_at: '2026-05-10T15:45:00Z', description: 'Complainant reports extortion via cloned voice message.', mo_tags: 'audio-cloning, extortion', status: 'OPEN', created_at: '2026-05-10T15:50:00Z' },
    { id: 'cr-2', case_number: 'FIR-2026-0092', category_id: 'House Breaking', location_id: 'Devaraja Limit', occurred_at: '2026-05-12T02:00:00Z', reported_at: '2026-05-12T09:00:00Z', description: 'Lock-break entry during early morning hours.', mo_tags: 'lock-break, night-burglar', status: 'OPEN', created_at: '2026-05-12T09:15:00Z' }
  ]
};

const MOCK_CRIMINALS = {
  total: 2,
  page: 1,
  page_size: 100,
  results: [
    { id: 'crm-1', full_name: 'Ramu Swamy', aliases: 'Kodaikanal Ramu', date_of_birth: '1984-06-15', gender: 'M', address: 'Kodaikanal, Tamil Nadu', identifying_marks: 'Scar on left wrist', mo_summary: 'Interstate night residential robberies.', status: 'ACTIVE', created_at: '2026-01-10T12:00:00Z' },
    { id: 'crm-2', full_name: 'Vikram Yadav', aliases: 'Vicky', date_of_birth: '1990-11-22', gender: 'M', address: 'Bengaluru, Karnataka', identifying_marks: 'Tattoo on right forearm', mo_summary: 'Cryptocurrency and peer-to-peer loan fraud.', status: 'UNDER_SURVEILLANCE', created_at: '2026-01-12T14:30:00Z' }
  ]
};

function getMockResponse(path: string, options: RequestInit = {}): any {
  if (path.startsWith('/auth/login')) {
    let username = 'SCRB-7740';
    let password = '';
    try {
      if (options.body) {
        const body = JSON.parse(options.body as string);
        username = body.username || 'SCRB-7740';
        password = body.password || '';
      }
    } catch {}
    const cleanUser = username.toUpperCase().trim();
    if (cleanUser === 'SP-0088') {
      if (password !== '987654') {
        throw new Error('Access Denied: Invalid Badge ID or PIN.');
      }
    } else if (cleanUser === 'IO-3921') {
      if (password !== '456789') {
        throw new Error('Access Denied: Invalid Badge ID or PIN.');
      }
    } else {
      if (password !== '123456') {
        throw new Error('Access Denied: Invalid Badge ID or PIN.');
      }
    }
    const badgeId = username.toUpperCase();
    return {
      access_token: 'mock-token-for-' + badgeId,
      refresh_token: 'mock-refresh-token',
      token_type: 'bearer',
      expires_in: 1800
    };
  }
  if (path.startsWith('/auth/me')) {
    const { accessToken } = getStoredTokens();
    const badgeId = accessToken ? accessToken.replace('mock-token-for-', '') : 'SCRB-7740';
    if (badgeId.startsWith('SP')) {
      return {
        id: 'mock-sp',
        username: badgeId,
        email: 'annamalai@ksp.gov.in',
        full_name: 'SP. K. Annamalai',
        district: 'Bengaluru Urban',
        station: 'SCRB Headquarters',
        is_active: true,
        role: 'policymaker',
        created_at: '2026-01-01T00:00:00Z'
      };
    } else if (badgeId.startsWith('IO')) {
      return {
        id: 'mock-io',
        username: badgeId,
        email: 'ravikumar@ksp.gov.in',
        full_name: 'Inspector Ravi Kumar',
        district: 'Bengaluru Urban',
        station: 'Whitefield Station',
        is_active: true,
        role: 'investigator',
        created_at: '2026-01-01T00:00:00Z'
      };
    } else {
      return {
        id: 'mock-scrb',
        username: badgeId,
        email: 'sharanappa@ksp.gov.in',
        full_name: 'Dr. Sharanappa S. D.',
        district: 'Bengaluru Urban',
        station: 'SCRB Headquarters',
        is_active: true,
        role: 'admin',
        created_at: '2026-01-01T00:00:00Z'
      };
    }
  }
  if (path.startsWith('/dashboard/summary')) return MOCK_SUMMARY;
  if (path.startsWith('/dashboard/crime-trends')) return MOCK_TRENDS;
  if (path.startsWith('/dashboard/category-breakdown')) return MOCK_CATEGORIES;
  if (path.startsWith('/dashboard/district-comparison')) return MOCK_DISTRICTS;
  if (path.startsWith('/ai/predictions/risk-scores')) return MOCK_RISK_SCORES;
  if (path.startsWith('/ai/hotspots')) return MOCK_HOTSPOTS;
  if (path.startsWith('/ai/predictions/anomalies')) return MOCK_ANOMALIES;
  if (path.startsWith('/ai/network/person/')) return MOCK_NETWORK;
  if (path.startsWith('/ai/chat/query')) {
    return {
      answer: "Analyzed recent trends in Bengaluru Urban. Cyber extortion reports show a 12% rise, concentrated in Indiranagar and Whitefield Sectors. Suggesting patrol density increases around Indiranagar Section B.",
      data: [],
      sources: ["KSP-SEC-2026/CYBER-EXTORTION-MEMO", "SCRB-WHITEFIELD-SECTOR-THREAT-MATRIX"],
      chart_suggestion: null
    };
  }
  if (path.startsWith('/crimes')) return MOCK_CRIMES;
  if (path.startsWith('/criminals')) return MOCK_CRIMINALS;
  if (path.startsWith('/ai/offenders/dossiers')) return MOCK_OFFENDERS;

  return {};
}

async function apiRequest<T>(path: string, options: RequestInit = {}, includeAuth = true): Promise<T> {
  const { accessToken } = getStoredTokens();
  
  if (isEmulatorActive) {
    return getMockResponse(path, options) as T;
  }

  const headers = new Headers(options.headers ?? {});

  if (includeAuth && accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorMsg = await readErrorMessage(response);
      if (errorMsg.includes('offline') || errorMsg.includes('connection failed') || response.status >= 500) {
        console.warn(`[API] Degraded backend state detected. Engaging emulator mode for: ${path}`);
        setEmulatorActive(true);
        return getMockResponse(path, options) as T;
      }
      throw new Error(errorMsg);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  } catch (error) {
    console.warn(`[API] Connection to backend failed. Engaging emulator mode for: ${path}`, error);
    setEmulatorActive(true);
    return getMockResponse(path, options) as T;
  }
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
