import React, { useState } from 'react';
import {
  Activity,
  Cpu,
  Radar,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react';
import type { UnifiedIntelligenceResult } from '../../services/api';
import SentinelAlertCard from './SentinelAlertCard';
import SentinelWorkflowModal, { type ModalTab } from './SentinelWorkflowModal';

interface IntelligencePatternsFeedProps {
  patterns: UnifiedIntelligenceResult[];
  total: number;
  loading?: boolean;
  running?: boolean;
  error?: string | null;
  onRunFusion?: () => void;
  onInvestigate?: (pattern: UnifiedIntelligenceResult) => void;
}

const IntelligencePatternsFeed: React.FC<IntelligencePatternsFeedProps> = ({
  patterns,
  total,
  loading = false,
  running = false,
  error = null,
  onRunFusion,
  onInvestigate,
}) => {
  const [selectedPattern, setSelectedPattern] = useState<UnifiedIntelligenceResult | null>(null);
  const [modalTab, setModalTab] = useState<ModalTab>('recommendation');
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleInvestigate = (p: UnifiedIntelligenceResult) => {
    if (onInvestigate) {
      onInvestigate(p);
      return;
    }
    const targetId =
      p.related_fir_ids?.[0] ||
      p.related_entity_ids?.[0] ||
      p.location?.district;
    window.dispatchEvent(
      new CustomEvent('navigate-tab', {
        detail: { tab: 'investigation', targetId: targetId },
      })
    );
  };

  const handleWhyThisInsight = (p: UnifiedIntelligenceResult) => {
    setSelectedPattern(p);
    setModalTab('why_insight');
    setIsModalOpen(true);
  };

  const handlePlanIntervention = (p: UnifiedIntelligenceResult) => {
    setSelectedPattern(p);
    setModalTab('recommendation');
    setIsModalOpen(true);
  };

  return (
    <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 overflow-hidden select-none">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 px-3.5 py-2.5 border-b border-[var(--border-primary)] bg-[var(--bg-elevated)]/40">
        <div className="flex items-center gap-2">
          <span className="w-6 h-6 rounded-md flex items-center justify-center border border-[#C94A2A]/40 bg-[#C94A2A]/10 text-[#FF6B4A]">
            <Radar className="w-3.5 h-3.5" />
          </span>
          <div>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[var(--text-primary)]">
              Sentinel Intelligence Alerts
            </span>
            <span className="text-[8px] font-mono text-[var(--text-muted)] ml-2">
              ({total} active pattern{total === 1 ? '' : 's'})
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onRunFusion && (
            <button
              onClick={onRunFusion}
              disabled={running || loading}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[#a855f7]/40 bg-[#a855f7]/5 text-[#c084fc] hover:bg-[#a855f7]/15 font-mono text-[8px] uppercase font-bold transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-2.5 h-2.5 ${running ? 'animate-spin' : ''}`} />
              {running ? 'Fusing…' : 'Run Fusion'}
            </button>
          )}
        </div>
      </div>

      <p className="px-3.5 py-2 border-b border-[var(--border-primary)]/60 text-[8px] font-mono text-[var(--text-muted)] bg-[var(--bg-primary)]/20">
        Officer Sentinel Interface: Converts fused intelligence into structured recommendations, simulation comparison, and human approval workflow.
      </p>

      {/* Body */}
      {loading ? (
        <div className="p-8 text-center">
          <div className="w-6 h-6 mx-auto mb-2 border-2 border-[#C94A2A]/20 border-t-[#C94A2A] rounded-full animate-spin" />
          <span className="text-[9.5px] font-mono text-[var(--text-muted)] uppercase tracking-wider">
            Detecting emerging Sentinel patterns…
          </span>
        </div>
      ) : error ? (
        <div className="p-6 text-center">
          <ShieldAlert className="w-7 h-7 text-amber-400 mx-auto mb-2" />
          <p className="text-[10px] font-mono text-[var(--text-secondary)]">{error}</p>
        </div>
      ) : patterns.length === 0 ? (
        <div className="p-10 text-center">
          <Activity className="w-7 h-7 text-[var(--text-muted)] mx-auto mb-2 opacity-50" />
          <p className="text-[10.5px] font-mono text-[var(--text-muted)] uppercase tracking-wider font-semibold">
            No patterns detected for current filters
          </p>
          <p className="text-[9px] text-[var(--text-muted)] mt-1">
            Widen the observation window or adjust the detection sensitivity in the control bar above.
          </p>
        </div>
      ) : (
        <div className="p-3 space-y-3 max-h-[700px] overflow-y-auto custom-scrollbar">
          {patterns.map((p) => (
            <SentinelAlertCard
              key={p.intelligence_id}
              pattern={p}
              onInvestigate={handleInvestigate}
              onWhyThisInsight={handleWhyThisInsight}
              onPlanIntervention={handlePlanIntervention}
            />
          ))}
        </div>
      )}

      {patterns.length > 0 && (
        <div className="px-3.5 py-2 border-t border-[var(--border-primary)] bg-[var(--bg-elevated)]/30 text-[7.5px] font-mono text-[var(--text-muted)] flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Cpu className="w-3 h-3" />
            <span>Modes: {Array.from(new Set(patterns.map((p) => p.ml_status))).join(' / ')}</span>
            <span>· Model v{patterns[0]?.model_version || '1.0'}</span>
          </div>
          <span className="uppercase text-[var(--text-muted)]">
            Human-in-the-loop prevention loop active
          </span>
        </div>
      )}

      {/* Workflow & Explainability Modal */}
      <SentinelWorkflowModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        pattern={selectedPattern}
        initialTab={modalTab}
        onNavigateToInvestigation={(targetId) => {
          window.dispatchEvent(
            new CustomEvent('navigate-tab', {
              detail: { tab: 'investigation', targetId },
            })
          );
        }}
      />
    </div>
  );
};

export default IntelligencePatternsFeed;