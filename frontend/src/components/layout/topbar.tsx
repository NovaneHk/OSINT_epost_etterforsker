'use client';

import { usePathname } from 'next/navigation';
import { Bell, Search } from 'lucide-react';
import { cn } from '@/lib/utils';

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/dashboard': 'Dashboard',
  '/leads': 'Leads',
  '/sources': 'Sources',
  '/runs': 'Runs',
  '/exports': 'Exports',
  '/reports': 'Reports',
  '/playbooks': 'Playbooks',
  '/monitoring': 'Monitoring',
  '/analytics': 'Analytics',
  '/settings': 'Settings',
  '/campaigns': 'Segments',
  '/investigations': 'Investigations',
};

function getPageTitle(pathname: string): string {
  const normalized = pathname.replace(/^\/(nb|en)(?=\/|$)/, '') || '/';
  if (PAGE_TITLES[normalized]) return PAGE_TITLES[normalized];
  const prefix = Object.keys(PAGE_TITLES).find((k) => k !== '/' && normalized.startsWith(k));
  return prefix ? PAGE_TITLES[prefix] : 'Nova Trace';
}

export function Topbar() {
  const pathname = usePathname();
  const title = getPageTitle(pathname);

  return (
    <header
      className="flex h-11 shrink-0 items-center border-b border-nova-border bg-nova-surface px-6 gap-4"
    >
      <h1 className="flex-1 text-sm font-semibold text-nova-text-primary">{title}</h1>

      <div className="flex items-center gap-1">
        <button
          type="button"
          aria-label="Search"
          className={cn(
            'flex h-8 w-8 items-center justify-center rounded-md text-nova-text-secondary transition-colors',
            'hover:bg-[var(--nt-surface-elevated)] hover:text-nova-text-primary',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-nova-accent'
          )}
        >
          <Search className="h-4 w-4" aria-hidden />
        </button>

        <button
          type="button"
          aria-label="Notifications"
          className={cn(
            'flex h-8 w-8 items-center justify-center rounded-md text-nova-text-secondary transition-colors',
            'hover:bg-[var(--nt-surface-elevated)] hover:text-nova-text-primary',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-nova-accent'
          )}
        >
          <Bell className="h-4 w-4" aria-hidden />
        </button>

        {/* Avatar placeholder */}
        <button
          type="button"
          aria-label="User menu"
          className={cn(
            'ml-1 flex h-7 w-7 items-center justify-center rounded-full bg-nova-accent text-xs font-semibold text-white',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-nova-accent focus-visible:ring-offset-2 focus-visible:ring-offset-nova-surface'
          )}
        >
          NT
        </button>
      </div>
    </header>
  );
}
