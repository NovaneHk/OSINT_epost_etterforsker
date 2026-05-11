'use client';

import React, { memo, useMemo } from 'react';
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
  type Updater,
} from '@tanstack/react-table';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Copy,
  ChevronDown,
  ChevronRight,
  Users,
} from 'lucide-react';
import { toast } from 'sonner';
import type { Lead } from '@/lib/types';
import { ScoreBadge } from '@/components/leads/score-badge';
import { LeadStatusBadge } from '@/components/leads/lead-status-badge';
import { LeadRowDetails } from '@/components/leads/lead-row-details';
import { SkeletonBlock } from '@/components/shared/skeleton-block';
import { EmptyState } from '@/components/shared/empty-state';
import { formatDateShort } from '@/lib/format';
import { cn } from '@/lib/utils';

interface LeadTableProps {
  data: Lead[];
  isLoading?: boolean;
  globalFilter: string;
  sorting: SortingState;
  onSortingChange: (sorting: SortingState) => void;
  rowSelection: RowSelectionState;
  onRowSelectionChange: (selection: RowSelectionState) => void;
  expandedRowId: string | null;
  onExpandedRowChange: (id: string | null) => void;
  onMarkContacted: (id: string) => void;
}

function SortIcon({ sorted }: { sorted: false | 'asc' | 'desc' }) {
  if (!sorted) return <ArrowUpDown className="ml-1 h-3.5 w-3.5 text-[var(--nt-text-secondary)] opacity-50" aria-hidden="true" />;
  return sorted === 'asc'
    ? <ArrowUp className="ml-1 h-3.5 w-3.5 text-[var(--nt-accent)]" aria-hidden="true" />
    : <ArrowDown className="ml-1 h-3.5 w-3.5 text-[var(--nt-accent)]" aria-hidden="true" />;
}

