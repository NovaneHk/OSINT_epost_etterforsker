'use client';

import { usePathname } from 'next/navigation';
import { SidebarNav } from '@/components/layout/sidebar-nav';
import { TopNav } from '@/components/layout/top-nav';
import { FloatingActions } from '@/components/layout/floating-actions';
import { MobileNav } from '@/components/layout/mobile-nav';

interface AppShellProps {
  children: React.ReactNode;
}

function isAuthRoute(pathname: string): boolean {
  const normalizedPath = pathname.replace(/^\/(nb|en)(?=\/|$)/, '') || '/';
  return normalizedPath === '/login' || normalizedPath === '/forgot-password' || normalizedPath === '/register';
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();

  if (isAuthRoute(pathname)) {
    return children;
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="flex h-screen">
        <aside className="hidden w-64 border-r border-border bg-card lg:block">
          <SidebarNav />
        </aside>

        <div className="flex flex-1 flex-col overflow-hidden">
          <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <TopNav />
          </header>

          <main className="flex-1 overflow-auto pb-16 lg:pb-0">
            <div className="container mx-auto px-4 py-6">
              {children}
            </div>
          </main>
        </div>
      </div>

      <MobileNav />
      <FloatingActions />
    </div>
  );
}