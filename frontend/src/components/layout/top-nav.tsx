'use client';

import { useState } from 'react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import {
  Search,
  Bell,
  Settings,
  User,
  LogOut,
  Moon,
  Sun,
  Monitor,
  Command,
  Play,
  Download,
  Plus,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export function TopNav() {
  const { theme, setTheme } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [notifications] = useState([
    { id: 1, title: 'Ny kjøring fullført', message: '1,234 leads funnet', time: '2 min siden', unread: true },
    { id: 2, title: 'Export klar', message: 'CSV-fil er klar for nedlasting', time: '10 min siden', unread: true },
    { id: 3, title: 'Systemoppdatering', message: 'Versjon 1.0.1 er tilgjengelig', time: '1 time siden', unread: false },
  ]);

  const unreadCount = notifications.filter(n => n.unread).length;

  return (
    <div className="flex h-16 items-center justify-between px-4 lg:px-6">
      {/* Left side - Search */}
      <div className="flex items-center space-x-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Søk i leads, kilder, kjøringer... (Ctrl+K)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-64 pl-10 pr-4 lg:w-80"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
              <Command className="h-3 w-3" />K
            </kbd>
          </div>
        </div>
      </div>

      {/* Right side - Actions and User */}
      <div className="flex items-center space-x-4">
        {/* Quick Actions */}
        <div className="hidden md:flex items-center space-x-2">
          <Button size="sm" variant="outline" className="gap-2">
            <Play className="h-4 w-4" />
            Start kjøring
          </Button>
          <Button size="sm" variant="outline" className="gap-2" data-shortcut="export">
            <Download className="h-4 w-4" />
            Eksporter
          </Button>
          <Button size="sm" className="gap-2">
            <Plus className="h-4 w-4" />
            Ny
          </Button>
        </div>

        {/* Theme Toggle */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              <span className="sr-only">Bytt tema</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setTheme('light')}>
              <Sun className="mr-2 h-4 w-4" />
              Lys
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme('dark')}>
              <Moon className="mr-2 h-4 w-4" />
              Mørk
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme('system')}>
              <Monitor className="mr-2 h-4 w-4" />
              System
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-4 w-4" />
              {unreadCount > 0 && (
                <Badge variant="destructive" className="absolute -top-2 -right-2 h-5 w-5 rounded-full p-0 text-xs">
                  {unreadCount}
                </Badge>
              )}
              <span className="sr-only">Varslinger</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel>Varslinger</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {notifications.length === 0 ? (
              <div className="p-4 text-center text-sm text-muted-foreground">
                Ingen nye varslinger
              </div>
            ) : (
              notifications.map((notification) => (
                <DropdownMenuItem key={notification.id} className="flex flex-col items-start space-y-1 p-4">
                  <div className="flex w-full items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <p className="text-sm font-medium">{notification.title}</p>
                        {notification.unread && (
                          <div className="h-2 w-2 rounded-full bg-blue-500" />
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">{notification.message}</p>
                      <p className="text-xs text-muted-foreground">{notification.time}</p>
                    </div>
                  </div>
                </DropdownMenuItem>
              ))
            )}
            {notifications.length > 0 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-center">
                  <Button variant="ghost" size="sm" className="w-full">
                    Se alle varslinger
                  </Button>
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-8 w-8 rounded-full">
              <Avatar className="h-8 w-8">
                <AvatarImage src="/placeholder-avatar.jpg" alt="@user" />
                <AvatarFallback>
                  <User className="h-4 w-4" />
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">OSINT Analytiker</p>
                <p className="text-xs leading-none text-muted-foreground">
                  analyst@osint.no
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              <span>Profil</span>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              <span>Innstillinger</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-red-600">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Logg ut</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}