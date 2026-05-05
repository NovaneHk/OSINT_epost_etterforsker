'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Users, Search, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/leads', label: 'Leads', icon: Users },
    { href: '/investigations', label: 'Søk', icon: Search },
    { href: '/settings', label: 'Innstillinger', icon: Settings },
];

export function MobileNav() {
    const pathname = usePathname();

    return (
        <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 lg:hidden">
            <div className="flex items-center justify-around px-2 py-1">
                {navItems.map(({ href, label, icon: Icon }) => {
                    const isActive = pathname === href || pathname.startsWith(href + '/');
                    return (
                        <Link
                            key={href}
                            href={href}
                            className={cn(
                                'flex flex-col items-center gap-0.5 px-3 py-2 rounded-md text-xs transition-colors',
                                isActive
                                    ? 'text-primary font-semibold'
                                    : 'text-muted-foreground hover:text-foreground'
                            )}
                        >
                            <Icon className={cn('h-5 w-5', isActive && 'text-primary')} />
                            <span>{label}</span>
                        </Link>
                    );
                })}
            </div>
        </nav>
    );
}
