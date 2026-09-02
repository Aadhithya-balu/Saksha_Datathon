import React, { useEffect, useMemo, useState } from 'react';
import {
  Search,
  Sliders,
  RotateCcw,
  X,
  MapPin,
  Tag,
  Building2,
  CalendarRange,
  AlertTriangle,
} from 'lucide-react';
import {
  getCrimeCategories,
  getLocationsList,
  type CrimeCategoryRecord,
  type LocationSimpleRecord,
  type NetworkFilterParams,
} from '../../services/api';
import { parseCombinedSearch } from '../../utils/networkSearch';

interface MultiSelectChipsProps {
  label: string;
  icon: React.ReactNode;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}

const MultiSelectChips: React.FC<MultiSelectChipsProps> = ({
  label,
  icon,
  options,
  selected,
  onChange,
}) => {
  const available = options.filter((o) => !selected.includes(o));
  return (
    <div className="flex flex-col gap-1 min-w-[170px] flex-1">
      <span className="text-[9.5px] uppercase font-bold text-[var(--text-muted)] flex items-center gap-1">
        {icon}
        {label}
      </span>
      <div className="flex flex-wrap items-center gap-1">
        {selected.map((value) => (
          <span
            key={value}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-btn bg-[var(--accent-purple)]/15 border border-[var(--accent-purple)]/30 text-[10px] text-[var(--text-primary)]"
          >
            {value}
            <button
              type="button"
              title={`Remove ${value}`}
              onClick={() => onChange(selected.filter((x) => x !== value))}
              className="text-[var(--text-muted)] hover:text-[var(--accent-coral)] cursor-pointer"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
        <select
          value=""
          onChange={(e) => {
            const v = e.target.value;
            if (v) onChange([...selected, v]);
          }}
          className="bg-[var(--bg-primary)] border border-[var(--border-secondary)] text-[var(--text-primary)] rounded-btn px-2 py-1 text-[10.5px] focus:outline-none focus:border-[var(--accent-blue)] max-w-[150px]"
        >
          <option value="">{selected.length ? `+ Add ${label}` : `All ${label}s`}</option>
          {available.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export interface NetworkFilterPanelProps {
  filters: NetworkFilterParams;
  onApply: (filters: NetworkFilterParams) => void;
  onClear: () => void;
  loading: boolean;
  resultCount: number | null;
  hasActiveFilters: boolean;
}

export const NetworkFilterPanel: React.FC<NetworkFilterPanelProps> = ({
  filters,
  onApply,
  onClear,
  loading,
  resultCount,
  hasActiveFilters,
}) => {
  const [crimeTypes, setCrimeTypes] = useState<string[]>([]);
  const [districts, setDistricts] = useState<string[]>([]);
  const [stations, setStations] = useState<string[]>([]);

  // Draft (unapplied) filter state — edited freely, committed via Apply Filters.
  const [search, setSearch] = useState<string>('');
  const [selectedCrimeTypes, setSelectedCrimeTypes] = useState<string[]>([]);
  const [selectedDistricts, setSelectedDistricts] = useState<string[]>([]);
  const [selectedStations, setSelectedStations] = useState<string[]>([]);
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [cats, locs] = await Promise.all([
          getCrimeCategories(),
          getLocationsList(),
        ]);
        if (!active) return;
        setCrimeTypes((cats as CrimeCategoryRecord[]).map((c) => c.name).filter(Boolean));
        const districtSet = new Set<string>();
        const stationSet = new Set<string>();
        for (const loc of locs as LocationSimpleRecord[]) {
          if (loc.district) districtSet.add(loc.district);
          if (loc.station) stationSet.add(loc.station);
        }
        setDistricts([...districtSet].sort());
        setStations([...stationSet].sort());
      } catch {
        // Options are cosmetic; a failed fetch just leaves the dropdowns empty.
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const parsedSearch = useMemo(
    () => parseCombinedSearch(search, crimeTypes, districts),
    [search, crimeTypes, districts]
  );

  const activeParts: string[] = [];
  if (filters.criminalName) activeParts.push(`Criminal: ${filters.criminalName}`);
  if (filters.crimeTypes?.length) activeParts.push(`Crime: ${filters.crimeTypes.join(' / ')}`);
  if (filters.districts?.length) activeParts.push(`District: ${filters.districts.join(' / ')}`);
  if (filters.policeStations?.length) activeParts.push(`Station: ${filters.policeStations.join(' / ')}`);
  if (filters.firNumbers?.length) activeParts.push(`Case: ${filters.firNumbers.join(' / ')}`);
  if (filters.victimName) activeParts.push(`Victim: ${filters.victimName}`);
  if (filters.dateFrom || filters.dateTo) {
    activeParts.push(`Date: ${filters.dateFrom || '…'} → ${filters.dateTo || '…'}`);
  }

  const handleApply = () => {
    setValidationError(null);
    // A year token from the combined search box (`Theft Bengaluru 2025`)
    // backfills the date window unless the user entered explicit dates.
    const resolvedDateFrom = dateFrom || (parsedSearch.year ? `${parsedSearch.year}-01-01` : undefined);
    const resolvedDateTo = dateTo || (parsedSearch.year ? `${parsedSearch.year}-12-31` : undefined);
    if (resolvedDateFrom && resolvedDateTo && resolvedDateFrom > resolvedDateTo) {
      setValidationError('Date From must be on or before Date To.');
      return;
    }
    const next: NetworkFilterParams = {
      criminalName: parsedSearch.criminalName,
      crimeTypes:
        parsedSearch.crimeTypes.length || selectedCrimeTypes.length
          ? Array.from(new Set([...parsedSearch.crimeTypes, ...selectedCrimeTypes]))
          : undefined,
      districts:
        parsedSearch.districts.length || selectedDistricts.length
          ? Array.from(new Set([...parsedSearch.districts, ...selectedDistricts]))
          : undefined,
      policeStations: selectedStations.length ? [...selectedStations] : undefined,
      dateFrom: resolvedDateFrom || undefined,
      dateTo: resolvedDateTo || undefined,
    };
    onApply(next);
  };

  const handleClear = () => {
    setValidationError(null);
    setSearch('');
    setSelectedCrimeTypes([]);
    setSelectedDistricts([]);
    setSelectedStations([]);
    setDateFrom('');
    setDateTo('');
    onClear();
  };

  return (
    <div className="flex flex-col gap-2.5 bg-[var(--bg-secondary)] p-3 rounded-card border border-[var(--border-secondary)] font-mono">
      {/* Combined keyword search */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[260px]">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[var(--text-muted)]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleApply();
            }}
            placeholder="Search criminal / suspect, or combine e.g. 'Theft Bengaluru 2025' ..."
            className="w-full bg-[var(--bg-primary)] border border-[var(--border-secondary)] rounded-btn pl-8 pr-3 py-1.5 text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-blue)]"
          />
        </div>
        {parsedSearch.crimeTypes.length > 0 || parsedSearch.districts.length > 0 || parsedSearch.year ? (
          <span className="text-[9.5px] text-[var(--accent-teal)] uppercase tracking-wider">
            Keywords detected: {parsedSearch.crimeTypes.join(' / ')}
            {parsedSearch.districts.length ? ` · ${parsedSearch.districts.join(' / ')}` : ''}
            {parsedSearch.year ? ` · ${parsedSearch.year}` : ''}
          </span>
        ) : null}

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleApply}
            disabled={loading}
            className="px-3.5 py-1.5 bg-[var(--accent-blue)]/20 hover:bg-[var(--accent-blue)]/40 border border-[var(--accent-blue)]/40 text-[var(--text-primary)] rounded-btn text-[11px] font-bold uppercase tracking-wider transition-colors cursor-pointer disabled:opacity-50"
          >
            {loading ? 'Loading…' : 'Apply Filters'}
          </button>
          <button
            type="button"
            onClick={handleClear}
            title="Clear all filters and restore the default network"
            className="px-3 py-1.5 bg-[var(--bg-tertiary)] hover:bg-[var(--accent-coral)]/15 border border-[var(--border-primary)] text-[var(--text-muted)] hover:text-[var(--text-primary)] rounded-btn text-[11px] font-bold uppercase tracking-wider transition-colors cursor-pointer flex items-center gap-1.5"
          >
            <RotateCcw className="w-3 h-3" />
            Clear Filters
          </button>
        </div>
      </div>

      {/* Structured filters */}
      <div className="flex flex-wrap items-end gap-x-4 gap-y-3 pt-2 border-t border-[var(--border-primary)]">
        <MultiSelectChips
          label="Crime Type"
          icon={<Tag className="w-3 h-3 text-[var(--accent-amber)]" />}
          options={crimeTypes}
          selected={selectedCrimeTypes}
          onChange={setSelectedCrimeTypes}
        />
        <MultiSelectChips
          label="District"
          icon={<MapPin className="w-3 h-3 text-[var(--accent-blue)]" />}
          options={districts}
          selected={selectedDistricts}
          onChange={setSelectedDistricts}
        />
        <MultiSelectChips
          label="Police Station"
          icon={<Building2 className="w-3 h-3 text-[var(--accent-teal)]" />}
          options={stations}
          selected={selectedStations}
          onChange={setSelectedStations}
        />
        <div className="flex items-center gap-2">
          <div className="flex flex-col gap-1">
            <span className="text-[9.5px] uppercase font-bold text-[var(--text-muted)] flex items-center gap-1">
              <CalendarRange className="w-3 h-3 text-[var(--accent-purple)]" />
              Date From
            </span>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="bg-[var(--bg-primary)] border border-[var(--border-secondary)] text-[var(--text-primary)] rounded-btn px-2 py-1 text-[10.5px] focus:outline-none focus:border-[var(--accent-blue)]"
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-[9.5px] uppercase font-bold text-[var(--text-muted)] flex items-center gap-1">
              <CalendarRange className="w-3 h-3 text-[var(--accent-purple)]" />
              Date To
            </span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="bg-[var(--bg-primary)] border border-[var(--border-secondary)] text-[var(--text-primary)] rounded-btn px-2 py-1 text-[10.5px] focus:outline-none focus:border-[var(--accent-blue)]"
            />
          </div>
        </div>
      </div>

      {/* Validation / result / active-filter feedback */}
      {validationError && (
        <div className="flex items-center gap-1.5 text-[10px] text-[var(--accent-coral)] uppercase tracking-wide">
          <AlertTriangle className="w-3 h-3" />
          {validationError}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 pt-1">
        {hasActiveFilters && (
          <>
            <span className="text-[9.5px] uppercase font-bold text-[var(--text-muted)] flex items-center gap-1">
              <Sliders className="w-3 h-3 text-[var(--accent-purple)]" />
              Active:
            </span>
            <div className="flex flex-wrap gap-1">
              {activeParts.map((part) => (
                <span
                  key={part}
                  className="px-2 py-0.5 rounded-btn bg-[var(--accent-blue)]/10 border border-[var(--accent-blue)]/30 text-[9.5px] text-[#60A5FA] uppercase tracking-wider"
                >
                  {part}
                </span>
              ))}
            </div>
          </>
        )}
        {!loading && resultCount !== null && (
          <span
            className={`ml-auto text-[10px] font-bold uppercase tracking-wider ${
              resultCount === 0 ? 'text-[var(--accent-coral)]' : 'text-[var(--text-muted)]'
            }`}
          >
            {resultCount === 0 ? 'No relationships found' : `${resultCount} network nodes`}
          </span>
        )}
      </div>
    </div>
  );
};

export default NetworkFilterPanel;