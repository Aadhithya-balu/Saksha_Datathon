import React from 'react';

interface Tab {
  id: string;
  label: string;
  icon?: React.ReactNode;
  count?: number;
  disabled?: boolean;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
  size?: 'sm' | 'md';
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  className = '',
  size = 'md',
}) => {
  const sizeClasses = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-sm px-3 py-2 gap-2',
  };

  return (
    <div className={`flex items-center gap-1 p-1 bg-[var(--bg-tertiary)] rounded-lg overflow-x-auto ${className}`}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => !tab.disabled && onChange(tab.id)}
          disabled={tab.disabled}
          className={`inline-flex items-center font-medium rounded-md whitespace-nowrap transition-all cursor-pointer ${
            sizeClasses[size]
          } ${
            activeTab === tab.id
              ? 'bg-[var(--bg-elevated)] text-[var(--text-primary)] shadow-sk-xs'
              : tab.disabled
              ? 'text-[var(--text-disabled)] cursor-not-allowed'
              : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)]/50'
          }`}
        >
          {tab.icon && <span className="shrink-0">{tab.icon}</span>}
          {tab.label}
          {tab.count !== undefined && (
            <span className={`ml-1 px-1.5 py-0.5 text-[10px] rounded-full ${
              activeTab === tab.id ? 'bg-[var(--accent-blue)]/20 text-[var(--accent-blue)]' : 'bg-[var(--bg-secondary)] text-[var(--text-muted)]'
            }`}>
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
};

export interface TabPanelProps {
  activeTab: string;
  tabId: string;
  children: React.ReactNode;
  className?: string;
}

export const TabPanel: React.FC<TabPanelProps> = ({ activeTab, tabId, children, className = '' }) => {
  if (activeTab !== tabId) return null;
  return <div className={`sk-fade-in ${className}`}>{children}</div>;
};

export default Tabs;
