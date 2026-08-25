import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import IntelligenceStatusBadges from '../components/ui/IntelligenceStatusBadges';
import { getIntelligenceStatus } from '../services/intelligenceStatus';

describe('IntelligenceStatusBadges (issue 9 §25 accessibility)', () => {
  it('renders status as readable text with an accessible description', () => {
    const badges = getIntelligenceStatus({ predictionMode: 'FALLBACK', dataProvenance: 'LIVE_DB' });
    render(<IntelligenceStatusBadges badges={badges} />);
    const el = screen.getByText('STATISTICAL FALLBACK');
    expect(el).toBeInTheDocument();
    // Screen-reader-friendly: role=status + full-text aria-label.
    expect(el.closest('[role="status"]')).not.toBeNull();
    expect(el.closest('[role="status"]')?.getAttribute('aria-label')).toContain('fallback');
  });

  it('shows both primary and secondary warnings when both apply', () => {
    const badges = getIntelligenceStatus({ predictionMode: 'FALLBACK', dataProvenance: 'DEMO' });
    render(<IntelligenceStatusBadges badges={badges} />);
    expect(screen.getByText('DEMO DATA')).toBeInTheDocument();
    expect(screen.getByText('STATISTICAL FALLBACK')).toBeInTheDocument();
  });
});
