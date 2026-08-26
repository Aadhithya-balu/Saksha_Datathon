import { create } from 'zustand';
import {
  clearStoredTokens,
  getMe,
  getStoredTokens,
  login as loginRequest,
  logout as logoutRequest,
  mapBackendRoleToUiRole,
  refreshSession,
  setStoredTokens,
} from '../services/api';

export type UserRole = 'SCRB' | 'IO' | 'SP' | 'INSPECTOR' | 'FORENSIC' | 'VIEWER' | 'ADMIN';

export interface UserSession {
  name: string;
  badgeId: string;
  role: UserRole;
}

interface AuthState {
  user: UserSession | null;
  isAuthenticated: boolean;
  loginError: string | null;
  sessionTimeRemaining: number;
  isHydrating: boolean;
  initializeSession: () => Promise<void>;
  login: (badgeId: string, pin: string) => Promise<boolean>;
  logout: (expired?: boolean) => void;
  tickSession: () => void;
  resetSessionTimer: () => void;
  updateUser: (patch: Partial<UserSession>) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  loginError: null,
  sessionTimeRemaining: 1800, // 30 minutes
  isHydrating: true,

  initializeSession: async () => {
    const hydrateFromBackendUser = async () => {
      const currentUser = await getMe();
      set({
        user: {
          name: currentUser.full_name,
          badgeId: currentUser.username,
          role: mapBackendRoleToUiRole(currentUser.role),
        },
        isAuthenticated: true,
        loginError: null,
        sessionTimeRemaining: 1800,
        isHydrating: false,
      });
    };

    const { accessToken, refreshToken } = getStoredTokens();

    if (!accessToken && !refreshToken) {
      set({ user: null, isAuthenticated: false, loginError: null, isHydrating: false });
      return;
    }

    try {
      if (accessToken) {
        await hydrateFromBackendUser();
        return;
      }

      const tokens = await refreshSession(refreshToken);
      setStoredTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
      await hydrateFromBackendUser();
    } catch {
      if (refreshToken) {
        try {
          const tokens = await refreshSession(refreshToken);
          setStoredTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
          await hydrateFromBackendUser();
          return;
        } catch {
          clearStoredTokens();
        }
      } else {
        clearStoredTokens();
      }
      set({ user: null, isAuthenticated: false, loginError: null, isHydrating: false });
    }
  },

  login: async (badgeId: string, pin: string) => {
    // Use the input as-is (case-sensitive DB lookup; seed data uses lowercase 'admin')
    const cleanId = badgeId.trim();
    const cleanPin = pin.trim();

    try {
      const tokens = await loginRequest(cleanId, cleanPin);
      setStoredTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });

      const currentUser = await getMe();
      set({
        user: {
          name: currentUser.full_name,
          badgeId: currentUser.username,
          role: mapBackendRoleToUiRole(currentUser.role),
        },
        isAuthenticated: true,
        loginError: null,
        sessionTimeRemaining: tokens.expires_in || 1800,
      });
      return true;
    } catch (error) {
      clearStoredTokens();
      const message = error instanceof Error ? error.message : 'Access Denied: Invalid Badge ID or PIN.';
      set({
        loginError: message.includes('temporarily unavailable')
          ? 'Backend database is offline. Start PostgreSQL and Neo4j, then retry login.'
          : message,
      });
      return false;
    }
  },

  logout: (expired = false) => {
    const { accessToken } = getStoredTokens();
    if (accessToken) {
      void logoutRequest().catch(() => undefined);
    }
    clearStoredTokens();
    set({ user: null, isAuthenticated: false, sessionTimeRemaining: 1800, loginError: expired ? 'Session Expired: Please log in again.' : null });
    // Always navigate to /login so the protected URL is never visible after logout
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('auth:navigate-login'));
    }
  },

  tickSession: () => {
    const current = get().sessionTimeRemaining;
    if (current <= 1) {
      get().logout(true);
    } else {
      set({ sessionTimeRemaining: current - 1 });
    }
  },

  resetSessionTimer: () => {
    if (get().isAuthenticated) {
      set({ sessionTimeRemaining: 1800 });
    }
  },

  updateUser: (patch: Partial<UserSession>) => {
    const current = get().user;
    if (current) set({ user: { ...current, ...patch } });
  },
}));

if (typeof window !== 'undefined') {
  window.addEventListener('auth:session-expired', () => {
    useAuthStore.getState().logout(true);
  });
}
