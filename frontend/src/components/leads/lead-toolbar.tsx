'use client';

import { useRef } from 'react';
import { Search, X, SlidersHorizontal } from 'lucide-react';
import type { LeadStatus } from '@/lib/types';
import { LEAD_STATUS_LABELS } from '@/lib/constants';
import { cn } from '@/lib/utils';

interface LeadToolbarProps {
  globalFilter: string;
  onGlobalFilterChange: (value: string) => void;
  statusFilter: LeadStatus | '';
  onStatusFilterChange: (status: LeadStatus | '') => void;
  totalCount: number;
  filteredCount: number;
}

const STATUS_OPTIONS = Object.entries(LEAD_STATUS_LABELS) as [LeadStatus, string][];

export function LeadToolbar({
  globalFilter,
  onGlobalFilterChange,
  statusFilter,
  onStatusFilterChange,
  totalCount,
  filteredCount,
}: LeadToolbarProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      data-testid="filter-bar"
      className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--nt-border)] bg-[var(--nt-surface)] px-4 py-3"
    >
      {/* Search */}
      <div className="relative flex min-w-[220px] flex-1 items-center">
        <Search
          className="pointer-events-none absolute left-3 h-3.5 w-3.5 text-[var(--nt-text-secondary)]"
          aria-hidden="true"
        />
        <input
          ref={inputRef}
          data-testid="search-input"
          type="search"
          placeholder="Search name, email, company…"
          value={globalFilter}
          onChange={(e) => onGlobalFilterChange(e.target.value)}
          className="w-full rounded-md border border-[var(--nt-border)] bg-[var(--nt-surface-elevated)] py-1.5 pl-8 pr-8 text-sm text-[var(--nt-text-primary)] placeholder:text-[var(--nt-text-secondary)] outline-none focus:ring-2 focus:ring-[var(--nt-accent)] focus:ring-offset-0"
        />
        {globalFilter && (
          <button
            onClick={() => { onGlobalFilterChange(''); inputRef.current?.focus(); }}
            aria-label="Clear search"
            className="absolute right-2 rounded p-0.5 text-[var(--nt-text-secondary)] hover:text-[var(--nt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)]"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        )}
      </div>

      {/* Status filter */}
      <div className="flex items-center gap-1.5">
        <SlidersHorizontal className="h-3.5 w-3.5 text-[var(--nt-text-secondary)]" aria-hidden="true" />
        <div className="flex flex-wrap gap-1">
          <button
            onClick={() => onStatusFilterChange('')}
            className={cn(
              'rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
              statusFilter === ''
                ? 'bg-[var(--nt-accent)] text-white'
                : 'bg-[var(--nt-surface-elevated)] text-[var(--nt-text-secondary)] hover:text-[var(--nt-text-primary)]'
            )}
          >
            All
          </button>
          {STATUS_OPTIONS.map(([value, label]) => (
            <button
              key={value}
              onClick={() => onStatusFilterChange(value)}
              className={cn(
                'rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
                statusFilter === value
                  ? 'bg-[var(--nt-accent)] text-white'
                  : 'bg-[var(--nt-surface-elevated)] text-[var(--nt-text-secondary)] hover:text-[var(--nt-text-primary)]'
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Count */}
      <span className="ml-auto shrink-0 text-xs text-[var(--nt-text-secondary)]">
        {filteredCount < totalCount ? `${filteredCount} of ${totalCount}` : totalCount} leads
      </span>
    </div>
  );
}
