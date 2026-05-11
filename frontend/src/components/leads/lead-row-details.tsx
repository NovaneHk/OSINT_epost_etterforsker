'use client';

import { Copy, Linkedin, Phone, Tag, Clock, Database, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import type { Lead } from '@/lib/types';
import { LeadStatusBadge } from '@/components/leads/lead-status-badge';
import { ScoreBadge } from '@/components/leads/score-badge';
import { formatDateTime, formatRelative } from '@/lib/format';

interface LeadRowDetailsProps {
  lead: Lead;
  onMarkContacted: (id: string) => void;
}

function DetailItem({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-[10px] font-semibold uppercase tracking-widest text-[var(--nt-text-secondary)]">
        {label}
      </dt>
      <dd className="text-sm text-[var(--nt-text-primary)]">{children}</dd>
    </div>
  );
}

export function LeadRowDetails({ lead, onMarkContacted }: LeadRowDetailsProps) {
  function copyEmail() {
    navigator.clipboard.writeText(lead.email).then(() => {
      toast.success('Email copied', { description: lead.email });
    });
  }

  return (
    <div
      data-testid="lead-modal"
      className="grid grid-cols-1 gap-6 border-t border-[var(--nt-border)] bg-[var(--nt-surface-elevated)] px-6 py-5 sm:grid-cols-2 lg:grid-cols-3"
    >
      {/* ── Company / contact ─────────────────────────────────────── */}
      <div className="space-y-4">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-[var(--nt-text-secondary)]">
          <Database className="h-3.5 w-3.5" aria-hidden="true" />
          Company &amp; Contact
        </h3>
        <dl className="space-y-3">
          <DetailItem label="Company">{lead.company}</DetailItem>
          <DetailItem label="Domain">
            <a
              href={`https://${lead.domain}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--nt-accent)] hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)] rounded"
            >
              {lead.domain}
            </a>
          </DetailItem>
          {lead.position && <DetailItem label="Position">{lead.position}</DetailItem>}
          <DetailItem label="Email">
            <button
              onClick={copyEmail}
              className="inline-flex items-center gap-1 text-[var(--nt-text-primary)] hover:text-[var(--nt-accent)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)] rounded"
              aria-label={`Copy email ${lead.email}`}
            >
              <span data-testid="lead-email">{lead.email}</span>
              <Copy className="h-3 w-3" aria-hidden="true" />
            </button>
          </DetailItem>
          {lead.phone && (
            <DetailItem label="Phone">
              <span className="inline-flex items-center gap-1">
                <Phone className="h-3 w-3 text-[var(--nt-text-secondary)]" aria-hidden="true" />
                {lead.phone}
              </span>
            </DetailItem>
          )}
          {lead.linkedIn && (
            <DetailItem label="LinkedIn">
              <a
                href={lead.linkedIn}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[var(--nt-accent)] hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)] rounded"
              >
                <Linkedin className="h-3 w-3" aria-hidden="true" />
                View profile
              </a>
            </DetailItem>
          )}
        </dl>
      </div>

      {/* ── Score / status / source ───────────────────────────────── */}
      <div className="space-y-4">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-[var(--nt-text-secondary)]">
          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
          Validation &amp; Source
        </h3>
        <dl className="space-y-3">
          <DetailItem label="Score">
            <span className="inline-flex items-center gap-2">
              <ScoreBadge score={lead.score} band={lead.scoreBand} />
              <span className="text-xs text-[var(--nt-text-secondary)]">{lead.scoreBand} quality</span>
            </span>
          </DetailItem>
          <DetailItem label="Status">
            <LeadStatusBadge status={lead.status} />
          </DetailItem>
          <DetailItem label="Source">
            <span data-testid="lead-company" className="text-[var(--nt-text-primary)]">
              {lead.sourceName}
            </span>
          </DetailItem>
          <DetailItem label="Confidence score">
            <span data-testid="lead-confidence">{lead.score}</span>
          </DetailItem>
          {lead.tags && lead.tags.length > 0 && (
            <DetailItem label="Tags">
              <span className="flex flex-wrap gap-1">
                {lead.tags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-0.5 rounded-full bg-[var(--nt-surface)] px-2 py-0.5 text-[10px] font-medium text-[var(--nt-text-secondary)]"
                  >
                    <Tag className="h-2.5 w-2.5" aria-hidden="true" />
                    {tag}
                  </span>
                ))}
              </span>
            </DetailItem>
          )}
        </dl>
      </div>

      {/* ── Timestamps + actions ──────────────────────────────────── */}
      <div className="space-y-4">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-[var(--nt-text-secondary)]">
          <Clock className="h-3.5 w-3.5" aria-hidden="true" />
          History
        </h3>
        <dl className="space-y-3">
          <DetailItem label="Discovered">
            <span title={formatDateTime(lead.foundAt)}>{formatRelative(lead.foundAt)}</span>
          </DetailItem>
          <DetailItem label="Last updated">
            <span title={formatDateTime(lead.updatedAt)}>{formatRelative(lead.updatedAt)}</span>
          </DetailItem>
          <DetailItem label="Source run">run via {lead.sourceName}</DetailItem>
        </dl>

        {/* Actions */}
        <div className="flex flex-wrap gap-2 pt-2">
          <button
            onClick={() => onMarkContacted(lead.id)}
            disabled={lead.status === 'contacted' || lead.status === 'converted'}
            className="rounded-md bg-[var(--nt-accent)]/15 px-3 py-1.5 text-xs font-medium text-[var(--nt-accent)] transition-colors hover:bg-[var(--nt-accent)]/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)] disabled:cursor-not-allowed disabled:opacity-40"
          >
            Mark contacted
          </button>
          <button
            onClick={() => {
              navigator.clipboard.writeText(lead.email).then(() => {
                toast.success('Email copied', { description: lead.email });
              });
            }}
            className="rounded-md bg-[var(--nt-surface)] px-3 py-1.5 text-xs font-medium text-[var(--nt-text-secondary)] ring-1 ring-[var(--nt-border)] transition-colors hover:text-[var(--nt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)]"
          >
            Copy email
          </button>
        </div>
      </div>
    </div>
  );
}
