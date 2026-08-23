import React from 'react';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  count?: number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'text',
  width,
  height,
  count = 1,
}) => {
  const baseClass = 'sk-skeleton';
  const variantClass = {
    text: 'rounded-sm',
    circular: 'rounded-full',
    rectangular: 'rounded-md',
    rounded: 'rounded-xl',
  }[variant];

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`${baseClass} ${variantClass}`}
          style={{
            width: width || (variant === 'circular' ? 40 : '100%'),
            height: height || (variant === 'text' ? 16 : variant === 'circular' ? 40 : 200),
          }}
        />
      ))}
    </div>
  );
};

export const CardSkeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`sk-card ${className}`}>
    <div className="flex items-center gap-3 mb-4">
      <Skeleton variant="circular" width={40} height={40} />
      <div className="flex-1">
        <Skeleton width="60%" height={16} />
        <Skeleton width="40%" height={12} className="mt-1" />
      </div>
    </div>
    <Skeleton count={3} />
  </div>
);

export const TableSkeleton: React.FC<{ rows?: number; cols?: number; className?: string }> = ({
  rows = 5,
  cols = 4,
  className = '',
}) => (
  <div className={`sk-card p-0 overflow-hidden ${className}`}>
    <div className="p-4 border-b border-sk-border-primary">
      <Skeleton width="30%" height={20} />
    </div>
    <div className="p-4 space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          {Array.from({ length: cols }).map((_, j) => (
            <Skeleton key={j} className="flex-1" height={14} />
          ))}
        </div>
      ))}
    </div>
  </div>
);

export const StatCardSkeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`sk-card ${className}`}>
    <div className="flex items-start justify-between mb-3">
      <Skeleton variant="circular" width={44} height={44} />
      <Skeleton width={60} height={14} />
    </div>
    <Skeleton width="80%" height={28} className="mb-2" />
    <Skeleton width="50%" height={14} />
  </div>
);

export const PageSkeleton: React.FC = () => (
  <div className="space-y-6 sk-page-enter">
    <div className="flex items-center justify-between">
      <Skeleton width={250} height={28} />
      <Skeleton width={120} height={36} variant="rounded" />
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <StatCardSkeleton key={i} />
      ))}
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2">
        <CardSkeleton />
      </div>
      <CardSkeleton />
    </div>
  </div>
);

export default Skeleton;
