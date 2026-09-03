import { useAuthStore } from '../store/authStore';
import type { UserRole } from '../store/authStore';

export interface RoutePermission {
  allowedRoles: UserRole[];
  moduleName: string;
}

export const ALL_UI_ROLES: UserRole[] = ['ADMIN', 'SCRB', 'IO', 'SP', 'INSPECTOR', 'FORENSIC', 'VIEWER'];

// Role clearance sets (per CONTEXT.md RBAC).
// crime_analyst -> SCRB, investigator -> IO, inspector -> INSPECTOR,
// policymaker -> SP, forensic -> FORENSIC, viewer -> VIEWER.

// Read-only insight modules are visible to every signed-in role (incl. VIEWER).
// Write / operational modules below are narrowed to their owning roles.
const INSIGHT_ROLES: UserRole[] = ALL_UI_ROLES;
// Reviewers / investigators that own and mutate case-linked records.
const INVESTIGATION_ROLES: UserRole[] = ['ADMIN', 'SCRB', 'IO', 'INSPECTOR'];

export const ROUTE_PERMISSIONS: Record<string, RoutePermission> = {
  // ---- Read-only insight modules (all roles, VIEWER included) ----
  '/dashboard':      { allowedRoles: INSIGHT_ROLES, moduleName: 'Analytics Dashboard' },
  '/command-center': { allowedRoles: INSIGHT_ROLES, moduleName: 'Command Center' },
  '/hotspots':       { allowedRoles: INSIGHT_ROLES, moduleName: 'Crime Hotspot Map' },
  '/network':        { allowedRoles: INSIGHT_ROLES, moduleName: 'Criminal Network Analytics' },
  '/predictions':    { allowedRoles: INSIGHT_ROLES, moduleName: 'Predictive Crime AI Engine' },
  '/anomalies':      { allowedRoles: INSIGHT_ROLES, moduleName: 'Anomaly Detection Engine' },
  '/sociological':   { allowedRoles: INSIGHT_ROLES, moduleName: 'Sociological Intelligence' },
  '/strategic':      { allowedRoles: INSIGHT_ROLES, moduleName: 'Strategic Intelligence' },
  '/reports':        { allowedRoles: INSIGHT_ROLES, moduleName: 'Reports Center' },
  '/offenders':      { allowedRoles: INSIGHT_ROLES, moduleName: 'Offender Registry' },
  '/victims':        { allowedRoles: INSIGHT_ROLES, moduleName: 'Victim Registry' },
  '/notifications':  { allowedRoles: INSIGHT_ROLES, moduleName: 'Intelligence Center' },
  '/ai-chat':        { allowedRoles: INSIGHT_ROLES, moduleName: 'AI Chat Assistant' },
  '/docs':           { allowedRoles: INSIGHT_ROLES, moduleName: 'Documentation' },
  '/settings':       { allowedRoles: INSIGHT_ROLES, moduleName: 'Settings & Operator Help' },

  // ---- Admin / operational write modules (role-narrowed) ----
  '/admin':          { allowedRoles: ['ADMIN'], moduleName: 'System Security Control Center' },
  '/officers':       { allowedRoles: ['ADMIN', 'INSPECTOR'], moduleName: 'Officer Management' },
  '/evidence':       { allowedRoles: ['ADMIN', 'IO', 'INSPECTOR', 'FORENSIC'], moduleName: 'Evidence Handling' },
  '/identity-resolution': { allowedRoles: INVESTIGATION_ROLES, moduleName: 'Identity Resolution & Data Integrity' },
  '/crime-cases':    { allowedRoles: INVESTIGATION_ROLES, moduleName: 'Crime Case Management' },
  '/investigation':  { allowedRoles: INVESTIGATION_ROLES, moduleName: 'Investigation Workspace' },
  '/firs':           { allowedRoles: INVESTIGATION_ROLES, moduleName: 'FIR Lifecycle Management' },
  '/criminals':      { allowedRoles: INVESTIGATION_ROLES, moduleName: 'Criminal Registry' },
  '/intelligence-engine': { allowedRoles: ['ADMIN', 'SCRB', 'IO', 'INSPECTOR', 'SP'], moduleName: 'Intelligence Engine' },
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
