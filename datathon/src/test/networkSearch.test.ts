import { describe, expect, it } from 'vitest';
import {
  parseCombinedSearch,
  splitSearchTokens,
  hasActiveNetworkFilters,
} from '../utils/networkSearch';

const KNOWN_CRIME_TYPES = ['Theft & Burglaries', 'Narcotics', 'Cyber Crime'];
const KNOWN_DISTRICTS = ['Bengaluru Urban', 'Mysuru', 'Belagavi'];

describe('splitSearchTokens', () => {
  it('splits on spaces, plus signs and commas', () => {
    expect(splitSearchTokens('Theft + Bengaluru,Bangalore')).toEqual([
      'Theft',
      'Bengaluru',
      'Bangalore',
    ]);
  });

  it('ignores empty and whitespace-only tokens', () => {
    expect(splitSearchTokens('  ')).toEqual([]);
    expect(splitSearchTokens('Ramu   Swamy')).toEqual(['Ramu', 'Swamy']);
  });
});

describe('parseCombinedSearch', () => {
  it('maps unknown terms to a criminal-name filter', () => {
    const result = parseCombinedSearch('Ramu Swamy', KNOWN_CRIME_TYPES, KNOWN_DISTRICTS);
    expect(result.criminalName).toBe('Ramu Swamy');
    expect(result.crimeTypes).toEqual([]);
    expect(result.districts).toEqual([]);
  });

  it('maps known crime type tokens onto the crime-type filter', () => {
    const result = parseCombinedSearch('Theft & Burglaries', KNOWN_CRIME_TYPES, KNOWN_DISTRICTS);
    expect(result.crimeTypes).toEqual(['Theft & Burglaries']);
    expect(result.criminalName).toBeUndefined();
  });

  it('combines crime type + district detection with a name term', () => {
    const result = parseCombinedSearch('Theft Bengaluru Ramu', KNOWN_CRIME_TYPES, KNOWN_DISTRICTS);
    expect(result.crimeTypes).toEqual(['Theft & Burglaries']);
    expect(result.districts).toEqual(['Bengaluru Urban']);
    expect(result.criminalName).toBe('Ramu');
  });

  it('captures a bare 4-digit year as a time window, not a suspect name', () => {
    const result = parseCombinedSearch('2025', KNOWN_CRIME_TYPES, KNOWN_DISTRICTS);
    expect(result.year).toBe('2025');
    expect(result.criminalName).toBeUndefined();
    expect(result.crimeTypes).toEqual([]);
    expect(result.districts).toEqual([]);
  });

  it('filters out a year token from a combined crime + district + year query', () => {
    const result = parseCombinedSearch('Theft Bengaluru 2025', KNOWN_CRIME_TYPES, KNOWN_DISTRICTS);
    expect(result.crimeTypes).toEqual(['Theft & Burglaries']);
    expect(result.districts).toEqual(['Bengaluru Urban']);
    expect(result.year).toBe('2025');
    expect(result.criminalName).toBeUndefined();
  });

  it('keeps a 4-digit token out of the criminal-name fallback', () => {
    const result = parseCombinedSearch('Vikram 2025', KNOWN_CRIME_TYPES, KNOWN_DISTRICTS);
    expect(result.criminalName).toBe('Vikram');
    expect(result.year).toBe('2025');
  });

  it('treats plus/comma separated tokens identically', () => {
    const a = parseCombinedSearch('Narcotics + Mysuru', KNOWN_CRIME_TYPES, KNOWN_DISTRICTS);
    const b = parseCombinedSearch('Narcotics, Mysuru', KNOWN_CRIME_TYPES, KNOWN_DISTRICTS);
    expect(a).toEqual(b);
  });

  it('returns undefined criminalName when only known terms are present', () => {
    const result = parseCombinedSearch('Bengaluru', KNOWN_CRIME_TYPES, KNOWN_DISTRICTS);
    expect(result.districts).toEqual(['Bengaluru Urban']);
    expect(result.criminalName).toBeUndefined();
  });
});

describe('hasActiveNetworkFilters', () => {
  it('is false for an empty filter object', () => {
    expect(hasActiveNetworkFilters({})).toBe(false);
  });

  it('is true when any filter dimension is populated', () => {
    expect(hasActiveNetworkFilters({ crimeTypes: ['Narcotics'] })).toBe(true);
    expect(hasActiveNetworkFilters({ districts: ['Mysuru'] })).toBe(true);
    expect(hasActiveNetworkFilters({ policeStations: ['KR Puram'] })).toBe(true);
    expect(hasActiveNetworkFilters({ firNumbers: ['FIR-1'] })).toBe(true);
    expect(hasActiveNetworkFilters({ victimName: 'Anita' })).toBe(true);
    expect(hasActiveNetworkFilters({ dateFrom: '2026-01-01' })).toBe(true);
    expect(hasActiveNetworkFilters({ dateTo: '2026-12-31' })).toBe(true);
    expect(hasActiveNetworkFilters({ criminalName: 'Ramu' })).toBe(true);
  });
});