export const LeadTable = memo(function LeadTable({
  data,
  isLoading,
  globalFilter,
  sorting,
  onSortingChange,
  rowSelection,
  onRowSelectionChange,
  expandedRowId,
  onExpandedRowChange,
  onMarkContacted,
}: LeadTableProps) {
  const columns = useMemo<ColumnDef<Lead>[]>(
    () => [
      {
        id: 'select',
        header: ({ table }) => (
          <input
            type="checkbox"
            checked={table.getIsAllPageRowsSelected()}
            ref={(el) => {
              if (el) el.indeterminate = table.getIsSomePageRowsSelected();
            }}
            onChange={table.getToggleAllPageRowsSelectedHandler()}
            aria-label="Select all leads"
            className="h-4 w-4 cursor-pointer rounded border-[var(--nt-border)] accent-[var(--nt-accent)]"
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            checked={row.getIsSelected()}
            onChange={row.getToggleSelectedHandler()}
            onClick={(e) => e.stopPropagation()}
            aria-label={`Select ${row.original.name}`}
            className="h-4 w-4 cursor-pointer rounded border-[var(--nt-border)] accent-[var(--nt-accent)]"
          />
        ),
        size: 40,
        enableSorting: false,
      },
      {
        id: 'email',
        accessorKey: 'email',
        header: ({ column }) => (
          <button
            className="flex items-center text-xs uppercase tracking-wider"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Email
            <SortIcon sorted={column.getIsSorted()} />
          </button>
        ),
        cell: ({ row }) => (
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm font-medium text-[var(--nt-text-primary)]">
              {row.original.name}
            </span>
            <span className="truncate text-xs text-[var(--nt-text-secondary)]">
              {row.original.email}
            </span>
          </div>
        ),
        size: 240,
      },
      {
        id: 'domain',
        accessorKey: 'domain',
        header: ({ column }) => (
          <button
            className="flex items-center text-xs uppercase tracking-wider"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Domain
            <SortIcon sorted={column.getIsSorted()} />
          </button>
        ),
        cell: ({ row }) => (
          <span className="text-xs text-[var(--nt-text-secondary)]">
            {row.original.domain}
          </span>
        ),
        size: 160,
      },
      {
        id: 'score',
        accessorKey: 'score',
        header: ({ column }) => (
          <button
            data-testid="confidence-header"
            className="flex items-center text-xs uppercase tracking-wider"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Score
            <SortIcon sorted={column.getIsSorted()} />
          </button>
        ),
        cell: ({ row }) => (
          <span data-testid="confidence-score">
            <ScoreBadge score={row.original.score} band={row.original.scoreBand} />
          </span>
        ),
        size: 80,
      },
      {
        id: 'sourceName',
        accessorKey: 'sourceName',
        header: () => <span className="text-xs uppercase tracking-wider">Source</span>,
        cell: ({ row }) => (
          <span className="text-xs text-[var(--nt-text-secondary)]">{row.original.sourceName}</span>
        ),
        size: 160,
        enableSorting: false,
      },
      {
        id: 'foundAt',
        accessorKey: 'foundAt',
        header: ({ column }) => (
          <button
            className="flex items-center text-xs uppercase tracking-wider"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Found
            <SortIcon sorted={column.getIsSorted()} />
          </button>
        ),
        cell: ({ row }) => (
          <span className="text-xs text-[var(--nt-text-secondary)]" title={row.original.foundAt}>
            {formatDateShort(row.original.foundAt)}
          </span>
        ),
        size: 90,
      },
      {
        id: 'actions',
        header: () => null,
        cell: ({ row }) => {
          const isExpanded = expandedRowId === row.original.id;
          return (
            <div className="flex items-center justify-end gap-1">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  navigator.clipboard.writeText(row.original.email).then(() => {
                    toast.success('Email copied', { description: row.original.email });
                  });
                }}
                aria-label={`Copy email for ${row.original.name}`}
                className="rounded p-1.5 text-[var(--nt-text-secondary)] hover:bg-[var(--nt-surface-elevated)] hover:text-[var(--nt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)]"
              >
                <Copy className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
              <button
                data-testid="view-lead"
                onClick={(e) => {
                  e.stopPropagation();
                  onExpandedRowChange(isExpanded ? null : row.original.id);
                }}
                aria-label={isExpanded ? `Collapse ${row.original.name}` : `Expand ${row.original.name}`}
                aria-expanded={isExpanded}
                className="rounded p-1.5 text-[var(--nt-text-secondary)] hover:bg-[var(--nt-surface-elevated)] hover:text-[var(--nt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)]"
              >
                {isExpanded
                  ? <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                  : <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />}
              </button>
            </div>
          );
        },
        size: 80,
        enableSorting: false,
      },
    ],
    [expandedRowId, onExpandedRowChange]
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting, rowSelection, globalFilter },
    onSortingChange: (updater: Updater<SortingState>) => {
      onSortingChange(typeof updater === 'function' ? updater(sorting) : updater);
    },
    onRowSelectionChange: (updater: Updater<RowSelectionState>) => {
      onRowSelectionChange(typeof updater === 'function' ? updater(rowSelection) : updater);
    },
    onGlobalFilterChange: () => {},
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    globalFilterFn: (row, _id, filterValue: string) => {
      const q = filterValue.toLowerCase();
      const { name, email, company, domain } = row.original;
      return (
        name.toLowerCase().includes(q) ||
        email.toLowerCase().includes(q) ||
        company.toLowerCase().includes(q) ||
        domain.toLowerCase().includes(q)
      );
    },
    enableRowSelection: true,
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonBlock key={i} className="h-12 rounded" />
        ))}
      </div>
    );
  }

  const rows = table.getRowModel().rows;

  if (rows.length === 0) {
    return (
      <EmptyState
        icon={Users}
        title="No leads found"
        description="Try adjusting your search or filters, or start a run to discover new leads."
        className="rounded-lg border border-[var(--nt-border)] bg-[var(--nt-surface)]"
      />
    );
  }

  return (
    <div
      data-testid="leads-table"
      className="overflow-hidden rounded-lg border border-[var(--nt-border)]"
      role="region"
      aria-label="Leads table"
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-[var(--nt-border)] bg-[var(--nt-surface)]">
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-4 py-3 text-left font-medium text-[var(--nt-text-secondary)]"
                    style={{ width: header.getSize() }}
                    aria-sort={
                      header.column.getIsSorted() === 'asc' ? 'ascending'
                      : header.column.getIsSorted() === 'desc' ? 'descending'
                      : undefined
                    }
                  >
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="bg-[var(--nt-surface)]">
            {rows.map((row) => {
              const isExpanded = expandedRowId === row.original.id;
              return (
                <React.Fragment key={row.id}>
                  <tr
                    className={cn(
                      'cursor-pointer border-b border-[var(--nt-border)] transition-colors last:border-b-0',
                      row.getIsSelected() ? 'bg-[var(--nt-accent)]/5' : 'hover:bg-[var(--nt-surface-elevated)]',
                      isExpanded && 'bg-[var(--nt-surface-elevated)]'
                    )}
                    onClick={() => onExpandedRowChange(isExpanded ? null : row.original.id)}
                    aria-selected={row.getIsSelected()}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                  {isExpanded && (
                    <tr key={`${row.id}-details`} className="border-b border-[var(--nt-border)] last:border-b-0">
                      <td colSpan={columns.length} className="p-0">
                        <LeadRowDetails lead={row.original} onMarkContacted={onMarkContacted} />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between border-t border-[var(--nt-border)] bg-[var(--nt-surface)] px-4 py-2.5">
        <span className="text-xs text-[var(--nt-text-secondary)]">
          {Object.keys(rowSelection).length > 0 && <>{Object.keys(rowSelection).length} selected · </>}
          {rows.length} rows
        </span>
      </div>
    </div>
  );
});
