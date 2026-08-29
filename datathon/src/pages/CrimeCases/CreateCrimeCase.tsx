import React, { useEffect, useState } from 'react';
import { createCrimeCase, createCriminal, createFIR, listCriminals, getCrimeCategories, getLocationsList } from '../../services/api';
import type { CrimeCategoryRecord, LocationSimpleRecord } from '../../services/api';
import { ArrowLeft, Save, AlertTriangle } from 'lucide-react';

interface CreateCrimeCaseProps {
  onCancel: () => void;
  onSuccess: () => void;
}

const CreateCrimeCase: React.FC<CreateCrimeCaseProps> = ({
  onCancel,
  onSuccess
}) => {
  const [categories, setCategories] = useState<CrimeCategoryRecord[]>([]);
  const [locations, setLocations] = useState<LocationSimpleRecord[]>([]);

  // Form Fields
  const [caseNumber, setCaseNumber] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [locationId, setLocationId] = useState('');
  const [occurredAt, setOccurredAt] = useState('');
  const [description, setDescription] = useState('');
  const [moTags, setMoTags] = useState('');
  const [status, setStatus] = useState('open');

  // Optional accused / criminal linkage fields
  const [accusedNames, setAccusedNames] = useState('');
  const [complainantName, setComplainantName] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Generate placeholder case number
    const randomNum = Math.floor(1000 + Math.random() * 9000);
    const year = new Date().getFullYear();
    setCaseNumber(`CR-${year}-BLR-${randomNum}`);

    // Load category and location lists
    Promise.all([getCrimeCategories(), getLocationsList()])
      .then(([cats, locs]) => {
        setCategories(cats);
        setLocations(locs);
        if (cats.length > 0) setCategoryId(cats[0].id);
        if (locs.length > 0) setLocationId(locs[0].id);
      })
      .catch((err) => {
        console.error('Error loading dropdown data:', err);
        setError('Failed to fetch categories or locations from backend.');
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseNumber.trim() || !categoryId || !locationId || !occurredAt) {
      setError('PLEASE SPECIFY ALL MANDATORY CLASSIFICATION FIELDS.');
      return;
    }

    const names = accusedNames
      .split(/[\n,;]/)
      .map(n => n.trim())
      .filter(Boolean);

    if (names.length > 0 && complainantName.trim().length < 3) {
      setError('PLEASE PROVIDE A COMPLAINANT NAME (3+ CHARS) TO LINK THE ACCUSED VIA FIR.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload = {
        case_number: caseNumber,
        category_id: categoryId,
        location_id: locationId,
        occurred_at: occurredAt,
        description: description || null,
        mo_tags: moTags || null,
        status: status
      };

      const created = await createCrimeCase(payload as any);

      // Optional: link accused criminals through an auto-created FIR
      if (names.length > 0 && created?.id) {
        const criminalIds: string[] = [];
        for (const name of names) {
          const search = await listCriminals(name, 1, 5).catch(() => null);
          let existing = search?.results?.find(
            c => c.full_name.toLowerCase() === name.toLowerCase()
          );
          if (!existing) {
            existing = await createCriminal({ full_name: name, status: 'at_large' });
          }
          if (existing?.id) criminalIds.push(existing.id);
        }

        const year = new Date().getFullYear();
        const station = locationId ? (locations.find(l => l.id === locationId)?.station || 'PS') : 'PS';
        const firNumber = `FIR-${Math.floor(100 + Math.random() * 900)}/${station.replace(/[^A-Z0-9]/gi, '').slice(0, 10).toUpperCase()}/${year}`;

        await createFIR({
          fir_number: firNumber,
          crime_case_id: created.id,
          complainant_name: complainantName.trim(),
          sections: moTags || null,
          narrative: description || null,
          status: 'registered',
          criminal_ids: criminalIds,
        });
      }

      onSuccess();
    } catch (err: any) {
      setError(err?.message || 'Failed to create crime case record.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Page Header */}
      <div className="flex justify-between items-center pb-4 border-b border-border-color">
        <button
          onClick={onCancel}
          className="flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer text-xs uppercase font-bold"
        >
          <ArrowLeft className="w-4 h-4" /> Cancel Enrolment
        </button>
        <h2 className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">Crime Case Registry Enrolment</h2>
      </div>

      {error && (
        <div className="p-4 border border-[#C94A2A]/20 bg-[#C94A2A]/5 text-[#C94A2A] rounded text-xs flex items-center gap-3 font-mono">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main input form */}
      <form onSubmit={handleSubmit} className="p-6 bg-secondary-bg border border-border-color rounded-card space-y-5 font-mono text-xs text-[var(--text-secondary)]">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {/* Case Number */}
          <div className="flex flex-col gap-1.5">
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Case Number *</label>
            <input
              type="text"
              required
              placeholder="e.g. CR-2026-BLR-8321"
              value={caseNumber}
              onChange={(e) => setCaseNumber(e.target.value)}
              className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] uppercase placeholder-[var(--text-muted)] focus:border-[#1E6FD9]/60 focus:outline-none"
            />
          </div>

          {/* Occurred At */}
          <div className="flex flex-col gap-1.5">
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Date *</label>
            <input
              type="datetime-local"
              required
              value={occurredAt}
              onChange={(e) => setOccurredAt(e.target.value)}
              className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] uppercase focus:border-[#1E6FD9]/60 focus:outline-none"
            />
          </div>

          {/* Crime Category */}
          <div className="flex flex-col gap-1.5">
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Category *</label>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] cursor-pointer focus:border-[#1E6FD9]/60 focus:outline-none"
            >
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.section_code ? `(${c.section_code})` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Incident Location */}
          <div className="flex flex-col gap-1.5">
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Location *</label>
            <select
              value={locationId}
              onChange={(e) => setLocationId(e.target.value)}
              className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] cursor-pointer focus:border-[#1E6FD9]/60 focus:outline-none"
            >
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.district} - {loc.station} {loc.pincode ? `(${loc.pincode})` : ''}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* MO Tags */}
        <div className="flex flex-col gap-1.5">
          <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Crime Type / MO Tags</label>
          <input
            type="text"
            placeholder="e.g. night-trespass, safe-cracking, lock-break"
            value={moTags}
            onChange={(e) => setMoTags(e.target.value)}
            className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[#1E6FD9]/60 focus:outline-none"
          />
        </div>

        {/* Case Status */}
        <div className="flex flex-col gap-1.5">
          <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Initial Process Status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] cursor-pointer focus:border-[#1E6FD9]/60 focus:outline-none"
          >
            <option value="open">OPEN</option>
            <option value="assigned">ASSIGNED</option>
            <option value="investigating">INVESTIGATING</option>
          </select>
        </div>

        {/* Description Statement */}
        <div className="flex flex-col gap-1.5">
          <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Description</label>
          <textarea
            placeholder="ENTER COMPREHENSIVE DESCRIPTION DETAILS RELEVANT TO THIS ACTIVE INTELLIGENCE FILE..."
            rows={5}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full p-3.5 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[#1E6FD9]/60 focus:outline-none resize-none uppercase"
          />
        </div>

        {/* Optional Accused / Criminal Names */}
        <div className="border border-border-color/40 rounded p-4 space-y-4">
          <div className="flex items-center justify-between">
            <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Accused / Criminal Name(s) (Optional)</label>
            {accusedNames.trim() && (
              <span className="text-[10px] text-[var(--accent-teal)] uppercase font-bold">Will auto-create linked FIR</span>
            )}
          </div>
          <textarea
            placeholder="e.g. Ramu Swamy, Vikram Yadav (one per line, comma or semicolon separated). Leave blank if no accused is known yet."
            rows={3}
            value={accusedNames}
            onChange={(e) => setAccusedNames(e.target.value)}
            className="w-full p-3.5 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[#1E6FD9]/60 focus:outline-none resize-none"
          />
          {accusedNames.trim().length > 0 && (
            <div className="flex flex-col gap-1.5">
              <label className="uppercase text-[10px] text-[var(--text-muted)] font-bold">Complainant Name (required to register FIR) *</label>
              <input
                type="text"
                placeholder="e.g. Anil Kumar"
                value={complainantName}
                onChange={(e) => setComplainantName(e.target.value)}
                className="px-3.5 py-2 bg-[var(--bg-tertiary)] border border-border-color rounded text-xs text-[var(--text-primary)] focus:border-[#1E6FD9]/60 focus:outline-none"
              />
            </div>
          )}
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
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2 bg-[#1E6FD9] hover:bg-[#1E6FD9]/80 disabled:opacity-50 transition-colors rounded uppercase font-bold text-[var(--text-primary)] cursor-pointer animate-pulse-slow"
          >
            <Save className="w-4 h-4" /> Create Case
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreateCrimeCase;
