import { useAuthStore } from '../store/authStore';
import type { UserRole } from '../store/authStore';

export interface RoutePermission {
  allowedRoles: UserRole[];
  moduleName: string;
}

export const ROUTE_PERMISSIONS: Record<string, RoutePermission> = {
  '/dashboard': { allowedRoles: ['SCRB', 'IO', 'SP', 'INSPECTOR', 'FORENSIC', 'VIEWER'], moduleName: 'Overview Dashboard' },
  '/hotspots': { allowedRoles: ['SCRB', 'IO'], moduleName: 'Crime Hotspot Map' },
  '/network': { allowedRoles: ['SCRB', 'IO'], moduleName: 'Criminal Network Analytics' },
  '/predictions': { allowedRoles: ['SCRB', 'IO'], moduleName: 'Predictive Crime AI Engine' },
  '/anomalies': { allowedRoles: ['SCRB', 'IO', 'SP'], moduleName: 'Anomaly Detection Engine' },
  '/offenders': { allowedRoles: ['SCRB', 'IO'], moduleName: 'Offender Registry' },
  '/reports': { allowedRoles: ['SCRB', 'IO', 'SP'], moduleName: 'Reports Center' },
  '/settings': { allowedRoles: ['SCRB', 'IO', 'SP', 'INSPECTOR', 'FORENSIC', 'VIEWER'], moduleName: 'Settings & Operator Help' },
  '/admin': { allowedRoles: ['SCRB'], moduleName: 'System Security Control Center' },
  '/ai-chat': { allowedRoles: ['SCRB', 'IO', 'SP'], moduleName: 'AI Chat Assistant' },
  '/crime-cases': { allowedRoles: ['SCRB', 'IO', 'SP'], moduleName: 'Crime Case Management' },
  '/firs': { allowedRoles: ['SCRB', 'IO', 'SP'], moduleName: 'FIR Lifecycle Management' },
  '/officers': { allowedRoles: ['SCRB'], moduleName: 'Officer Management' },
  '/evidence': { allowedRoles: ['SCRB', 'IO', 'SP', 'INSPECTOR', 'FORENSIC', 'VIEWER'], moduleName: 'Evidence Handling' },
};

export const useRBAC = () => {
  const user = useAuthStore((state) => state.user);

  const checkPermission = (path: string): boolean => {
    if (!user) return false;
    const rule = ROUTE_PERMISSIONS[path];
    if (!rule) return true; // public path or not restricted
    return rule.allowedRoles.includes(user.role);
  };

  const getRequiredRoles = (path: string): UserRole[] => {
    return ROUTE_PERMISSIONS[path]?.allowedRoles || [];
  };

  return {
    user,
    role: user?.role || null,
    checkPermission,
    getRequiredRoles,
    isSCRB: user?.role === 'SCRB',
    isIO: user?.role === 'IO',
    isSP: user?.role === 'SP',
    isInspector: user?.role === 'INSPECTOR',
    isForensic: user?.role === 'FORENSIC',
    isViewer: user?.role === 'VIEWER',
  };
};
