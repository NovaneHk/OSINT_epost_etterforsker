'use client';

import { Activity, AlertCircle } from 'lucide-react';
import type { SourceHealth } from '@/lib/types';
import { StatusBadge } from '@/components/shared/status-badge';
import { EmptyState } from '@/components/shared/empty-state';
import { formatResponseTime, formatRelative, formatNumber } from '@/lib/format';
import { cn } from '@/lib/utils';

interface SourceHealthGridProps {
  sources: SourceHealth[];
}

function HealthBar({ rate }: { rate: number }) {
  const color =
    rate >= 90
      ? 'bg-[var(--nt-success)]'
      : rate >= 70
        ? 'bg-[var(--nt-warning)]'
        : 'bg-[var(--nt-danger)]';

  return (
    <div
      className="h-1 w-full overflow-hidden rounded-full bg-[var(--nt-surface-elevated)]"
      role="progressbar"
      aria-valuenow={rate}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Success rate ${rate}%`}
    >
      <div className={cn('h-full rounded-full', color)} style={{ width: `${rate}%` }} />
    </div>
  );
}

export function SourceHealthGrid({ sources }: SourceHealthGridProps) {
  return (
    <div className="rounded-lg border border-[var(--nt-border)] bg-[var(--nt-surface)]">
      <div className="border-b border-[var(--nt-border)] px-5 py-4">
        <h2 className="text-sm font-semibold text-[var(--nt-text-primary)]">
          Source Health
        </h2>
        <p className="text-xs text-[var(--nt-text-secondary)]">
          {sources.filter((s) => s.status === 'active').length} of{' '}
          {sources.length} sources healthy
        </p>
      </div>

      {sources.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="No sources configured"
          description="Add a source to start monitoring data quality."
        />
      ) : (
        <div className="divide-y divide-[var(--nt-border)]">
          {sources.map((src) => (
            <div key={src.sourceId} className="flex flex-col gap-2 px-5 py-3">
              {/* Name + status */}
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0 flex items-center gap-2">
                  {(src.status === 'error' || src.status === 'degraded') && (
                    <AlertCircle
                      className="h-3.5 w-3.5 shrink-0 text-[var(--nt-warning)]"
                      aria-hidden="true"
                    />
                  )}
                  <span className="truncate text-sm font-medium text-[var(--nt-text-primary)]">
                    {src.sourceName}
                  </span>
                </div>
                <StatusBadge status={src.status} />
              </div>

              {/* Health bar */}
              <HealthBar rate={src.successRate} />

              {/* Stats row */}
              <div className="flex items-center justify-between text-[10px] text-[var(--nt-text-secondary)]">
                <span>
                  {src.successRate}% success · {formatResponseTime(src.avgResponseMs)}
                </span>
                <span>Checked {formatRelative(src.lastCheckedAt)}</span>
              </div>

              {/* Error message */}
              {src.errorMessage && (
                <p className="text-[10px] text-[var(--nt-danger)]">
                  {src.errorMessage}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
