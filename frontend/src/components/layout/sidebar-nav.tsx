'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  BarChart3,
  Users,
  Database,
  Play,
  Workflow,
  Download,
  Settings,
  Menu,
  X,
  Search,
} from 'lucide-react';

export interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  shortcut?: string;
  badge?: string | number;
}

const navigation: NavItem[] = [
  {
    href: '/',
    label: 'Dashboard',
    icon: BarChart3,
    shortcut: 'G D',
  },
  {
    href: '/leads',
    label: 'Leads',
    icon: Users,
    shortcut: 'G L',
  },
  {
    href: '/sources',
    label: 'Kilder',
    icon: Database,
    shortcut: 'G S',
  },
  {
    href: '/runs',
    label: 'Kjøringer',
    icon: Play,
    shortcut: 'G R',
  },
  {
    href: '/campaigns',
    label: 'Segmenter',
    icon: Search,
    shortcut: 'G C',
  },
  {
    href: '/exports',
    label: 'Eksporter',
    icon: Download,
    shortcut: 'G E',
  },
  {
    href: '/playbooks',
    label: 'Playbooks',
    icon: Workflow,
    shortcut: 'G P',
  },
  {
    href: '/settings',
    label: 'Innstillinger',
    icon: Settings,
    shortcut: 'G T',
  },
];

interface SidebarNavProps {
  className?: string;
}

export function SidebarNav({ className }: SidebarNavProps) {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <>
      {/* Mobile menu button */}
      <div className="flex items-center justify-between p-4 lg:hidden">
        <h1 className="text-lg font-semibold">OSINT</h1>
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="inline-flex items-center justify-center rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          aria-expanded="false"
        >
          <span className="sr-only">Åpne hovedmeny</span>
          {isMobileMenuOpen ? (
            <X className="h-6 w-6" aria-hidden="true" />
          ) : (
            <Menu className="h-6 w-6" aria-hidden="true" />
          )}
        </button>
      </div>

      {/* Desktop sidebar */}
      <nav
        className={cn(
          'hidden h-full flex-col border-r bg-card lg:flex',
          className
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center border-b px-6">
          <Link href="/" className="flex items-center space-x-2">
            <BarChart3 className="h-6 w-6 text-primary" />
            <span className="text-lg font-bold">OSINT</span>
          </Link>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 space-y-1 p-4">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'group flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                <div className="flex items-center space-x-3">
                  <item.icon
                    className={cn(
                      'h-4 w-4',
                      isActive ? 'text-primary-foreground' : 'text-muted-foreground'
                    )}
                  />
                  <span>{item.label}</span>
                </div>
                {item.shortcut && (
                  <span className="hidden text-xs opacity-60 group-hover:opacity-100 xl:block">
                    {item.shortcut}
                  </span>
                )}
                {item.badge && (
                  <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>

        {/* Footer */}
        <div className="border-t p-4">
          <div className="flex items-center space-x-2 text-xs text-muted-foreground">
            <div className="h-2 w-2 rounded-full bg-green-500"></div>
            <span>System aktiv</span>
          </div>
          <div className="mt-2 text-xs text-muted-foreground">
            Versjon 1.0.0
          </div>
        </div>
      </nav>

      {/* Mobile menu overlay */}
      {isMobileMenuOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          <nav className="fixed inset-y-0 left-0 z-50 w-64 bg-card shadow-lg lg:hidden">
            <div className="flex h-16 items-center justify-between border-b px-6">
              <Link href="/" className="flex items-center space-x-2">
                <BarChart3 className="h-6 w-6 text-primary" />
                <span className="text-lg font-bold">OSINT</span>
              </Link>
              <button
                onClick={() => setIsMobileMenuOpen(false)}
                className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="space-y-1 p-4">
              {navigation.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={cn(
                      'group flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                    )}
                  >
                    <div className="flex items-center space-x-3">
                      <item.icon className="h-4 w-4" />
                      <span>{item.label}</span>
                    </div>
                    {item.shortcut && (
                      <span className="text-xs opacity-60">{item.shortcut}</span>
                    )}
                  </Link>
                );
              })}
            </div>
          </nav>
        </>
      )}
    </>
  );
}