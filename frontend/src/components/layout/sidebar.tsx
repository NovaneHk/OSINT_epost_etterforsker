'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  BarChart3,
  Users,
  Database,
  Play,
  Download,
  FileText,
  Workflow,
  Activity,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { NavItem } from './nav-item';
import { useSidebarStore } from '@/store/sidebar';

const NAV_SECTIONS = [
  {
    label: 'Main',
    items: [
      { href: '/dashboard', label: 'Dashboard', icon: BarChart3 },
      { href: '/leads', label: 'Leads', icon: Users },
      { href: '/sources', label: 'Sources', icon: Database },
      { href: '/runs', label: 'Runs', icon: Play },
    ],
  },
  {
    label: 'Output',
    items: [
      { href: '/exports', label: 'Exports', icon: Download },
      { href: '/reports', label: 'Reports', icon: FileText },
    ],
  },
  {
    label: 'Advanced',
    items: [
      { href: '/playbooks', label: 'Playbooks', icon: Workflow },
      { href: '/monitoring', label: 'Monitoring', icon: Activity },
    ],
  },
] as const;

const BOTTOM_ITEMS = [{ href: '/settings', label: 'Settings', icon: Settings }] as const;

function normalizePathname(pathname: string): string {
  return pathname.replace(/^\/(nb|en)(?=\/|$)/, '') || '/';
}

export function Sidebar() {
  const pathname = usePathname();
  const { isCollapsed, toggle } = useSidebarStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    useSidebarStore.persist.rehydrate();
    setMounted(true);
  }, []);

  // Avoid hydration mismatch: render expanded on SSR, then switch after mount
  const collapsed = mounted ? isCollapsed : false;
  const normalized = normalizePathname(pathname);

  const isActive = (href: string) => normalized.startsWith(href);

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
      className="flex h-full shrink-0 flex-col overflow-hidden border-r bg-nova-surface border-nova-border"
      aria-label="Main navigation"
    >
      {/* Brand / logo */}
      <div
        className={cn(
          'flex h-11 shrink-0 items-center border-b border-nova-border px-4',
          collapsed && 'justify-center px-0'
        )}
      >
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-nova-accent">
            <Zap className="h-4 w-4 text-white" aria-hidden />
          </div>
          {!collapsed && (
            <span className="text-sm font-semibold tracking-tight text-nova-text-primary">
              Nova Trace
            </span>
          )}
        </div>
      </div>

      {/* Nav sections */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden px-2 py-3 space-y-4">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            {!collapsed && (
              <p className="mb-1 px-3 text-[11px] font-semibold uppercase tracking-wider text-nova-text-secondary">
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavItem
                  key={item.href}
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  isActive={isActive(item.href)}
                  isCollapsed={collapsed}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom: Settings + collapse toggle */}
      <div className="shrink-0 border-t border-nova-border px-2 py-2 space-y-0.5">
        {BOTTOM_ITEMS.map((item) => (
          <NavItem
            key={item.href}
            href={item.href}
            label={item.label}
            icon={item.icon}
            isActive={isActive(item.href)}
            isCollapsed={collapsed}
          />
        ))}

        <button
          type="button"
          onClick={toggle}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={cn(
            'mt-1 flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
            'text-nova-text-secondary hover:bg-[var(--nt-surface-elevated)] hover:text-nova-text-primary',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-nova-accent focus-visible:ring-offset-1 focus-visible:ring-offset-nova-bg',
            collapsed && 'justify-center px-2'
          )}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4 shrink-0" aria-hidden />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4 shrink-0" aria-hidden />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </motion.aside>
  );
}
