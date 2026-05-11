import { cn } from '@/lib/utils';
import type { RunStatus, SourceStatus, LeadStatus } from '@/lib/types';

type StatusValue = RunStatus | SourceStatus | LeadStatus;

const CONFIG: Record<
  StatusValue,
  { label: string; dot: string; text: string; bg: string }
> = {
  // Run statuses
  queued: {
    label: 'Queued',
    dot: 'bg-[var(--nt-text-secondary)]',
    text: 'text-[var(--nt-text-secondary)]',
    bg: 'bg-[var(--nt-text-secondary)]/10',
  },
  running: {
    label: 'Running',
    dot: 'bg-[var(--nt-accent)]',
    text: 'text-[var(--nt-accent)]',
    bg: 'bg-[var(--nt-accent)]/10',
  },
  completed: {
    label: 'Completed',
    dot: 'bg-[var(--nt-success)]',
    text: 'text-[var(--nt-success)]',
    bg: 'bg-[var(--nt-success)]/10',
  },
  failed: {
    label: 'Failed',
    dot: 'bg-[var(--nt-danger)]',
    text: 'text-[var(--nt-danger)]',
    bg: 'bg-[var(--nt-danger)]/10',
  },
  cancelled: {
    label: 'Cancelled',
    dot: 'bg-[var(--nt-text-secondary)]',
    text: 'text-[var(--nt-text-secondary)]',
    bg: 'bg-[var(--nt-text-secondary)]/10',
  },
  // Source statuses
  active: {
    label: 'Active',
    dot: 'bg-[var(--nt-success)]',
    text: 'text-[var(--nt-success)]',
    bg: 'bg-[var(--nt-success)]/10',
  },
  paused: {
    label: 'Paused',
    dot: 'bg-[var(--nt-warning)]',
    text: 'text-[var(--nt-warning)]',
    bg: 'bg-[var(--nt-warning)]/10',
  },
  error: {
    label: 'Error',
    dot: 'bg-[var(--nt-danger)]',
    text: 'text-[var(--nt-danger)]',
    bg: 'bg-[var(--nt-danger)]/10',
  },
  degraded: {
    label: 'Degraded',
    dot: 'bg-[var(--nt-warning)]',
    text: 'text-[var(--nt-warning)]',
    bg: 'bg-[var(--nt-warning)]/10',
  },
  // Lead statuses
  new: {
    label: 'New',
    dot: 'bg-[var(--nt-accent)]',
    text: 'text-[var(--nt-accent)]',
    bg: 'bg-[var(--nt-accent)]/10',
  },
  qualified: {
    label: 'Qualified',
    dot: 'bg-[var(--nt-ai)]',
    text: 'text-[var(--nt-ai)]',
    bg: 'bg-[var(--nt-ai)]/10',
  },
  contacted: {
    label: 'Contacted',
    dot: 'bg-[var(--nt-warning)]',
    text: 'text-[var(--nt-warning)]',
    bg: 'bg-[var(--nt-warning)]/10',
  },
  converted: {
    label: 'Converted',
    dot: 'bg-[var(--nt-success)]',
    text: 'text-[var(--nt-success)]',
    bg: 'bg-[var(--nt-success)]/10',
  },
  archived: {
    label: 'Archived',
    dot: 'bg-[var(--nt-text-secondary)]',
    text: 'text-[var(--nt-text-secondary)]',
    bg: 'bg-[var(--nt-text-secondary)]/10',
  },
};

interface StatusBadgeProps {
  status: StatusValue;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const cfg = CONFIG[status];
  if (!cfg) return null;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium',
        cfg.bg,
        cfg.text,
        className
      )}
    >
      <span
        className={cn('h-1.5 w-1.5 rounded-full', cfg.dot)}
        aria-hidden="true"
      />
      {cfg.label}
    </span>
  );
}
