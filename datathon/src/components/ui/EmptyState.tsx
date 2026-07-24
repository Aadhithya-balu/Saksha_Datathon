import React from 'react';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary';
  };
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center py-16 px-6 text-center ${className}`}>
      {icon && (
        <div className="w-16 h-16 rounded-2xl bg-sk-bg-tertiary border border-sk-border-primary flex items-center justify-center text-sk-text-muted mb-5">
          {icon}
        </div>
      )}
      <h3 className="text-base font-semibold text-sk-text-primary mb-2">{title}</h3>
      <p className="text-sm text-sk-text-muted max-w-sm mb-6">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all cursor-pointer ${
            action.variant === 'secondary'
              ? 'bg-sk-bg-tertiary text-sk-text-secondary border border-sk-border-primary hover:bg-sk-bg-elevated'
              : 'bg-[var(--accent-blue)] text-[var(--text-primary)] hover:bg-[var(--accent-blue-light)] shadow-sk-sm'
          }`}
        >
          {action.label}
        </button>
      )}
    </div>
  );
};

export const ErrorState: React.FC<{
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}> = ({
  title = 'Something went wrong',
  description = 'An unexpected error occurred. Please try again.',
  onRetry,
  className = '',
}) => {
  return (
    <EmptyState
      icon={
        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
      }
      title={title}
      description={description}
      action={onRetry ? { label: 'Try Again', onClick: onRetry, variant: 'primary' } : undefined}
      className={className}
    />
  );
};

export default EmptyState;
