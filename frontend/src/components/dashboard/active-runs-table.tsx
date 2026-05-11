'use client';

import { Play, Clock } from 'lucide-react';
import type { Run } from '@/lib/types';
import { StatusBadge } from '@/components/shared/status-badge';
import { EmptyState } from '@/components/shared/empty-state';
import { formatRelative, formatProgress } from '@/lib/format';

interface ActiveRunsTableProps {
  runs: Run[];
}

export function ActiveRunsTable({ runs }: ActiveRunsTableProps) {
  const activeRuns = runs.filter(
    (r) => r.status === 'running' || r.status === 'queued'
  );

  return (
    <div className="rounded-lg border border-[var(--nt-border)] bg-[var(--nt-surface)]">
      <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--nt-border)]">
        <div>
          <h2 className="text-sm font-semibold text-[var(--nt-text-primary)]">
            Active Runs
          </h2>
          <p className="text-xs text-[var(--nt-text-secondary)]">
            {activeRuns.length} run{activeRuns.length !== 1 ? 's' : ''} in progress
          </p>
        </div>
        {activeRuns.length > 0 && (
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--nt-accent)]/15 text-[10px] font-semibold text-[var(--nt-accent)]">
            {activeRuns.length}
          </span>
        )}
      </div>

      {activeRuns.length === 0 ? (
        <EmptyState
          icon={Play}
          title="No active runs"
          description="Start a run from Sources or Playbooks to see progress here."
        />
      ) : (
        <div className="divide-y divide-[var(--nt-border)]" role="list">
          {activeRuns.map((run) => (
            <div
              key={run.id}
              role="listitem"
              className="flex flex-col gap-2 px-5 py-4"
            >
              {/* Top row: name + status */}
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-[var(--nt-text-primary)]">
                    {run.name}
                  </p>
                  <p className="text-xs text-[var(--nt-text-secondary)]">
                    {run.sourceName}
                  </p>
                </div>
                <StatusBadge status={run.status} />
              </div>

              {/* Progress bar */}
              {run.status === 'running' && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[10px] text-[var(--nt-text-secondary)]">
                    <span>{formatProgress(run.progress)}</span>
                    <span>{run.leadsFound} leads found</span>
                  </div>
                  <div
                    className="h-1 w-full overflow-hidden rounded-full bg-[var(--nt-surface-elevated)]"
                    role="progressbar"
                    aria-valuenow={run.progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`${run.name} progress`}
                  >
                    <div
                      className="h-full rounded-full bg-[var(--nt-accent)] transition-all"
                      style={{ width: `${run.progress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Footer: started */}
              {run.startedAt && (
                <div className="flex items-center gap-1 text-[10px] text-[var(--nt-text-secondary)]">
                  <Clock className="h-3 w-3" aria-hidden="true" />
                  Started {formatRelative(run.startedAt)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
