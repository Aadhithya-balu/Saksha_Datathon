import React, { useEffect, useState } from 'react';
import { getCrimeCase, updateCrimeCase, getUnassignedOfficers } from '../../services/api';
import type { OfficerWithUserRecord } from '../../services/api';
import { ArrowLeft, Save, AlertTriangle, Lock } from 'lucide-react';

interface EditCrimeCaseProps {
  caseId: string;
  onCancel: () => void;
  onSuccess: () => void;
}

// Canonical status values and their display labels
const STATUS_LABELS: Record<string, string> = {
  active: 'ACTIVE',
  under_investigation: 'UNDER INVESTIGATION',
  arrested: 'ARRESTED',
  chargesheeted: 'CHARGESHEETED',
  convicted: 'CONVICTED',
  closed: 'CLOSED',
  // legacy — shown read-only if returned from older records
  open: 'OPEN (ACTIVE)',
  assigned: 'ASSIGNED (ACTIVE)',
  investigating: 'INVESTIGATING',
  'evidence collected': 'EVIDENCE COLLECTED',
  'charge sheet filed': 'CHARGE SHEET FILED',
};

// Allowed forward transitions per canonical status (mirrors backend)
const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  active: ['under_investigation', 'arrested', 'closed'],
  under_investigation: ['arrested', 'chargesheeted', 'closed'],
  arrested: ['chargesheeted'],
  chargesheeted: ['convicted', 'closed'],
  convicted: ['closed'],
  closed: [],
  // legacy aliases map to same rules as their canonical equivalents
  open: ['under_investigation', 'arrested', 'closed'],
  assigned: ['under_investigation', 'arrested', 'closed'],
  investigating: ['arrested', 'chargesheeted', 'closed'],
  'evidence collected': ['arrested', 'chargesheeted', 'closed'],
  'charge sheet filed': ['convicted', 'closed'],
};

const IMMUTABLE_STATUSES = new Set(['arrested', 'convicted']);

