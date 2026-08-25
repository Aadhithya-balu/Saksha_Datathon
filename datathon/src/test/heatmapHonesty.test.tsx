import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

const { mockMatrixOk, mockTemporalOk } = vi.hoisted(() => ({
  mockMatrixOk: vi.fn(),
  mockTemporalOk: vi.fn(),
}));

vi.mock('../services/api', () => ({
  getSociologicalTemporalMatrix: (...args: unknown[]) => mockMatrixOk(...args),
  getSociologicalTemporal: (...args: unknown[]) => mockTemporalOk(...args),
}));

import SpatiotemporalHeatmap from '../components/dashboard/SpatiotemporalHeatmap';

describe('SpatiotemporalHeatmap data-source honesty (issue 161)', () => {
  beforeEach(() => {
    mockMatrixOk.mockReset();
    mockTemporalOk.mockReset();
  });

  it('labels the grid DEMO DATA and drops the Database-Backed claim when both endpoints fail', async () => {
    mockMatrixOk.mockRejectedValue(new Error('backend down'));
    mockTemporalOk.mockRejectedValue(new Error('backend down'));

    render(<SpatiotemporalHeatmap />);

    await waitFor(() => expect(screen.getByText('Demo Data')).toBeInTheDocument());
    expect(screen.getByText(/Demo Baseline/i)).toBeInTheDocument();
    expect(screen.queryByText(/Database-Backed/i)).not.toBeInTheDocument();
  });

  it('keeps the Database-Backed label only when real matrix data arrives', async () => {
    mockMatrixOk.mockResolvedValue({
      matrix: [
        {
          hour: 20,
          cells: [
            { day: 'Friday', count: 12 },
            { day: 'Saturday', count: 18 },
          ],
        },
      ],
    });

    render(<SpatiotemporalHeatmap />);

    await waitFor(() => expect(screen.getByText(/Database-Backed/i)).toBeInTheDocument());
    expect(screen.queryByText('Demo Data')).not.toBeInTheDocument();
  });
});
