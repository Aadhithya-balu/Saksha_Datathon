import React, { useState } from 'react';
import { Filter, FileText, User, ShieldAlert, X } from 'lucide-react';
import type { ChatContextOptions } from '../../services/api';

interface ContextSelectorProps {
  context: ChatContextOptions;
  onChange: (newContext: ChatContextOptions) => void;
}

export const ContextSelector: React.FC<ContextSelectorProps> = ({ context, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [firInput, setFirInput] = useState(context.firId || '');
  const [criminalInput, setCriminalInput] = useState(context.criminalId || '');
  const [evidenceInput, setEvidenceInput] = useState(context.evidenceId || '');

  const hasContext = Boolean(context.firId || context.criminalId || context.evidenceId || context.caseId);

  const handleApply = () => {
    onChange({
      firId: firInput.trim() || undefined,
      criminalId: criminalInput.trim() || undefined,
      evidenceId: evidenceInput.trim() || undefined,
      caseId: context.caseId,
    });
    setIsOpen(false);
  };

  const handleClear = () => {
    setFirInput('');
    setCriminalInput('');
    setEvidenceInput('');
    onChange({});
    setIsOpen(false);
  };

  return (
    <div className="flex items-center gap-2 font-mono text-[9.5px]">
      {/* Active context pills */}
      {hasContext && (
        <div className="flex items-center gap-1.5 flex-wrap">
          {context.firId && (
            <span className="px-2 py-0.5 bg-sky-950/60 border border-sky-800/60 text-sky-400 rounded flex items-center gap-1 font-bold">
              <FileText className="w-3 h-3" />
              FIR: {context.firId}
              <button
                onClick={() => onChange({ ...context, firId: undefined })}
                className="hover:text-red-400 font-bold ml-1 cursor-pointer"
              >
                ×
              </button>
            </span>
          )}

          {context.criminalId && (
            <span className="px-2 py-0.5 bg-amber-950/60 border border-amber-800/60 text-amber-400 rounded flex items-center gap-1 font-bold">
              <User className="w-3 h-3" />
              Suspect: {context.criminalId}
              <button
                onClick={() => onChange({ ...context, criminalId: undefined })}
                className="hover:text-red-400 font-bold ml-1 cursor-pointer"
              >
                ×
              </button>
            </span>
          )}

          {context.evidenceId && (
            <span className="px-2 py-0.5 bg-rose-950/60 border border-rose-800/60 text-rose-400 rounded flex items-center gap-1 font-bold">
              <ShieldAlert className="w-3 h-3" />
              Evidence: {context.evidenceId}
              <button
                onClick={() => onChange({ ...context, evidenceId: undefined })}
                className="hover:text-red-400 font-bold ml-1 cursor-pointer"
              >
                ×
              </button>
            </span>
          )}

          <button
            onClick={() => onChange({})}
            className="text-[var(--text-muted)] hover:text-red-400 transition-colors uppercase font-bold text-[8.5px] cursor-pointer"
          >
            Clear All
          </button>
        </div>
      )}

      {/* Scope Context Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`px-2.5 py-1 rounded border font-bold uppercase tracking-wider transition-all flex items-center gap-1 cursor-pointer ${
          hasContext
            ? 'bg-[var(--accent-blue)]/20 border-[var(--accent-blue)]/50 text-[var(--accent-blue)]'
            : 'bg-[var(--bg-tertiary)]/60 border-[var(--border-primary)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border-secondary)]'
        }`}
      >
        <Filter className="w-3 h-3" />
        <span>{hasContext ? 'Context Scoped' : 'Scope Context'}</span>
      </button>

      {/* Context Selection Popover */}
      {isOpen && (
        <div className="absolute bottom-14 left-4 z-40 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-card p-4 shadow-2xl max-w-sm w-full space-y-3 font-mono text-left">
          <div className="flex items-center justify-between border-b border-[var(--border-primary)] pb-2">
            <span className="text-[10px] font-bold text-[var(--text-primary)] uppercase tracking-widest flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-[var(--accent-blue)]" />
              Set Intelligence Context
            </span>
            <button
              onClick={() => setIsOpen(false)}
              className="text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2.5">
            <div>
              <label className="text-[8.5px] font-bold text-[var(--text-muted)] uppercase block mb-1">
                FIR ID / Number Filter
              </label>
              <input
                type="text"
                value={firInput}
                onChange={(e) => setFirInput(e.target.value)}
                placeholder="e.g. FIR-2024-001"
                className="w-full bg-[var(--bg-secondary)] border border-[var(--border-primary)] focus:border-[var(--accent-blue)] rounded px-2.5 py-1.5 text-[10.5px] text-[var(--text-primary)] outline-none"
              />
            </div>

            <div>
              <label className="text-[8.5px] font-bold text-[var(--text-muted)] uppercase block mb-1">
                Criminal / Suspect ID Filter
              </label>
              <input
                type="text"
                value={criminalInput}
                onChange={(e) => setCriminalInput(e.target.value)}
                placeholder="e.g. CR-89421"
                className="w-full bg-[var(--bg-secondary)] border border-[var(--border-primary)] focus:border-[var(--accent-blue)] rounded px-2.5 py-1.5 text-[10.5px] text-[var(--text-primary)] outline-none"
              />
            </div>

            <div>
              <label className="text-[8.5px] font-bold text-[var(--text-muted)] uppercase block mb-1">
                Evidence Record ID Filter
              </label>
              <input
                type="text"
                value={evidenceInput}
                onChange={(e) => setEvidenceInput(e.target.value)}
                placeholder="e.g. EV-7890"
                className="w-full bg-[var(--bg-secondary)] border border-[var(--border-primary)] focus:border-[var(--accent-blue)] rounded px-2.5 py-1.5 text-[10.5px] text-[var(--text-primary)] outline-none"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-[var(--border-primary)]">
            <button
              onClick={handleClear}
              className="text-[9px] font-bold text-red-400 hover:text-red-300 uppercase cursor-pointer"
            >
              Reset
            </button>
            <button
              onClick={handleApply}
              className="px-3 py-1 bg-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/85 text-[var(--text-primary)] text-[9.5px] font-bold uppercase rounded cursor-pointer transition-colors"
            >
              Apply Context
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ContextSelector;
