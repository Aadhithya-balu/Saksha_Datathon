import React from 'react';
import type { CrimeCaseInsights } from '../../services/api';
import { 
  Shield, AlertTriangle, CheckCircle2, Activity, 
  BarChart2
} from 'lucide-react';

interface CrimeInsightsBarProps {
  insights: CrimeCaseInsights | null;
  activeStatus: string;
  activePriority: string;
  onSelectStatus: (status: string) => void;
  onSelectPriority: (priority: string) => void;
  onResetFilters: () => void;
}

const EMPTY_METRICS = {
  open: 0,
  investigating: 0,
  chargeSheet: 0,
  closed: 0,
  critical: 0,
  high: 0,
  medium: 0,
  low: 0,
  avgProgress: 0,
  clearanceRate: 0,
};

export const CrimeInsightsBar: React.FC<CrimeInsightsBarProps> = ({
  insights,
  activeStatus,
  activePriority,
  onSelectStatus,
  onSelectPriority,
  onResetFilters,
}) => {
  const total = insights?.total_cases ?? 0;

  const metrics = insights
    ? {
        open: insights.open,
        investigating: insights.investigating,
        chargeSheet: insights.charge_sheet,
        closed: insights.closed,
        critical: insights.critical,
        high: insights.high,
        medium: insights.medium,
        low: insights.low,
        avgProgress: insights.avg_progress,
        clearanceRate: insights.clearance_rate,
      }
    : EMPTY_METRICS;

  if (total === 0) return null;

  return (
    <div className="bg-secondary-bg border border-border-color rounded-card p-4 space-y-4 font-mono select-none">
      {/* Top telemetry title bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-border-color/60 pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#1E6FD9] animate-pulse" />
          <span className="text-xs uppercase font-bold tracking-wider text-[var(--text-primary)]">
            Active Dataset Crime Record Insights
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-[#1E6FD9]/15 text-[#1E6FD9] border border-[#1E6FD9]/30 font-bold">
            {total} Cases Analyzed
          </span>
        </div>

        <div className="flex items-center gap-3 text-[10px] text-[var(--text-muted)]">
          <div className="flex items-center gap-1.5">
            <span className="text-[var(--text-secondary)] font-bold">Clearance:</span>
            <span className="text-[#0E9E78] font-bold">{metrics.clearanceRate}%</span>
          </div>
          <span>•</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[var(--text-secondary)] font-bold">Avg Velocity:</span>
            <span className="text-[#1E6FD9] font-bold">{metrics.avgProgress}%</span>
          </div>
          {(activeStatus || activePriority) && (
            <>
              <span>•</span>
              <button
                type="button"
                onClick={onResetFilters}
                className="text-[var(--accent-coral)] hover:underline cursor-pointer font-bold uppercase"
              >
                Clear Filters
              </button>
            </>
          )}
        </div>
      </div>

      {/* Visual Analytics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* Metric 1: Open / In-Take */}
        <button
          type="button"
          onClick={() => onSelectStatus(activeStatus === 'open' ? '' : 'open')}
          className={`p-3 rounded border text-left transition-all cursor-pointer flex flex-col justify-between ${
            activeStatus === 'open'
              ? 'bg-blue-500/15 border-blue-500 shadow-glow-blue/20 ring-1 ring-blue-500'
              : 'bg-[var(--bg-secondary)]/40 border-border-color hover:border-blue-500/50 hover:bg-blue-500/5'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-blue-400 flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5" /> Initial Intake
            </span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">
              {Math.round((metrics.open / total) * 100)}%
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-xl font-bold text-[var(--text-primary)]">{metrics.open}</span>
            <span className="text-[9px] text-[var(--text-muted)]">Open / Assigned</span>
          </div>
          <div className="w-full bg-black/20 h-1 rounded-full overflow-hidden mt-2">
            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(metrics.open / total) * 100}%` }} />
          </div>
        </button>

        {/* Metric 2: Under Active Investigation */}
        <button
          type="button"
          onClick={() => onSelectStatus(activeStatus === 'investigating' ? '' : 'investigating')}
          className={`p-3 rounded border text-left transition-all cursor-pointer flex flex-col justify-between ${
            activeStatus === 'investigating'
              ? 'bg-purple-500/15 border-purple-500 shadow-glow-blue/20 ring-1 ring-purple-500'
              : 'bg-[var(--bg-secondary)]/40 border-border-color hover:border-purple-500/50 hover:bg-purple-500/5'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-purple-400 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" /> In Investigation
            </span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold">
              {Math.round((metrics.investigating / total) * 100)}%
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-xl font-bold text-[var(--text-primary)]">{metrics.investigating}</span>
            <span className="text-[9px] text-[var(--text-muted)]">Field / Forensic</span>
          </div>
          <div className="w-full bg-black/20 h-1 rounded-full overflow-hidden mt-2">
            <div className="h-full bg-purple-500 rounded-full" style={{ width: `${(metrics.investigating / total) * 100}%` }} />
          </div>
        </button>

        {/* Metric 3: Critical Threat Priority */}
        <button
          type="button"
          onClick={() => onSelectPriority(activePriority === 'critical' ? '' : 'critical')}
          className={`p-3 rounded border text-left transition-all cursor-pointer flex flex-col justify-between ${
            activePriority === 'critical'
              ? 'bg-[#C94A2A]/15 border-[#C94A2A] shadow-glow-coral/20 ring-1 ring-[#C94A2A]'
              : 'bg-[var(--bg-secondary)]/40 border-border-color hover:border-[#C94A2A]/50 hover:bg-[#C94A2A]/5'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-[#C94A2A] flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" /> Critical Severity
            </span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-[#C94A2A]/20 text-[#C94A2A] font-bold">
              {metrics.critical} Cases
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-xl font-bold text-[var(--text-primary)]">{metrics.critical}</span>
            <span className="text-[9px] text-[var(--text-muted)]">Urgent Attention</span>
          </div>
          <div className="w-full bg-black/20 h-1 rounded-full overflow-hidden mt-2">
            <div className="h-full bg-[#C94A2A] rounded-full" style={{ width: `${(metrics.critical / total) * 100}%` }} />
          </div>
        </button>

        {/* Metric 4: Closed / Resolved */}
        <button
          type="button"
          onClick={() => onSelectStatus(activeStatus === 'closed' ? '' : 'closed')}
          className={`p-3 rounded border text-left transition-all cursor-pointer flex flex-col justify-between ${
            activeStatus === 'closed'
              ? 'bg-[#0E9E78]/15 border-[#0E9E78] shadow-glow-teal/20 ring-1 ring-[#0E9E78]'
              : 'bg-[var(--bg-secondary)]/40 border-border-color hover:border-[#0E9E78]/50 hover:bg-[#0E9E78]/5'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-[#0E9E78] flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> Solved / Closed
            </span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-[#0E9E78]/20 text-[#0E9E78] font-bold">
              {metrics.closed} Cases
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-xl font-bold text-[var(--text-primary)]">{metrics.closed}</span>
            <span className="text-[9px] text-[var(--text-muted)]">Charge Sheet / Done</span>
          </div>
          <div className="w-full bg-black/20 h-1 rounded-full overflow-hidden mt-2">
            <div className="h-full bg-[#0E9E78] rounded-full" style={{ width: `${(metrics.closed / total) * 100}%` }} />
          </div>
        </button>
      </div>

      {/* Severity & Threat Spectrum Distribution Bar */}
      <div className="p-3 bg-[var(--bg-secondary)]/30 rounded border border-border-color/50 space-y-2">
        <div className="flex items-center justify-between text-[10px] text-[var(--text-muted)]">
          <span className="font-bold text-[var(--text-secondary)] uppercase flex items-center gap-1">
            <BarChart2 className="w-3 h-3 text-[#1E6FD9]" />
            Threat Spectrum Breakdown
          </span>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[#C94A2A]" /> Critical ({metrics.critical})
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-orange-400" /> High ({metrics.high})
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-400" /> Medium ({metrics.medium})
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-slate-400" /> Low ({metrics.low})
            </span>
          </div>
        </div>

        {/* Multi-segment stacked bar */}
        <div className="w-full h-2 rounded-full bg-black/30 flex overflow-hidden">
          <div
            className="h-full bg-[#C94A2A] transition-all duration-300"
            style={{ width: `${(metrics.critical / total) * 100}%` }}
            title={`Critical: ${metrics.critical} (${Math.round((metrics.critical / total) * 100)}%)`}
          />
          <div
            className="h-full bg-orange-400 transition-all duration-300"
            style={{ width: `${(metrics.high / total) * 100}%` }}
            title={`High: ${metrics.high} (${Math.round((metrics.high / total) * 100)}%)`}
          />
          <div
            className="h-full bg-blue-400 transition-all duration-300"
            style={{ width: `${(metrics.medium / total) * 100}%` }}
            title={`Medium: ${metrics.medium} (${Math.round((metrics.medium / total) * 100)}%)`}
          />
          <div
            className="h-full bg-slate-500 transition-all duration-300"
            style={{ width: `${(metrics.low / total) * 100}%` }}
            title={`Low: ${metrics.low} (${Math.round((metrics.low / total) * 100)}%)`}
          />
        </div>
      </div>
    </div>
  );
};

export default CrimeInsightsBar;