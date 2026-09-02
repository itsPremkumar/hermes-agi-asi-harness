/**
 * Tests for StatusBadge component.
 * @vitest @component
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../src/components/StatusBadge';

describe('StatusBadge', () => {
  it('renders the correct status label', () => {
    render(<StatusBadge status="planning" />);
    expect(screen.getByText('Planning')).toBeInTheDocument();
  });

  it('renders all agent statuses correctly', () => {
    const statuses = ['idle', 'planning', 'executing', 'observing', 'done', 'failed'];
    statuses.forEach((status) => {
      const { unmount } = render(<StatusBadge status={status as any} />);
      const label = status.charAt(0).toUpperCase() + status.slice(1);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    });
  });

  it('applies correct data-status attribute', () => {
    render(<StatusBadge status="executing" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge).toHaveAttribute('data-status', 'executing');
  });

  it('renders "Failed" for failed status', () => {
    render(<StatusBadge status="failed" />);
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByTestId('status-badge')).toHaveAttribute('data-status', 'failed');
  });

  it('renders "Done" for done status', () => {
    render(<StatusBadge status="done" />);
    expect(screen.getByText('Done')).toBeInTheDocument();
  });
});
