import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  apiRequest,
  login,
  clearStoredTokens,
  setStoredTokens,
} from '../services/api';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

describe('apiRequest', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('sends JSON body without auth header for public endpoints (login)', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ access_token: 'a', refresh_token: 'r' }), { status: 200 }));
    await login('admin', 'secret-pin');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/v2/auth/login');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ username: 'admin', password: 'secret-pin' });
    expect(init.headers.get('Authorization')).toBeNull();
  });

  it('attaches Bearer token when stored', async () => {
    setStoredTokens({ accessToken: 'tok-1', refreshToken: 'ref-1' });
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    await apiRequest('/dashboard/summary');
    expect(fetchMock.mock.calls[0][1].headers.get('Authorization')).toBe('Bearer tok-1');
  });

  it('clears session and reports expiry on unexpected 401', async () => {
    setStoredTokens({ accessToken: 'stale', refreshToken: 'stale-r' });
    const expired = vi.fn();
    window.addEventListener('auth:session-expired', expired);
    fetchMock.mockResolvedValue(new Response('{}', { status: 401 }));
    await expect(apiRequest('/notifications')).rejects.toThrow(/Session expired/);
    expect(sessionStorage.getItem('saksha_access_token')).toBeNull();
    expect(expired).toHaveBeenCalled();
    window.removeEventListener('auth:session-expired', expired);
  });

  it('extracts FastAPI detail strings into error messages', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ detail: 'Badge not found' }), { status: 404 }));
    await expect(apiRequest('/firs/abc')).rejects.toThrow('Badge not found');
  });

  it('formats validation detail arrays readably', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({
      detail: [{ loc: ['body', 'username'], msg: 'field required' }],
    }), { status: 422 }));
    await expect(apiRequest('/auth/login')).rejects.toThrow("Field 'username': field required");
  });

  it('resolves undefined for 204 responses', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    await expect(apiRequest('/ai/chat-history/conversations/x', { method: 'DELETE' })).resolves.toBeUndefined();
  });

  it('clearStoredTokens removes both tokens', () => {
    setStoredTokens({ accessToken: 'a', refreshToken: 'b' });
    clearStoredTokens();
    expect(sessionStorage.getItem('saksha_access_token')).toBeNull();
    expect(sessionStorage.getItem('saksha_refresh_token')).toBeNull();
  });
});

