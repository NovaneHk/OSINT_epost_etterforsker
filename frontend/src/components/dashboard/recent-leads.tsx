'use client';

import { Users, Copy, ExternalLink } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import type { Lead } from '@/lib/types';
import { StatusBadge } from '@/components/shared/status-badge';
import { EmptyState } from '@/components/shared/empty-state';
import { SCORE_BAND_TEXT, SCORE_BAND_BG } from '@/lib/constants';
import { formatRelative } from '@/lib/format';
import { cn } from '@/lib/utils';

interface RecentLeadsProps {
  leads: Lead[];
}

function ScorePill({ score, band }: { score: number; band: Lead['scoreBand'] }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-semibold tabular-nums',
        SCORE_BAND_BG[band],
        SCORE_BAND_TEXT[band]
      )}
    >
      {score}
    </span>
  );
}

export function RecentLeads({ leads }: RecentLeadsProps) {
  const recent = leads.slice(0, 8);

  function copyEmail(email: string) {
    navigator.clipboard.writeText(email).then(() => {
      toast.success('Email copied', { description: email });
    });
  }

  return (
    <div className="rounded-lg border border-[var(--nt-border)] bg-[var(--nt-surface)]">
      <div className="flex items-center justify-between border-b border-[var(--nt-border)] px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-[var(--nt-text-primary)]">
            Recent Leads
          </h2>
          <p className="text-xs text-[var(--nt-text-secondary)]">
            Latest discovered leads
          </p>
        </div>
        <Link
          href="/leads"
          className="text-xs font-medium text-[var(--nt-accent)] hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)] rounded"
        >
          View all
        </Link>
      </div>

      {recent.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No leads yet"
          description="Leads discovered by runs will appear here."
        />
      ) : (
        <div className="divide-y divide-[var(--nt-border)]" role="list">
          {recent.map((lead) => (
            <div
              key={lead.id}
              role="listitem"
              className="group flex items-center gap-3 px-5 py-3"
            >
              {/* Score */}
              <ScorePill score={lead.score} band={lead.scoreBand} />

              {/* Info */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium text-[var(--nt-text-primary)]">
                    {lead.name}
                  </span>
                  <span className="hidden text-xs text-[var(--nt-text-secondary)] sm:inline">
                    · {lead.company}
                  </span>
                </div>
                <p className="truncate text-xs text-[var(--nt-text-secondary)]">
                  {lead.position && `${lead.position} · `}{lead.email}
                </p>
              </div>

              {/* Status */}
              <StatusBadge status={lead.status} className="hidden sm:inline-flex" />

              {/* Time */}
              <span className="hidden shrink-0 text-[10px] text-[var(--nt-text-secondary)] lg:inline">
                {formatRelative(lead.foundAt)}
              </span>

              {/* Actions */}
              <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                <button
                  onClick={() => copyEmail(lead.email)}
                  aria-label={`Copy email for ${lead.name}`}
                  className="rounded p-1 text-[var(--nt-text-secondary)] hover:bg-[var(--nt-surface-elevated)] hover:text-[var(--nt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)]"
                >
                  <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
                <Link
                  href="/leads"
                  aria-label={`View ${lead.name} in leads`}
                  className="rounded p-1 text-[var(--nt-text-secondary)] hover:bg-[var(--nt-surface-elevated)] hover:text-[var(--nt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)]"
                >
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
