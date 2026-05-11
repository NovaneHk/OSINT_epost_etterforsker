'use client';

import { usePathname } from 'next/navigation';
import { Sidebar } from '@/components/layout/sidebar';
import { Topbar } from '@/components/layout/topbar';

interface AppShellProps {
  children: React.ReactNode;
}

const AUTH_ROUTES = new Set(['/login', '/register', '/forgot-password']);

function isAuthRoute(pathname: string): boolean {
  const normalized = pathname.replace(/^\/(nb|en)(?=\/|$)/, '') || '/';
  return AUTH_ROUTES.has(normalized);
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();

  if (isAuthRoute(pathname)) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-nova-bg">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Topbar />

        <main className="flex-1 overflow-auto bg-nova-bg">
          <div className="mx-auto max-w-[1400px] px-8 py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}