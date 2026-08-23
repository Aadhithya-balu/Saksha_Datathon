import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

const previewPayload = {
  report_type: 'cases',
  headers: ['case_number', 'status'],
  filters: {},
  total: 2,
  page: 1,
  page_size: 50,
  results: [
    { case_number: 'CR-2026-001', status: 'open' },
    { case_number: 'CR-2026-002', status: 'closed' },
  ],
};

vi.mock('../services/api', () => ({
  apiRequest: vi.fn(),
}));

import { apiRequest } from '../services/api';
import Reports from '../pages/Reports';

beforeEach(() => {
  vi.mocked(apiRequest).mockReset();
});

describe('Reports page', () => {
  it('renders statistics, filters and data rows from the backend', async () => {
    vi.mocked(apiRequest).mockImplementation(((path: string) => {
      if (String(path).includes('/statistics/summary')) {
        return Promise.resolve({ cases: 11, officers: 4 });
      }
      return Promise.resolve(previewPayload);
    }) as never);

    const { container } = render(<Reports />);

    await waitFor(() => expect(screen.getByText('CR-2026-001')).toBeInTheDocument());
    expect(screen.getByText(/Case Report - 2 matching records/i)).toBeInTheDocument();
    expect(container.querySelector('table')).not.toBeNull();
  });

  it('shows an inline error instead of crashing when the backend fails', async () => {
    vi.mocked(apiRequest).mockRejectedValue(new Error('Internal Server Error'));
    render(<Reports />);
    await waitFor(() => expect(screen.getByText(/Internal Server Error/i)).toBeInTheDocument());
    expect(screen.getByText(/Administrative Reporting/i)).toBeInTheDocument();
  });
});
