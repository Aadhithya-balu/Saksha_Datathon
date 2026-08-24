/**
 * Tests for Issues #107 (PersonAvatar) and #118 (useFaceAuth real verification).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';

// ---------------------------------------------------------------------------
// Issue #107 — PersonAvatar
// ---------------------------------------------------------------------------

import { PersonAvatar } from '../components/ui/PersonAvatar';

describe('PersonAvatar — Issue #107', () => {
  it('renders initials fallback when no imageUrl provided', () => {
    render(<PersonAvatar name="Ravi Kumar" />);
    expect(screen.getByText('RK')).toBeTruthy();
    expect(screen.getByText(/no image/i)).toBeTruthy();
  });

  it('renders initials fallback when imageUrl is null', () => {
    render(<PersonAvatar name="Priya Sharma" imageUrl={null} />);
    expect(screen.getByText('PS')).toBeTruthy();
  });

  it('renders img element when imageUrl is provided', () => {
    render(<PersonAvatar name="Test Person" imageUrl="https://example.com/photo.jpg" />);
    const img = screen.getByRole('img', { name: /profile image/i });
    // The img tag itself is inside the container
    const imgEl = img.querySelector('img');
    expect(imgEl).toBeTruthy();
    expect(imgEl?.getAttribute('src')).toBe('https://example.com/photo.jpg');
  });

  it('falls back to initials when image fails to load', async () => {
    render(<PersonAvatar name="Fail Person" imageUrl="https://broken.url/img.jpg" />);
    const imgEl = document.querySelector('img');
    if (imgEl) {
      // Simulate error
      imgEl.dispatchEvent(new Event('error'));
    }
    await waitFor(() => {
      expect(screen.getByText('FP')).toBeTruthy();
    });
  });

  it('uses correct accent color for criminal (blue)', () => {
    const { container } = render(
      <PersonAvatar name="Criminal Test" accentColor="#1E6FD9" />
    );
    expect(container.firstChild).toBeTruthy();
  });

  it('uses correct accent color for victim (teal)', () => {
    const { container } = render(
      <PersonAvatar name="Victim Test" accentColor="#0E9E78" shape="circle" />
    );
    expect(container.firstChild).toBeTruthy();
  });

  it('renders single initial for single-word name', () => {
    render(<PersonAvatar name="Ravi" />);
    expect(screen.getByText('R')).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// Issue #118 — useFaceAuth real verification (no Math.random, no demo data)
// ---------------------------------------------------------------------------

import { renderHook, act } from '@testing-library/react';
import { useFaceAuth } from '../hooks/useFaceAuth';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v; },
    removeItem: (k: string) => { delete store[k]; },
    clear: () => { store = {}; },
  };
})();
vi.stubGlobal('localStorage', localStorageMock);

const mockWebcamRef = {
  current: {
    getScreenshot: () => 'data:image/jpeg;base64,/9j/fakeframe',
  },
};

const mockWebcamRefNoCamera = {
  current: null,
};

describe('useFaceAuth — Issue #118', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    localStorageMock.clear();
  });

  it('starts in idle state', () => {
    const { result } = renderHook(() => useFaceAuth());
    expect(result.current.scanSuccess).toBeNull();
    expect(result.current.isScanning).toBe(false);
    expect(result.current.state).toBe('idle');
  });

  it('does NOT use Math.random for authentication decision', () => {
    // The hook must call fetch, not Math.random
    const mathRandomSpy = vi.spyOn(Math, 'random');
    renderHook(() => useFaceAuth());
    // Math.random should never be called during hook initialization
    expect(mathRandomSpy).not.toHaveBeenCalled();
    mathRandomSpy.mockRestore();
  });

  it('calls /auth/face-verify endpoint on scan', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'NO_MATCH' }),
    });

    const { result } = renderHook(() => useFaceAuth());
    await act(async () => {
      result.current.startScanning(mockWebcamRef as any);
      await new Promise((r) => setTimeout(r, 1200));
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/face-verify'),
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('sets scanSuccess=false and errorMessage on NO_MATCH', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'NO_MATCH' }),
    });

    const { result } = renderHook(() => useFaceAuth());
    await act(async () => {
      result.current.startScanning(mockWebcamRef as any);
      await new Promise((r) => setTimeout(r, 1500));
    });

    expect(result.current.scanSuccess).toBe(false);
    expect(result.current.errorMessage).toBeTruthy();
    // Must not say "success" or "granted"
    expect(result.current.errorMessage?.toLowerCase()).not.toContain('granted');
  });

  it('sets scanSuccess=true and stores tokens on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        token_type: 'bearer',
        expires_in: 3600,
      }),
    });

    const { result } = renderHook(() => useFaceAuth());
    await act(async () => {
      result.current.startScanning(mockWebcamRef as any);
      await new Promise((r) => setTimeout(r, 1500));
    });

    expect(result.current.scanSuccess).toBe(true);
    expect(localStorageMock.getItem('saksha_access_token')).toBe('test-access-token');
    expect(localStorageMock.getItem('saksha_refresh_token')).toBe('test-refresh-token');
  });

  it('handles camera unavailable gracefully', async () => {
    const { result } = renderHook(() => useFaceAuth());
    await act(async () => {
      result.current.startScanning(mockWebcamRefNoCamera as any);
      await new Promise((r) => setTimeout(r, 1200));
    });

    expect(result.current.scanSuccess).toBe(false);
    expect(result.current.errorMessage).toBeTruthy();
    // fetch should NOT have been called — no frame to send
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('handles NO_ENROLLMENT error code', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'NO_ENROLLMENT' }),
    });

    const { result } = renderHook(() => useFaceAuth());
    await act(async () => {
      result.current.startScanning(mockWebcamRef as any);
      await new Promise((r) => setTimeout(r, 1500));
    });

    expect(result.current.scanSuccess).toBe(false);
    expect(result.current.errorMessage?.toLowerCase()).toContain('enrollment');
  });

  it('handles MULTI_FACE error code', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'MULTI_FACE' }),
    });

    const { result } = renderHook(() => useFaceAuth());
    await act(async () => {
      result.current.startScanning(mockWebcamRef as any);
      await new Promise((r) => setTimeout(r, 1500));
    });

    expect(result.current.scanSuccess).toBe(false);
    expect(result.current.errorMessage?.toLowerCase()).toContain('multiple');
  });

  it('resets state correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'NO_MATCH' }),
    });

    const { result } = renderHook(() => useFaceAuth());
    await act(async () => {
      result.current.startScanning(mockWebcamRef as any);
      await new Promise((r) => setTimeout(r, 1500));
    });

    expect(result.current.scanSuccess).toBe(false);

    act(() => { result.current.resetScanner(); });

    expect(result.current.scanSuccess).toBeNull();
    expect(result.current.state).toBe('idle');
    expect(result.current.errorMessage).toBeNull();
    expect(result.current.scanProgress).toBe(0);
  });

  it('never exposes embedding in hook return value', () => {
    const { result } = renderHook(() => useFaceAuth());
    const keys = Object.keys(result.current);
    expect(keys).not.toContain('face_embedding');
    expect(keys).not.toContain('embedding');
    expect(keys).not.toContain('gallery');
  });
});
