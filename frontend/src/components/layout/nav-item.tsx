'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';

interface NavItemProps {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }>;
  isActive: boolean;
  isCollapsed: boolean;
  badge?: string | number;
}

export function NavItem({ href, label, icon: Icon, isActive, isCollapsed, badge }: NavItemProps) {
  return (
    <Link
      href={href}
      title={isCollapsed ? label : undefined}
      aria-label={isCollapsed ? label : undefined}
      aria-current={isActive ? 'page' : undefined}
      className={cn(
        'group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nt-accent)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--nt-bg)]',
        isCollapsed && 'justify-center px-2',
        isActive
          ? 'bg-[var(--nt-accent)]/15 text-[var(--nt-text-primary)]'
          : 'text-[var(--nt-text-secondary)] hover:bg-[var(--nt-surface-elevated)] hover:text-[var(--nt-text-primary)]'
      )}
    >
      <Icon
        className={cn(
          'h-4 w-4 shrink-0 transition-colors',
          isActive ? 'text-[var(--nt-accent)]' : 'text-[var(--nt-text-secondary)] group-hover:text-[var(--nt-text-primary)]'
        )}
        aria-hidden
      />
      {!isCollapsed && <span className="truncate">{label}</span>}
      {!isCollapsed && badge != null && (
        <span className="ml-auto font-mono text-xs tabular-nums text-[var(--nt-text-secondary)]">
          {badge}
        </span>
      )}
    </Link>
  );
}
