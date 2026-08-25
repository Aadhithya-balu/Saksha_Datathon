import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';

const { mockPage, backendUser } = vi.hoisted(() => ({
  mockPage: (label: string) => ({ default: () => <div>{label}</div> }),
  backendUser: {
    id: 'u-1',
    username: 'TEST-ADMIN-1',
    email: 'admin@saksha.gov.in',
    full_name: 'Test Admin',
    district: 'Bengaluru Urban',
    station: 'HQ',
    is_active: true,
    role: 'admin',
    created_at: '2026-01-01T00:00:00Z',
  },
}));

vi.mock('../services/api', () => ({
  login: vi.fn(),
  logout: vi.fn().mockResolvedValue({}),
  refreshSession: vi.fn(),
  getMe: vi.fn().mockResolvedValue(backendUser),
  mapBackendRoleToUiRole: (role: string) => String(role).toUpperCase(),
  setStoredTokens: vi.fn((t: { accessToken: string; refreshToken: string }) => {
    sessionStorage.setItem('saksha_access_token', t.accessToken);
    sessionStorage.setItem('saksha_refresh_token', t.refreshToken);
  }),
  getStoredTokens: vi.fn(() => ({
    accessToken: sessionStorage.getItem('saksha_access_token'),
    refreshToken: sessionStorage.getItem('saksha_refresh_token'),
  })),
  clearStoredTokens: vi.fn(() => {
    sessionStorage.removeItem('saksha_access_token');
    sessionStorage.removeItem('saksha_refresh_token');
  }),
}));

vi.mock('../pages/Login', () => mockPage('LOGIN-MARKER'));
vi.mock('../pages/Overview', () => mockPage('OVERVIEW-PAGE'));
vi.mock('../pages/Hotspots', () => mockPage('HOTSPOTS-PAGE'));
vi.mock('../pages/Network', () => mockPage('NETWORK-PAGE'));
vi.mock('../pages/Predictions', () => mockPage('PREDICTIONS-PAGE'));
vi.mock('../pages/Anomalies', () => mockPage('ANOMALIES-PAGE'));
vi.mock('../pages/Offenders', () => mockPage('OFFENDERS-PAGE'));
vi.mock('../pages/Reports', () => mockPage('REPORTS-PAGE'));
vi.mock('../pages/AIChat', () => mockPage('AICHAT-PAGE'));
vi.mock('../pages/CrimeCases', () => mockPage('CRIMECASES-PAGE'));
vi.mock('../pages/FIR', () => mockPage('FIR-PAGE'));
vi.mock('../pages/Criminals', () => mockPage('CRIMINALS-PAGE'));
vi.mock('../pages/Victims', () => mockPage('VICTIMS-PAGE'));
vi.mock('../pages/Officers', () => mockPage('OFFICERS-PAGE'));
vi.mock('../pages/Evidence', () => mockPage('EVIDENCE-PAGE'));
vi.mock('../pages/Investigation', () => mockPage('INVESTIGATION-PAGE'));
vi.mock('../pages/Notifications', () => mockPage('NOTIFICATIONS-PAGE'));
vi.mock('../pages/Sociological', () => mockPage('SOCIOLOGICAL-PAGE'));
vi.mock('../pages/Strategic', () => mockPage('STRATEGIC-PAGE'));
vi.mock('../pages/Docs', () => mockPage('DOCS-PAGE'));
vi.mock('../pages/SettingsHelp', () => mockPage('SETTINGS-PAGE'));
vi.mock('../pages/Admin', () => mockPage('ADMIN-PAGE'));
vi.mock('../components/layout/Sidebar', () => ({
  default: () => <nav data-testid="sidebar" />,
}));
vi.mock('../components/layout/Header', () => ({
  default: () => <header data-testid="header" />,
}));
vi.mock('../components/ui/CommandPalette', () => ({ default: () => null }));
vi.mock('../components/ai/GlobalAIAssistant', () => ({ default: () => null }));

import App from '../App';

function seedSession() {
  sessionStorage.setItem('saksha_access_token', 'acc');
  sessionStorage.setItem('saksha_refresh_token', 'ref');
}

beforeEach(() => {
  window.history.pushState({}, '', '/');
});

describe('App routing shell', () => {
  it('renders the Login page for unauthenticated visitors', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('LOGIN-MARKER')).toBeInTheDocument());
    expect(screen.queryByTestId('sidebar')).not.toBeInTheDocument();
  });

  it('renders NotFound for unknown deep routes instead of crashing', async () => {
    seedSession();
    window.history.pushState({}, '', '/this/route/does-not-exist');
    render(<App />);
    await waitFor(() => expect(screen.getByText(/404/i)).toBeInTheDocument());
    expect(screen.queryByTestId('sidebar')).not.toBeInTheDocument();
  });

  it('serves the authenticated dashboard shell at root', async () => {
    seedSession();
    render(<App />);
    await waitFor(() => expect(screen.getByText('OVERVIEW-PAGE')).toBeInTheDocument(), { timeout: 5000 });
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('header')).toBeInTheDocument();
  });

  it('restores the requested page from a deep URL on refresh', async () => {
    seedSession();
    window.history.pushState({}, '', '/ai-chat');
    render(<App />);

    await waitFor(() => expect(screen.getByText('AICHAT-PAGE')).toBeInTheDocument(), { timeout: 5000 });
    expect(window.location.pathname).toBe('/ai-chat');
  });

  it('restores the matching page when browser history changes', async () => {
    seedSession();
    window.history.pushState({}, '', '/ai-chat');
    render(<App />);
    await waitFor(() => expect(screen.getByText('AICHAT-PAGE')).toBeInTheDocument(), { timeout: 5000 });

    window.history.pushState({}, '', '/notifications');
    act(() => window.dispatchEvent(new PopStateEvent('popstate')));
    await waitFor(() => expect(screen.getByText('NOTIFICATIONS-PAGE')).toBeInTheDocument());
    expect(window.location.pathname).toBe('/notifications');
  });

  it('blocks admins-only modules for unauthorized roles via RoleGuard', async () => {
    seedSession();
    const { getMe } = await import('../services/api');
    vi.mocked(getMe).mockResolvedValue({ ...backendUser, role: 'viewer' });
    const { useAppStore } = await import('../store/appStore');
    useAppStore.getState().setActiveTab('admin');
    render(<App />);
    expect(
      await screen.findByText(/Access Restriction Triggered/i, {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.queryByText('ADMIN-PAGE')).not.toBeInTheDocument();
  });

  it('admits authorized roles into restricted modules', async () => {
    seedSession();
    const { useAppStore } = await import('../store/appStore');
    useAppStore.getState().setActiveTab('docs');
    render(<App />);
    await waitFor(() => expect(screen.getByText('DOCS-PAGE')).toBeInTheDocument(), { timeout: 5000 });
  });
});