const EditCrimeCase: React.FC<EditCrimeCaseProps> = ({ caseId, onCancel, onSuccess }) => {
  const [officers, setOfficers] = useState<OfficerWithUserRecord[]>([]);

  const [caseNumber, setCaseNumber] = useState('');
  const [description, setDescription] = useState('');
  const [moTags, setMoTags] = useState('');
  const [currentStatus, setCurrentStatus] = useState('active');
  const [status, setStatus] = useState('active');
  const [priority, setPriority] = useState('medium');
  const [progress, setProgress] = useState(10);
  const [assignedOfficerId, setAssignedOfficerId] = useState('');
  const [isLocked, setIsLocked] = useState(false);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [c, offList] = await Promise.all([getCrimeCase(caseId), getUnassignedOfficers()]);
        setOfficers(offList);
        setCaseNumber(c.case_number);
        setDescription(c.description || '');
        setMoTags(c.mo_tags || '');
        setCurrentStatus(c.status);
        setStatus(c.status);
        setPriority(c.priority);
        setProgress(c.progress);
        setAssignedOfficerId(c.assigned_officer_id || '');
        setIsLocked(c.is_locked ?? IMMUTABLE_STATUSES.has(c.status?.toLowerCase()));
      } catch (err: any) {
        setError(err?.message || 'Failed to load crime case data.');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [caseId]);

  const allowedNextStatuses: string[] = ALLOWED_TRANSITIONS[currentStatus?.toLowerCase()] ?? [];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload: Record<string, any> = {
        description: description || null,
        mo_tags: moTags || null,
        priority,
        progress,
        assigned_officer_id: assignedOfficerId || null,
      };

      // Only include status if it actually changed
      if (status !== currentStatus) {
        payload.status = status;
      }

      await updateCrimeCase(caseId, payload as any);
      onSuccess();
    } catch (err: any) {
      // Surface backend transition rejection clearly
      const detail = err?.response?.data?.detail || err?.response?.data?.error?.message || err?.message;
      setError(detail || 'Failed to save changes.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[40vh] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-[#1E6FD9] border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto font-mono text-xs">
      {/* Page Header */}
      <div className="flex justify-between items-center pb-4 border-b border-border-color">
        <button
          onClick={onCancel}
          className="flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer text-xs uppercase font-bold"
        >
          <ArrowLeft className="w-4 h-4" /> Cancel Modifications
        </button>
        <h2 className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">
          Modify Case Record [{caseNumber}]
        </h2>
      </div>

      {/* Locked status banner */}
      {isLocked && (
        <div className="p-4 border border-amber-500/40 bg-amber-500/10 text-amber-400 rounded text-xs flex items-center gap-3">
          <Lock className="w-4 h-4 shrink-0" />
          <span>
            This case has status <strong>{STATUS_LABELS[currentStatus] ?? currentStatus.toUpperCase()}</strong> which is{' '}
            <strong>locked</strong>. No fields may be modified. Only the next permitted status transition is
            available: <strong>{allowedNextStatuses.map(s => STATUS_LABELS[s] ?? s.toUpperCase()).join(', ') || 'None (terminal)'}</strong>.
          </span>
        </div>
      )}

      {error && (
        <div className="p-4 border border-[#C94A2A]/20 bg-[#C94A2A]/5 text-[#C94A2A] rounded text-xs flex items-center gap-3">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Form */}
      <form onSubmit={handleSubmit} className="p-6 bg-secondary-bg border border-border-color rounded-card space-y-5 text-[var(--text-secondary)]">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {/* Status Select */}
          <div className="flex flex-col gap-1.5">
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold flex items-center gap-1.5">
              Clearance Workflow Status
              {isLocked && <Lock className="w-3 h-3 text-amber-400" />}
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              disabled={isLocked && allowedNextStatuses.length === 0}
              className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] cursor-pointer focus:border-[#1E6FD9]/60 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {/* Always show current status */}
              <option value={currentStatus}>
                {STATUS_LABELS[currentStatus] ?? currentStatus.toUpperCase()} (current)
              </option>
              {/* Only show valid forward transitions */}
              {allowedNextStatuses
                .filter((s) => s !== currentStatus)
                .map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABELS[s] ?? s.toUpperCase()}
                  </option>
                ))}
            </select>
            {isLocked && (
              <span className="text-[9.5px] text-amber-400 font-mono">
                Status is locked. Only permitted forward transitions are shown.
              </span>
            )}
          </div>

          {/* Priority Select */}
          <div className="flex flex-col gap-1.5">
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Threat Priority Level</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              disabled={isLocked}
              className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] cursor-pointer focus:border-[#1E6FD9]/60 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="low">LOW</option>
              <option value="medium">MEDIUM</option>
              <option value="high">HIGH</option>
              <option value="critical">CRITICAL</option>
            </select>
          </div>

          {/* Progress Percent */}
          <div className="flex flex-col gap-1.5">
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">
              Progress Percentage ({progress}%)
            </label>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={progress}
              onChange={(e) => setProgress(Number(e.target.value))}
              disabled={isLocked}
              className="w-full h-1 bg-[var(--bg-tertiary)] rounded-lg appearance-none cursor-pointer border border-[#1E6FD9]/20 disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Assigned Officer */}
          <div className="flex flex-col gap-1.5">
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Assigned Investigating Officer</label>
            <select
              value={assignedOfficerId}
              onChange={(e) => setAssignedOfficerId(e.target.value)}
              disabled={isLocked}
              className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] cursor-pointer focus:border-[#1E6FD9]/60 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">[UNASSIGNED]</option>
              {officers.map((off) => (
                <option key={off.id} value={off.id}>
                  {off.full_name} ({off.badge_number})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* MO Tags */}
        <div className="flex flex-col gap-1.5">
          <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Modus Operandi Tags (Comma-Separated)</label>
          <input
            type="text"
            placeholder="e.g. night-trespass, safe-cracking, lock-break"
            value={moTags}
            onChange={(e) => setMoTags(e.target.value)}
            disabled={isLocked}
            className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[#1E6FD9]/60 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {/* Narrative Description */}
        <div className="flex flex-col gap-1.5">
          <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Narrative Description Brief</label>
          <textarea
            rows={5}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isLocked}
            className="w-full p-3.5 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[#1E6FD9]/60 focus:outline-none resize-none uppercase disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {/* Submit Actions */}
        <div className="flex justify-end gap-3 pt-3 border-t border-border-color/30">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 border border-border-color hover:bg-[var(--bg-tertiary)]/10 rounded uppercase font-bold cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving || (isLocked && status === currentStatus)}
            className="flex items-center gap-2 px-5 py-2 bg-[#1E6FD9] hover:bg-[#1E6FD9]/80 disabled:opacity-50 transition-colors rounded uppercase font-bold text-[var(--text-primary)] cursor-pointer"
          >
            <Save className="w-4 h-4" />
            {isLocked ? 'Advance Status' : 'Save Modifications'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default EditCrimeCase;
