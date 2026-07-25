import { useAuthStore } from '../store/authStore';
import type { UserRole } from '../store/authStore';

export interface RoutePermission {
  allowedRoles: UserRole[];
  moduleName: string;
}

export const ALL_UI_ROLES: UserRole[] = ['ADMIN', 'SCRB', 'IO', 'SP', 'INSPECTOR', 'FORENSIC', 'VIEWER'];

export const ROUTE_PERMISSIONS: Record<string, RoutePermission> = {
  '/dashboard':    { allowedRoles: ALL_UI_ROLES, moduleName: 'Overview Dashboard' },
  '/admin':        { allowedRoles: ['ADMIN'], moduleName: 'System Security Control Center' },
  '/crime-cases':  { allowedRoles: ALL_UI_ROLES, moduleName: 'Crime Case Management' },
  '/firs':         { allowedRoles: ALL_UI_ROLES, moduleName: 'FIR Lifecycle Management' },
  '/offenders':    { allowedRoles: ALL_UI_ROLES, moduleName: 'Offender Registry' },
  '/officers':     { allowedRoles: ALL_UI_ROLES, moduleName: 'Officer Management' },
  '/evidence':     { allowedRoles: ALL_UI_ROLES, moduleName: 'Evidence Handling' },
  '/hotspots':     { allowedRoles: ALL_UI_ROLES, moduleName: 'Crime Hotspot Map' },
  '/network':      { allowedRoles: ALL_UI_ROLES, moduleName: 'Criminal Network Analytics' },
  '/predictions':  { allowedRoles: ALL_UI_ROLES, moduleName: 'Predictive Crime AI Engine' },
  '/anomalies':    { allowedRoles: ALL_UI_ROLES, moduleName: 'Anomaly Detection Engine' },
  '/reports':      { allowedRoles: ALL_UI_ROLES, moduleName: 'Reports Center' },
  '/ai-chat':      { allowedRoles: ALL_UI_ROLES, moduleName: 'AI Chat Assistant' },
  '/settings':     { allowedRoles: ALL_UI_ROLES, moduleName: 'Settings & Operator Help' },
};

export const useRBAC = () => {
  const user = useAuthStore((state) => state.user);

  const checkPermission = (path: string): boolean => {
    if (!user) return false;
    const rule = ROUTE_PERMISSIONS[path];
    if (!rule) return true;
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
    isAdmin: user?.role === 'ADMIN',
    isSCRB: user?.role === 'SCRB',
    isIO: user?.role === 'IO',
    isSP: user?.role === 'SP',
    isInspector: user?.role === 'INSPECTOR',
    isForensic: user?.role === 'FORENSIC',
    isViewer: user?.role === 'VIEWER',
  };
};
