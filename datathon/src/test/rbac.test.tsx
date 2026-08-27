import { describe, expect, it, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RoleGuard } from '../components/layout/RoleGuard';
import { useAuthStore } from '../store/authStore';
import { ROUTE_PERMISSIONS } from '../hooks/useRBAC';
import type { UserRole } from '../store/authStore';

function loginAs(role: UserRole | null) {
  useAuthStore.setState({
    user: role ? { name: `Officer ${role}`, badgeId: `BADGE-${role}`, role } : null,
    isAuthenticated: Boolean(role),
    isHydrating: false,
  });
}

beforeEach(() => {
  useAuthStore.setState({ user: null, isAuthenticated: false, isHydrating: false });
});

describe('RoleGuard access control', () => {
  it('demands authentication for anonymous visitors', () => {
    loginAs(null);
    render(<RoleGuard path="/admin"><div>SECRET PANEL</div></RoleGuard>);
    expect(screen.getByText(/Authentication Required/i)).toBeInTheDocument();
    expect(screen.queryByText('SECRET PANEL')).not.toBeInTheDocument();
  });

  it('blocks unauthorized roles from restricted modules', () => {
    loginAs('VIEWER');
    render(<RoleGuard path="/admin"><div>SECRET PANEL</div></RoleGuard>);
    expect(screen.getByText(/Access Restriction Triggered/i)).toBeInTheDocument();
    expect(screen.queryByText('SECRET PANEL')).not.toBeInTheDocument();
  });

  it('admits authorized roles to restricted modules', () => {
    loginAs('ADMIN');
    render(<RoleGuard path="/admin"><div>SECRET PANEL</div></RoleGuard>);
    expect(screen.getByText('SECRET PANEL')).toBeInTheDocument();
  });

  it('opens /settings to all signed-in roles, keeping /admin admin-only', () => {
    expect(ROUTE_PERMISSIONS['/settings'].allowedRoles).toEqual(expect.arrayContaining(['VIEWER', 'SCRB', 'IO', 'SP']));
    expect(ROUTE_PERMISSIONS['/admin'].allowedRoles).toEqual(['ADMIN']);
    expect(ROUTE_PERMISSIONS['/dashboard'].allowedRoles).toContain('VIEWER');
  });

  it('renders content for unrestricted modules with any signed-in role', () => {
    loginAs('SCRB');
    render(<RoleGuard path="/ai-chat"><div>AI ASSISTANT</div></RoleGuard>);
    expect(screen.getByText('AI ASSISTANT')).toBeInTheDocument();
  });
});
