import React from 'react';

type BadgeVariant = 'default' | 'blue' | 'teal' | 'amber' | 'coral' | 'purple' | 'success' | 'warning' | 'error' | 'info';
type BadgeSize = 'xs' | 'sm' | 'md';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  dot?: boolean;
  pulse?: boolean;
  className?: string;
  icon?: React.ReactNode;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-sk-bg-tertiary text-sk-text-secondary border-sk-border-primary',
  blue: 'bg-[var(--accent-blue-subtle)] text-[var(--accent-blue-light)] border-[var(--accent-blue)]/20',
  teal: 'bg-[var(--accent-teal-subtle)] text-[var(--accent-teal-light)] border-[var(--accent-teal)]/20',
  amber: 'bg-[var(--accent-amber-subtle)] text-[var(--accent-amber-light)] border-[var(--accent-amber)]/20',
  coral: 'bg-[var(--accent-coral-subtle)] text-[var(--accent-coral-light)] border-[var(--accent-coral)]/20',
  purple: 'bg-[var(--accent-purple-subtle)] text-[var(--accent-purple-light)] border-[var(--accent-purple)]/20',
  success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  warning: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  error: 'bg-red-500/10 text-red-400 border-red-500/20',
  info: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
};

const sizeStyles: Record<BadgeSize, string> = {
  xs: 'px-1.5 py-0.5 text-[10px] gap-1',
  sm: 'px-2 py-0.5 text-[11px] gap-1.5',
  md: 'px-2.5 py-1 text-xs gap-1.5',
};

const dotColorMap: Record<BadgeVariant, string> = {
  default: 'bg-sk-text-muted',
  blue: 'bg-[var(--accent-blue)]',
  teal: 'bg-[var(--accent-teal)]',
  amber: 'bg-[var(--accent-amber)]',
  coral: 'bg-[var(--accent-coral)]',
  purple: 'bg-[var(--accent-purple)]',
  success: 'bg-emerald-400',
  warning: 'bg-amber-400',
  error: 'bg-red-400',
  info: 'bg-blue-400',
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'sm',
  dot = false,
  pulse = false,
  className = '',
  icon,
}) => {
  return (
    <span
      className={`inline-flex items-center font-medium border rounded-full whitespace-nowrap ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {dot && (
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColorMap[variant]} ${pulse ? 'animate-sk-pulse-dot' : ''}`} />
      )}
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </span>
  );
};

export const StatusBadge: React.FC<{ status: string; className?: string }> = ({ status, className = '' }) => {
  const statusMap: Record<string, { variant: BadgeVariant; label: string }> = {
    open: { variant: 'blue', label: 'Open' },
    active: { variant: 'teal', label: 'Active' },
    closed: { variant: 'default', label: 'Closed' },
    pending: { variant: 'amber', label: 'Pending' },
    critical: { variant: 'coral', label: 'Critical' },
    high: { variant: 'coral', label: 'High' },
    medium: { variant: 'amber', label: 'Medium' },
    low: { variant: 'teal', label: 'Low' },
    arrest_warrant: { variant: 'coral', label: 'Arrest Warrant' },
    under_investigation: { variant: 'purple', label: 'Under Investigation' },
    convicted: { variant: 'error', label: 'Convicted' },
    acquitted: { variant: 'teal', label: 'Acquitted' },
    escaped: { variant: 'coral', label: 'Escaped' },
    deceased: { variant: 'default', label: 'Deceased' },
    digital: { variant: 'purple', label: 'Digital' },
    document: { variant: 'blue', label: 'Document' },
  };

  const config = statusMap[status.toLowerCase()] || { variant: 'default' as BadgeVariant, label: status };
  return <Badge variant={config.variant} dot size="sm" className={className}>{config.label}</Badge>;
};

export default Badge;
