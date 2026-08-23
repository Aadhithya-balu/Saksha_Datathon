import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '../store/authStore';

vi.mock('../services/api', () => ({
  login: vi.fn(),
  logout: vi.fn().mockResolvedValue({ message: 'ok' }),
  refreshSession: vi.fn(),
  getMe: vi.fn(),
  mapBackendRoleToUiRole: (role: string) => role.toUpperCase(),
  setStoredTokens: vi.fn((t: { accessToken: string; refreshToken: string }) => {
    localStorage.setItem('saksha_access_token', t.accessToken);
    localStorage.setItem('saksha_refresh_token', t.refreshToken);
  }),
  getStoredTokens: vi.fn(() => ({
    accessToken: localStorage.getItem('saksha_access_token'),
    refreshToken: localStorage.getItem('saksha_refresh_token'),
  })),
  clearStoredTokens: vi.fn(() => {
    localStorage.removeItem('saksha_access_token');
    localStorage.removeItem('saksha_refresh_token');
  }),
}));

import {
  login as loginRequest,
  getMe,
  getStoredTokens,
} from '../services/api';

const mockedLogin = vi.mocked(loginRequest);
const mockedGetMe = vi.mocked(getMe);

function resetStore() {
  useAuthStore.setState({
    user: null,
    isAuthenticated: false,
    loginError: null,
    sessionTimeRemaining: 1800,
    isHydrating: false,
  });
}

const backendUser = {
  id: 'u-1',
  username: 'TEST-IO-001',
  email: 'io@example.com',
  full_name: 'Test Investigator',
  district: 'Bengaluru Urban',
  station: 'Whitefield',
  is_active: true,
  role: 'investigator',
  created_at: '2026-01-01T00:00:00Z',
};

describe('authStore session lifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStore();
    localStorage.clear();
  });

  it('logs in with valid credentials and stores tokens + user', async () => {
    mockedLogin.mockResolvedValue({
      access_token: 'acc', refresh_token: 'ref', token_type: 'bearer', expires_in: 1800,
    });
    mockedGetMe.mockResolvedValue(backendUser);

    const ok = await useAuthStore.getState().login('TEST-IO-001', 'pin');
    expect(ok).toBe(true);
    const s = useAuthStore.getState();
    expect(s.isAuthenticated).toBe(true);
    expect(s.user?.badgeId).toBe('TEST-IO-001');
    expect(s.user?.role).toBe('INVESTIGATOR');
    expect(localStorage.getItem('saksha_access_token')).toBe('acc');
  });

  it('rejects invalid credentials and records the error', async () => {
    mockedLogin.mockRejectedValue(new Error('Invalid credentials'));
    const ok = await useAuthStore.getState().login('TEST-IO-001', 'wrong');
    expect(ok).toBe(false);
    const s = useAuthStore.getState();
    expect(s.isAuthenticated).toBe(false);
    expect(s.loginError).toContain('Invalid credentials');
    expect(localStorage.getItem('saksha_access_token')).toBeNull();
  });

  it('restores an authenticated session from stored tokens on init', async () => {
    localStorage.setItem('saksha_access_token', 'acc');
    localStorage.setItem('saksha_refresh_token', 'ref');
    mockedGetMe.mockResolvedValue(backendUser);
    await useAuthStore.getState().initializeSession();
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().isHydrating).toBe(false);
  });

  it('stays logged out when no tokens exist', async () => {
    await useAuthStore.getState().initializeSession();
    const s = useAuthStore.getState();
    expect(s.isAuthenticated).toBe(false);
    expect(s.isHydrating).toBe(false);
    expect(mockedGetMe).not.toHaveBeenCalled();
  });

  it('logs out and discards local tokens', () => {
    localStorage.setItem('saksha_access_token', 'a');
    useAuthStore.setState({ isAuthenticated: true, user: { name: 'X', badgeId: 'B', role: 'IO' } });
    useAuthStore.getState().logout();
    const s = useAuthStore.getState();
    expect(s.isAuthenticated).toBe(false);
    expect(s.user).toBeNull();
    expect(getStoredTokens().accessToken).toBeFalsy();
  });

  it('expires the session when the timer runs out', () => {
    useAuthStore.setState({ isAuthenticated: true, sessionTimeRemaining: 1 });
    useAuthStore.getState().tickSession();
    const s = useAuthStore.getState();
    expect(s.isAuthenticated).toBe(false);
    expect(s.loginError).toMatch(/Session Expired/);
  });
});
