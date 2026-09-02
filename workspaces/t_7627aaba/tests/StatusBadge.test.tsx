/**
 * Tests for StatusBadge — pure presentational component.
 * Verifies color mapping and accessibility attributes for each status.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge, STATUS_LABELS } from '../src/components/StatusBadge';
import { AgentStatus } from '../src/types/trace';

const ALL_STATUSES: AgentStatus[] = ['idle', 'planning', 'executing', 'observing', 'done', 'failed'];

describe('StatusBadge', () => {
  it('renders the correct label for each status', () => {
    ALL_STATUSES.forEach((status) => {
      const { unmount } = render(<StatusBadge status={status} />);
      const badge = screen.getByTestId('status-badge');
      expect(badge).toHaveTextContent(STATUS_LABELS[status]);
      expect(badge).toHaveAttribute('data-status', status);
      unmount();
    });
  });

  it('idle status uses slate background', () => {
    render(<StatusBadge status="idle" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge).toHaveClass('text-slate-400');
  });

  it('planning status uses amber text', () => {
    render(<StatusBadge status="planning" />);
    expect(screen.getByTestId('status-badge')).toHaveClass('text-amber-400');
  });

  it('executing status uses sky text', () => {
    render(<StatusBadge status="executing" />);
    expect(screen.getByTestId('status-badge')).toHaveClass('text-sky-400');
  });

  it('observing status uses violet text', () => {
    render(<StatusBadge status='observing' />);
    expect(screen.getByTestId('status-badge')).toHaveClass('text-violet-400');
  });

  it('done status uses green text + bg', () => {
    render(<StatusBadge status="done" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge).toHaveClass('text-green-400');
    expect(badge).toHaveClass('bg-green-900/30');
  });

  it('failed status uses red text + bg', () => {
    render(<StatusBadge status="failed" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge).toHaveClass('text-red-400');
    expect(badge).toHaveClass('bg-red-900/30');
  });

  it('accepts a custom className', () => {
    render(<StatusBadge status="done" className="ml-2" />);
    expect(screen.getByTestId('status-badge')).toHaveClass('ml-2');
  });
});
