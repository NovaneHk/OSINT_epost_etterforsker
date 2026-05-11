'use client';

import { Plus, Upload, Download, Play } from 'lucide-react';
import Link from 'next/link';

const ACTIONS = [
  {
    icon: Plus,
    label: 'New Lead',
    description: 'Add a lead manually',
    href: '/leads',
    color: 'var(--nt-accent)',
  },
  {
    icon: Play,
    label: 'Start Run',
    description: 'Execute a source scan',
    href: '/runs',
    color: 'var(--nt-success)',
  },
  {
    icon: Upload,
    label: 'Import CSV',
    description: 'Upload lead data',
    href: '/sources',
    color: 'var(--nt-warning)',
  },
  {
    icon: Download,
    label: 'Export',
    description: 'Download leads',
    href: '/exports',
    color: 'var(--nt-ai)',
  },
] as const;

export function QuickActions() {
  return (
    <div className="rounded-lg border border-[var(--nt-border)] bg-[var(--nt-surface)]">
      <div className="border-b border-[var(--nt-border)] px-5 py-4">
        <h2 className="text-sm font-semibold text-[var(--nt-text-primary)]">
          Quick Actions
        </h2>
      </div>
      <div className="grid grid-cols-2 gap-px bg-[var(--nt-border)] overflow-hidden rounded-b-lg">
        {ACTIONS.map(({ icon: Icon, label, description, href, color }) => (
          <Link
            key={label}
            href={href}
            className="flex flex-col gap-1 bg-[var(--nt-surface)] px-4 py-4 transition-colors hover:bg-[var(--nt-surface-elevated)] focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--nt-accent)]"
          >
            <div
              className="flex h-8 w-8 items-center justify-center rounded-md"
              style={{ backgroundColor: `color-mix(in srgb, ${color} 15%, transparent)` }}
            >
              <Icon
                className="h-4 w-4"
                style={{ color }}
                aria-hidden="true"
              />
            </div>
            <span className="mt-1 text-sm font-medium text-[var(--nt-text-primary)]">
              {label}
            </span>
            <span className="text-xs text-[var(--nt-text-secondary)]">
              {description}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
