import { create } from 'zustand';

export type UserRole = 'SCRB' | 'IO' | 'SP';

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

  login: async (badgeId: string, pin: string) => {
    // Standard credential checking:
    // SCRB Analyst: sees all modules (badge starting with SCRB, e.g., SCRB-7740)
    // Investigating Officer: no access to admin (badge starting with IO, e.g., IO-3921)
    // Superintendent of Police: summary + alerts only (badge starting with SP, e.g., SP-0088)
    
    let user: UserSession | null = null;
    const cleanId = badgeId.trim().toUpperCase();
    const cleanPin = pin.trim();

    if (cleanPin === '123456' || cleanPin === '987654') {
      if (cleanId.startsWith('SCRB')) {
        user = { name: 'DCP Rajesh Kumar', badgeId: cleanId, role: 'SCRB' };
      } else if (cleanId.startsWith('IO')) {
        user = { name: 'Inspector Meera Sen', badgeId: cleanId, role: 'IO' };
      } else if (cleanId.startsWith('SP')) {
        user = { name: 'SP Anil Kumble', badgeId: cleanId, role: 'SP' };
      }
    }

    if (user) {
      // Simulate setting httpOnly cookie for session security
      document.cookie = `session_token=ksp_jwt_mock_${user.role}_${Date.now()}; path=/; max-age=1800; samesite=strict`;
      set({ user, isAuthenticated: true, loginError: null, sessionTimeRemaining: 1800 });
      return true;
    } else {
      set({ loginError: 'Access Denied: Invalid Badge ID or PIN. (Use PIN 123456 and Prefix SCRB, IO, or SP)' });
      return false;
    }
  },

  loginWithFace: async () => {
    // Face ID defaults to Senior SCRB analyst role
    const user: UserSession = { name: 'DCP Rajesh Kumar (FaceID)', badgeId: 'SCRB-7740', role: 'SCRB' };
    document.cookie = `session_token=ksp_jwt_mock_SCRB_${Date.now()}; path=/; max-age=1800; samesite=strict`;
    set({ user, isAuthenticated: true, loginError: null, sessionTimeRemaining: 1800 });
    return true;
  },

  logout: (expired = false) => {
    // Clear cookies
    document.cookie = 'session_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
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
