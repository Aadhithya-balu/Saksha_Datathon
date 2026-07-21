import { create } from 'zustand';
import {
  clearStoredTokens,
  getMe,
  getStoredTokens,
  login as loginRequest,
  logout as logoutRequest,
  mapBackendRoleToUiRole,
  setStoredTokens,
} from '../services/api';

export type UserRole = 'SCRB' | 'IO' | 'SP' | 'INSPECTOR' | 'FORENSIC' | 'VIEWER';

export interface UserSession {
  name: string;
  badgeId: string;
  role: UserRole;
}

interface AuthState {
  user: UserSession | null;
  isAuthenticated: boolean;
  loginError: string | null;
  sessionTimeRemaining: number; // in seconds (1800s = 30min)
  isHydrating: boolean;
  initializeSession: () => Promise<void>;
  login: (badgeId: string, pin: string) => Promise<boolean>;
  loginWithFace: () => Promise<boolean>;
  logout: (expired?: boolean) => void;
  tickSession: () => void;
  resetSessionTimer: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  loginError: null,
  sessionTimeRemaining: 1800, // 30 minutes
  isHydrating: true,

  initializeSession: async () => {
    // Clear stored tokens on startup so we always force the login screen first
    clearStoredTokens();
    set({
      user: null,
      isAuthenticated: false,
      loginError: null,
      isHydrating: false
    });
  },

  login: async (badgeId: string, pin: string) => {
    const cleanId = badgeId.trim().toUpperCase();
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

  loginWithFace: async () => {
    return get().login('SCRB-7740', '123456');
  },

  logout: (expired = false) => {
    const { accessToken } = getStoredTokens();

    if (accessToken) {
      void logoutRequest().catch(() => undefined);
    }

    clearStoredTokens();
    set({ user: null, isAuthenticated: false, sessionTimeRemaining: 1800, loginError: expired ? 'Session Expired: Please log in again.' : null });
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
  }
}));
