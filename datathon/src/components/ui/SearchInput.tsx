import React, { useState, useRef, useEffect } from 'react';
import { Search, X } from 'lucide-react';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  onClear?: () => void;
  className?: string;
  autoFocus?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const SearchInput: React.FC<SearchInputProps> = ({
  value,
  onChange,
  placeholder = 'Search...',
  onClear,
  className = '',
  autoFocus = false,
  size = 'md',
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const sizeClasses = {
    sm: 'text-xs px-3 py-1.5 pl-8',
    md: 'text-sm px-3 py-2 pl-9',
    lg: 'text-sm px-4 py-2.5 pl-10',
  };

  const iconSize = { sm: 'w-3.5 h-3.5 left-2.5', md: 'w-4 h-4 left-3', lg: 'w-4.5 h-4.5 left-3.5' };

  return (
    <div className={`relative ${className}`}>
      <Search className={`absolute top-1/2 -translate-y-1/2 text-[var(--text-muted)] ${iconSize[size]}`} />
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoFocus={autoFocus}
        className={`w-full bg-[var(--bg-tertiary)] border border-[var(--border-secondary)] rounded-lg text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--border-focus)] focus:ring-1 focus:ring-[var(--border-focus)] outline-none transition-all ${sizeClasses[size]}`}
      />
      {value && onClear && (
        <button
          onClick={() => { onChange(''); onClear(); }}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};

export default SearchInput;
