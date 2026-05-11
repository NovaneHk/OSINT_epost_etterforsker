'use client';

import { useState, useEffect, useMemo, useCallback, useTransition, useRef } from 'react';
import { type SortingState, type RowSelectionState } from '@tanstack/react-table';
import { toast } from 'sonner';
import { AlertCircle } from 'lucide-react';
import { getLeads, updateLead, bulkUpdateLeads } from '@/lib/data/leads';
import type { Lead, LeadStatus } from '@/lib/types';
import { LeadToolbar } from '@/components/leads/lead-toolbar';
import { LeadTable } from '@/components/leads/lead-table';
import { BulkActionBar } from '@/components/leads/bulk-action-bar';
import { SkeletonBlock } from '@/components/shared/skeleton-block';

export function LeadsPageClient() {
  // inputFilter drives the controlled input; globalFilter drives TanStack (deferred)
  const [inputFilter, setInputFilter] = useState('');
  const [globalFilter, setGlobalFilter] = useState('');
  const [, startTransition] = useTransition();
  const [statusFilter, setStatusFilter] = useState<LeadStatus | ''>('');
  const [sorting, setSorting] = useState<SortingState>([{ id: 'score', desc: true }]);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  // Stable ref so handleMarkContacted doesn't recreate on every leads update
  const leadsRef = useRef<Lead[]>(leads);

  useEffect(() => {
    leadsRef.current = leads;
  }, [leads]);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setLoadError(null);
    getLeads({ pageSize: 200 })
      .then((res) => {
        if (cancelled) return;
        setLeads(res.data.items);
      })
      .catch((err) => {
        if (!cancelled)
          setLoadError(err instanceof Error ? err.message : 'Failed to load leads');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const filteredLeads = useMemo(() => {
    if (!statusFilter) return leads;
    return leads.filter((l) => l.status === statusFilter);
  }, [leads, statusFilter]);

  const selectedCount = useMemo(() => Object.keys(rowSelection).length, [rowSelection]);

  // Derive selected lead IDs (by index since TanStack uses row index as key by default)
  const selectedLeads = useMemo(() => {
    return Object.keys(rowSelection).map((idx) => filteredLeads[Number(idx)]).filter(Boolean);
  }, [rowSelection, filteredLeads]);

  // Deferred filter: input stays responsive; TanStack filter runs at lower priority
  const handleFilterChange = useCallback((value: string) => {
    setInputFilter(value);
    startTransition(() => setGlobalFilter(value));
  }, []); // startTransition is stable

  const handleMarkContacted = useCallback((id: string) => {
    updateLead(leadsRef.current, id, { status: 'contacted' }).then((res) => {
      if (res.ok) {
        setLeads((prev) => prev.map((l) => (l.id === id ? res.data : l)));
        toast.success('Lead marked as contacted');
      }
    });
  }, []); // stable: always reads from leadsRef

  const handleBulkContact = useCallback(() => {
    const ids = selectedLeads
      .filter((l) => l.status !== 'converted')
      .map((l) => l.id);
    bulkUpdateLeads(leads, ids, { status: 'contacted' }).then((res) => {
      if (res.ok) {
        const map = Object.fromEntries(res.data.map((l) => [l.id, l]));
        setLeads((prev) => prev.map((l) => map[l.id] ?? l));
        setRowSelection({});
        toast.success(`${ids.length} lead${ids.length !== 1 ? 's' : ''} marked as contacted`);
      }
    });
  }, [leads, selectedLeads]);

  const handleBulkExport = useCallback(() => {
    toast.info(`Exporting ${selectedCount} lead${selectedCount !== 1 ? 's' : ''}`, {
      description: 'CSV export will be available in the Exports section.',
    });
    setRowSelection({});
  }, [selectedCount]);

  const handleBulkReject = useCallback(() => {
    const ids = selectedLeads.map((l) => l.id);
    bulkUpdateLeads(leads, ids, { status: 'archived' }).then((res) => {
      if (res.ok) {
        const map = Object.fromEntries(res.data.map((l) => [l.id, l]));
        setLeads((prev) => prev.map((l) => map[l.id] ?? l));
        setRowSelection({});
        toast.warning(`${ids.length} lead${ids.length !== 1 ? 's' : ''} archived`);
      }
    });
  }, [leads, selectedLeads]);

  if (loadError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2">
        <AlertCircle className="h-6 w-6 text-[var(--nt-danger)]" aria-hidden="true" />
        <p className="text-sm font-medium text-[var(--nt-danger)]">Failed to load leads</p>
        <p className="text-xs text-[var(--nt-text-secondary)]">{loadError}</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* Page header */}
      <div className="flex items-center justify-between border-b border-[var(--nt-border)] px-6 py-4">
        <div>
          <h1 className="text-xl font-semibold text-[var(--nt-text-primary)]">Leads</h1>
          <p className="mt-0.5 text-sm text-[var(--nt-text-secondary)]">
            {filteredLeads.length} lead{filteredLeads.length !== 1 ? 's' : ''}
            {statusFilter && ` · ${statusFilter}`}
          </p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="border-b border-[var(--nt-border)] px-6 py-3">
        <LeadToolbar
          globalFilter={inputFilter}
          onGlobalFilterChange={handleFilterChange}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          totalCount={leads.length}
          filteredCount={filteredLeads.length}
        />
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <SkeletonBlock key={i} className="h-12 rounded" />
            ))}
          </div>
        ) : (
          <LeadTable
            data={filteredLeads}
            globalFilter={globalFilter}
            sorting={sorting}
            onSortingChange={setSorting}
            rowSelection={rowSelection}
            onRowSelectionChange={setRowSelection}
            expandedRowId={expandedRowId}
            onExpandedRowChange={setExpandedRowId}
            onMarkContacted={handleMarkContacted}
          />
        )}
      </div>

      {/* Bulk action bar — sticky floating */}
      <BulkActionBar
        selectedCount={selectedCount}
        onClearSelection={() => setRowSelection({})}
        onBulkContact={handleBulkContact}
        onBulkExport={handleBulkExport}
        onBulkReject={handleBulkReject}
      />
    </div>
  );
}
