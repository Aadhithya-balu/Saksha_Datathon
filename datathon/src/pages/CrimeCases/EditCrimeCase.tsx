import React, { useEffect, useState } from 'react';
import { getCrimeCase, updateCrimeCase, getUnassignedOfficers } from '../../services/api';
import type { OfficerWithUserRecord, CrimeCaseDetailRecord } from '../../services/api';
import { ArrowLeft, Save, AlertTriangle } from 'lucide-react';

interface EditCrimeCaseProps {
  caseId: string;
  onCancel: () => void;
  onSuccess: () => void;
}

const EditCrimeCase: React.FC<EditCrimeCaseProps> = ({
  caseId,
  onCancel,
  onSuccess
}) => {
  const [officers, setOfficers] = useState<OfficerWithUserRecord[]>([]);

  // Form Fields
  const [caseNumber, setCaseNumber] = useState('');
  const [description, setDescription] = useState('');
  const [moTags, setMoTags] = useState('');
  const [status, setStatus] = useState('open');
  const [priority, setPriority] = useState('medium');
  const [progress, setProgress] = useState(10);
  const [assignedOfficerId, setAssignedOfficerId] = useState('');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [c, offList] = await Promise.all([
          getCrimeCase(caseId),
          getUnassignedOfficers()
        ]);
        setOfficers(offList);
        setCaseNumber(c.case_number);
        setDescription(c.description || '');
        setMoTags(c.mo_tags || '');
        setStatus(c.status);
        setPriority(c.priority);
        setProgress(c.progress);
        setAssignedOfficerId(c.assigned_officer_id || '');
      } catch (err: any) {
        setError(err?.message || 'Failed to load crime case data.');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [caseId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        description: description || null,
        mo_tags: moTags || null,
        status: status,
        priority: priority,
        progress: progress,
        assigned_officer_id: assignedOfficerId || null
      };

      await updateCrimeCase(caseId, payload as any);
      onSuccess();
    } catch (err: any) {
      setError(err?.message || 'Failed to save changes.');
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
        <h2 className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">Modify Case Record [{caseNumber}]</h2>
      </div>

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
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Clearance Workflow Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] cursor-pointer focus:border-[#1E6FD9]/60 focus:outline-none"
            >
              <option value="open">OPEN</option>
              <option value="assigned">ASSIGNED</option>
              <option value="investigating">INVESTIGATING</option>
              <option value="evidence collected">EVIDENCE COLLECTED</option>
              <option value="charge sheet filed">CHARGE SHEET FILED</option>
              <option value="closed">CLOSED</option>
            </select>
          </div>

          {/* Priority Select */}
          <div className="flex flex-col gap-1.5">
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Threat Priority Level</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] cursor-pointer focus:border-[#1E6FD9]/60 focus:outline-none"
            >
              <option value="low">LOW</option>
              <option value="medium">MEDIUM</option>
              <option value="high">HIGH</option>
              <option value="critical">CRITICAL</option>
            </select>
          </div>

          {/* Progress Percent */}
          <div className="flex flex-col gap-1.5">
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Progress Percentage ({progress}%)</label>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={progress}
              onChange={(e) => setProgress(Number(e.target.value))}
              className="w-full h-1 bg-[var(--bg-tertiary)] rounded-lg appearance-none cursor-pointer border border-[#1E6FD9]/20"
            />
          </div>

          {/* Assigned Officer */}
          <div className="flex flex-col gap-1.5">
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Assigned Investigating Officer</label>
            <select
              value={assignedOfficerId}
              onChange={(e) => setAssignedOfficerId(e.target.value)}
              className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] cursor-pointer focus:border-[#1E6FD9]/60 focus:outline-none"
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
            className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[#1E6FD9]/60 focus:outline-none"
          />
        </div>

        {/* Narrative Description */}
        <div className="flex flex-col gap-1.5">
          <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Narrative Description Brief</label>
          <textarea
            rows={5}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full p-3.5 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[#1E6FD9]/60 focus:outline-none resize-none uppercase"
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
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2 bg-[#1E6FD9] hover:bg-[#1E6FD9]/80 disabled:opacity-50 transition-colors rounded uppercase font-bold text-[var(--text-primary)] cursor-pointer"
          >
            <Save className="w-4 h-4" /> Save Modifications
          </button>
        </div>
      </form>
    </div>
  );
};

export default EditCrimeCase;
