import React, { useState, useEffect } from 'react';
import { listCrimes, listOfficers, listCriminals, listVictims, type FIRDetailRecord, type CrimeCaseRecord, type OfficerRecord, type CriminalRecord, type VictimRecord } from '../../services/api';
import { Save, X, AlertTriangle } from 'lucide-react';

interface FIRFormProps {
  fir?: FIRDetailRecord | null;
  onSubmit: (data: any) => Promise<void>;
  onCancel: () => void;
}

export const FIRForm: React.FC<FIRFormProps> = ({ fir, onSubmit, onCancel }) => {
  const isEdit = !!fir;

  // Form Fields State
  const [firNumber, setFirNumber] = useState(fir?.fir_number || '');
  const [crimeCaseId, setCrimeCaseId] = useState(fir?.crime_case_id || '');
  const [officerId, setOfficerId] = useState(fir?.investigating_officer_id || '');
  const [complainantName, setComplainantName] = useState(fir?.complainant_name || '');
  const [complainantContact, setComplainantContact] = useState(fir?.complainant_contact || '');
  const [sections, setSections] = useState(fir?.sections || '');
  const [narrative, setNarrative] = useState(fir?.narrative || '');
  const [status, setStatus] = useState(fir?.status || 'registered');
  const [selectedCriminals, setSelectedCriminals] = useState<string[]>(fir?.criminals.map(c => c.id) || []);
  const [selectedVictims, setSelectedVictims] = useState<string[]>(fir?.victims.map(v => v.id) || []);

  // Dropdown Lists Data
  const [crimes, setCrimes] = useState<CrimeCaseRecord[]>([]);
  const [officers, setOfficers] = useState<OfficerRecord[]>([]);
  const [criminals, setCriminals] = useState<CriminalRecord[]>([]);
  const [victims, setVictims] = useState<VictimRecord[]>([]);
  
  // Loading & Errors State
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    let isMounted = true;
    
    const loadAllData = async () => {
      try {
        const [crimesRes, officersRes, criminalsRes, victimsRes] = await Promise.all([
          listCrimes(1, 100),
          listOfficers(1, 100),
          listCriminals(undefined, 1, 100),
          listVictims(undefined, 1, 100)
        ]);

        if (isMounted) {
          setCrimes(crimesRes.results || []);
          setOfficers(officersRes.results || []);
          setCriminals(criminalsRes.results || []);
          setVictims(victimsRes.results || []);
          
          // Default selection if creating
          if (!isEdit && crimesRes.results?.length > 0) {
            setCrimeCaseId(crimesRes.results[0].id);
          }
          setIsLoadingData(false);
        }
      } catch (err) {
        if (isMounted) {
          setError('Failed to fetch dropdown datasets. Verify database state.');
          setIsLoadingData(false);
        }
      }
    };

    void loadAllData();
    return () => { isMounted = false; };
  }, [isEdit]);

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (!isEdit) {
      if (!firNumber.trim()) {
        errors.fir_number = 'FIR number is required';
      } else if (!/^FIR-\d{3,4}\/[A-Z0-9]{2,10}\/\d{4}$/i.test(firNumber.trim())) {
        errors.fir_number = "Must match 'FIR-[3-4 digits]/[STATION]/[YEAR]' (e.g. FIR-045/BNG/2026)";
      }
    }

    if (!complainantName.trim()) {
      errors.complainant_name = 'Complainant name is required';
    } else if (complainantName.trim().length < 3) {
      errors.complainant_name = 'Name must be at least 3 characters long';
    }

    if (complainantContact.trim()) {
      const contactClean = complainantContact.replace(/[\s-]/g, '');
      if (!/^(?:\+91)?\d{10}$/.test(contactClean)) {
        errors.complainant_contact = 'Must be a valid 10-digit Indian phone number';
      }
    }

    if (!crimeCaseId) {
      errors.crime_case_id = 'A crime case linkage is required';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setError(null);

    const payload: any = {
      investigating_officer_id: officerId || null,
      complainant_name: complainantName.trim(),
      complainant_contact: complainantContact.trim() || null,
      sections: sections.trim() || null,
      narrative: narrative.trim() || null,
      status,
      criminal_ids: selectedCriminals,
      victim_ids: selectedVictims,
    };

    if (!isEdit) {
      payload.fir_number = firNumber.trim().toUpperCase();
      payload.crime_case_id = crimeCaseId;
    }

    try {
      await onSubmit(payload);
    } catch (err: any) {
      setError(err instanceof Error ? err.message : 'An error occurred during submission.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleCriminal = (id: string) => {
    setSelectedCriminals(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const toggleVictim = (id: string) => {
    setSelectedVictims(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  if (isLoadingData) {
    return (
      <div className="p-10 flex flex-col items-center justify-center space-y-4">
        <div className="w-8 h-8 rounded-full border-2 border-[var(--accent-blue)] border-t-transparent animate-spin" />
        <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase">Syncing Registry Metadata...</span>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 text-xs font-mono text-[var(--text-secondary)] p-4 bg-[var(--bg-tertiary)]/20 border border-border-color rounded-card">
      <div className="flex justify-between items-center border-b border-[var(--border-primary)] pb-3">
        <h3 className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">
          {isEdit ? `Edit FIR: ${fir?.fir_number}` : 'Register New FIR'}
        </h3>
        <button
          type="button"
          onClick={onCancel}
          className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-950/20 border border-red-900/30 rounded text-red-400 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* FIR Number */}
        <div>
          <label className="block text-[10px] text-[var(--text-muted)] uppercase font-semibold mb-1">FIR Number *</label>
          <input
            type="text"
            disabled={isEdit}
            placeholder="e.g., FIR-045/BNG/2026"
            value={firNumber}
            onChange={e => setFirNumber(e.target.value)}
            className={`w-full px-3 py-2 bg-[var(--bg-secondary)]/70 border rounded text-[var(--text-primary)] outline-none focus:border-[var(--accent-blue)] uppercase ${
              isEdit ? 'opacity-50 cursor-not-allowed border-[var(--border-primary)]' : 'border-border-color'
            }`}
          />
          {validationErrors.fir_number && (
            <span className="text-[9px] text-red-400 block mt-1">{validationErrors.fir_number}</span>
          )}
        </div>

        {/* Crime Case Link */}
        <div>
          <label className="block text-[10px] text-[var(--text-muted)] uppercase font-semibold mb-1">Linked Crime Case *</label>
          <select
            disabled={isEdit}
            value={crimeCaseId}
            onChange={e => setCrimeCaseId(e.target.value)}
            className={`w-full px-3 py-2 bg-[var(--bg-secondary)] border rounded text-[var(--text-primary)] outline-none focus:border-[var(--accent-blue)] ${
              isEdit ? 'opacity-50 cursor-not-allowed border-[var(--border-primary)]' : 'border-border-color'
            }`}
          >
            <option value="">Select Crime Case</option>
            {crimes.map(c => (
              <option key={c.id} value={c.id}>
                {c.case_number} - {c.description?.slice(0, 30)}...
              </option>
            ))}
          </select>
          {validationErrors.crime_case_id && (
            <span className="text-[9px] text-red-400 block mt-1">{validationErrors.crime_case_id}</span>
          )}
        </div>

        {/* Complainant Name */}
        <div>
          <label className="block text-[10px] text-[var(--text-muted)] uppercase font-semibold mb-1">Complainant Name *</label>
          <input
            type="text"
            placeholder="Full Name"
            value={complainantName}
            onChange={e => setComplainantName(e.target.value)}
            className="w-full px-3 py-2 bg-[var(--bg-secondary)]/70 border border-border-color rounded text-[var(--text-primary)] outline-none focus:border-[var(--accent-blue)]"
          />
          {validationErrors.complainant_name && (
            <span className="text-[9px] text-red-400 block mt-1">{validationErrors.complainant_name}</span>
          )}
        </div>

        {/* Complainant Contact */}
        <div>
          <label className="block text-[10px] text-[var(--text-muted)] uppercase font-semibold mb-1">Complainant Contact</label>
          <input
            type="text"
            placeholder="e.g., +919880000001"
            value={complainantContact}
            onChange={e => setComplainantContact(e.target.value)}
            className="w-full px-3 py-2 bg-[var(--bg-secondary)]/70 border border-border-color rounded text-[var(--text-primary)] outline-none focus:border-[var(--accent-blue)]"
          />
          {validationErrors.complainant_contact && (
            <span className="text-[9px] text-red-400 block mt-1">{validationErrors.complainant_contact}</span>
          )}
        </div>

        {/* Investigating Officer */}
        <div>
          <label className="block text-[10px] text-[var(--text-muted)] uppercase font-semibold mb-1">Investigating Officer</label>
          <select
            value={officerId}
            onChange={e => setOfficerId(e.target.value)}
            className="w-full px-3 py-2 bg-[var(--bg-secondary)] border border-border-color rounded text-[var(--text-primary)] outline-none focus:border-[var(--accent-blue)]"
          >
            <option value="">Unassigned (Assign Officer)</option>
            {officers.map(o => (
              <option key={o.id} value={o.id}>
                {o.badge_number} - {o.rank || 'Officer'}
              </option>
            ))}
          </select>
        </div>

        {/* Status */}
        <div>
          <label className="block text-[10px] text-[var(--text-muted)] uppercase font-semibold mb-1">FIR Status</label>
          <select
            value={status}
            onChange={e => setStatus(e.target.value as typeof status)}
            className="w-full px-3 py-2 bg-[var(--bg-secondary)] border border-border-color rounded text-[var(--text-primary)] outline-none focus:border-[var(--accent-blue)]"
          >
            <option value="registered">Registered</option>
            <option value="in_progress">In Investigation</option>
            <option value="closed">Closed / Filed in Court</option>
          </select>
        </div>

        {/* Sections */}
        <div className="md:col-span-2">
          <label className="block text-[10px] text-[var(--text-muted)] uppercase font-semibold mb-1">IPC / BNS Penal Sections</label>
          <input
            type="text"
            placeholder="e.g., IPC 379, IPC 457 (comma separated)"
            value={sections}
            onChange={e => setSections(e.target.value)}
            className="w-full px-3 py-2 bg-[var(--bg-secondary)]/70 border border-border-color rounded text-[var(--text-primary)] outline-none focus:border-[var(--accent-blue)]"
          />
        </div>

        {/* Narrative / Description */}
        <div className="md:col-span-2">
          <label className="block text-[10px] text-[var(--text-muted)] uppercase font-semibold mb-1">Incident Narrative Statement</label>
          <textarea
            rows={4}
            placeholder="State details of the crime description, evidence logs, witness accounts..."
            value={narrative}
            onChange={e => setNarrative(e.target.value)}
            className="w-full px-3 py-2 bg-[var(--bg-secondary)]/70 border border-border-color rounded text-[var(--text-primary)] outline-none focus:border-[var(--accent-blue)] resize-none"
          />
        </div>

        {/* Criminal Linkage Checklist */}
        <div className="p-3 bg-[var(--bg-secondary)]/40 border border-[var(--border-primary)] rounded-lg">
          <span className="block text-[10px] text-[var(--text-muted)] uppercase font-bold mb-2">Accused / Suspects Linked</span>
          <div className="max-h-[120px] overflow-y-auto space-y-1.5 custom-scrollbar pr-1">
            {criminals.length > 0 ? criminals.map(c => (
              <label key={c.id} className="flex items-center gap-2.5 p-1 px-2 hover:bg-[var(--bg-tertiary)]/10 rounded cursor-pointer transition-colors text-[10px]">
                <input
                  type="checkbox"
                  checked={selectedCriminals.includes(c.id)}
                  onChange={() => toggleCriminal(c.id)}
                  className="rounded text-[var(--accent-blue)] border-[var(--border-primary)] bg-[var(--bg-secondary)] outline-none"
                />
                <span className="truncate text-[var(--text-primary)]">{c.aliases ? `${c.full_name} (${c.aliases})` : c.full_name}</span>
              </label>
            )) : (
              <div className="text-[9px] text-[var(--text-muted)] py-4 text-center">No Suspects Found</div>
            )}
          </div>
        </div>

        {/* Victim Linkage Checklist */}
        <div className="p-3 bg-[var(--bg-secondary)]/40 border border-[var(--border-primary)] rounded-lg">
          <span className="block text-[10px] text-[var(--text-muted)] uppercase font-bold mb-2">Victims Linked</span>
          <div className="max-h-[120px] overflow-y-auto space-y-1.5 custom-scrollbar pr-1">
            {victims.length > 0 ? victims.map(v => (
              <label key={v.id} className="flex items-center gap-2.5 p-1 px-2 hover:bg-[var(--bg-tertiary)]/10 rounded cursor-pointer transition-colors text-[10px]">
                <input
                  type="checkbox"
                  checked={selectedVictims.includes(v.id)}
                  onChange={() => toggleVictim(v.id)}
                  className="rounded text-[var(--accent-blue)] border-[var(--border-primary)] bg-[var(--bg-secondary)] outline-none"
                />
                <span className="truncate text-[var(--text-primary)]">{v.full_name}</span>
              </label>
            )) : (
              <div className="text-[9px] text-[var(--text-muted)] py-4 text-center">No Victims Found</div>
            )}
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-3 border-t border-[var(--border-primary)] pt-4 mt-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-4 py-2 bg-[var(--bg-tertiary)] hover:bg-[var(--bg-elevated)] border border-border-color hover:border-[var(--text-muted)]/30 text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-btn transition-colors cursor-pointer select-none"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/80 text-[var(--text-primary)] rounded-btn flex items-center gap-2 font-bold cursor-pointer select-none transition-all shadow-glow-blue"
        >
          {isSubmitting ? (
            <div className="w-3.5 h-3.5 rounded-full border border-white border-t-transparent animate-spin" />
          ) : (
            <Save className="w-3.5 h-3.5" />
          )}
          {isEdit ? 'Save Changes' : 'Submit FIR Record'}
        </button>
      </div>
    </form>
  );
};
