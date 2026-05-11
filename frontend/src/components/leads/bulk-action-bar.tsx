'use client';

import { Mail, Download, XCircle, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';

interface BulkActionBarProps {
  selectedCount: number;
  onClearSelection: () => void;
  onBulkContact: () => void;
  onBulkExport: () => void;
  onBulkReject: () => void;
}

export function BulkActionBar({
  selectedCount,
  onClearSelection,
  onBulkContact,
  onBulkExport,
  onBulkReject,
}: BulkActionBarProps) {
  return (
    <AnimatePresence>
      {selectedCount > 0 && (
        <motion.div
          data-testid="batch-actions"
          initial={{ y: 80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 80, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
          className="fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-xl border border-[var(--nt-border)] bg-[var(--nt-surface-elevated)] px-4 py-3 shadow-2xl"
          role="toolbar"
          aria-label="Bulk actions"
        >
          {/* Count */}
          <span
            data-testid="selected-count"
            className="rounded-full bg-[var(--nt-accent)]/15 px-2.5 py-0.5 text-xs font-semibold text-[var(--nt-accent)]"
          >
            {selectedCount} selected
          </span>

          <div className="h-4 w-px bg-[var(--nt-border)]" aria-hidden="true" />

          {/* Mark contacted */}
          <button
            data-testid="bulk-contact"
            onClick={onBulkContact}
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-[var(--nt-text-primary)] transition-colors hover:bg-[var(--nt-surface)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)]"
          >
            <Mail className="h-3.5 w-3.5" aria-hidden="true" />
            Mark contacted
          </button>

          {/* Export */}
          <button
            data-testid="export-selected"
            onClick={onBulkExport}
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-[var(--nt-text-primary)] transition-colors hover:bg-[var(--nt-surface)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)]"
          >
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            Export
          </button>

          {/* Reject */}
          <button
            data-testid="delete-selected"
            onClick={onBulkReject}
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-[var(--nt-danger)] transition-colors hover:bg-[var(--nt-danger)]/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-danger)]"
          >
            <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
            Reject
          </button>

          <div className="h-4 w-px bg-[var(--nt-border)]" aria-hidden="true" />

          {/* Clear */}
          <button
            onClick={onClearSelection}
            aria-label="Clear selection"
            className="rounded-md p-1.5 text-[var(--nt-text-secondary)] transition-colors hover:bg-[var(--nt-surface)] hover:text-[var(--nt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)]"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
