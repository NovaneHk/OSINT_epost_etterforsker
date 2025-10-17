'use client';

import { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import { motion, AnimatePresence } from 'framer-motion';
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
  Zap,
  Activity,
  Shield,
  Sparkles,
  ChevronDown,
  Clock,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export function TopNav() {
  const { theme, setTheme } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [notifications] = useState([
    {
      id: 1,
      title: 'Ny kjøring fullført',
      message: '1,234 leads funnet fra LinkedIn',
      time: '2 min siden',
      unread: true,
      type: 'success',
      icon: TrendingUp
    },
    {
      id: 2,
      title: 'Export klar',
      message: 'CSV-fil med 856 leads er klar for nedlasting',
      time: '10 min siden',
      unread: true,
      type: 'info',
      icon: Download
    },
    {
      id: 3,
      title: 'Systemoppdatering',
      message: 'OSINT Pro v1.0.1 er tilgjengelig',
      time: '1 time siden',
      unread: false,
      type: 'update',
      icon: Sparkles
    },
  ]);

  const unreadCount = notifications.filter(n => n.unread).length;

  useEffect(() => {
    setMounted(true);
  }, []);

  const searchVariants = {
    focused: {
      scale: 1.02,
      boxShadow: '0 0 0 2px hsl(var(--osint-primary))',
      transition: { type: 'spring' as const, stiffness: 300, damping: 20 }
    },
    unfocused: {
      scale: 1,
      boxShadow: '0 0 0 0px transparent',
      transition: { type: 'spring' as const, stiffness: 300, damping: 20 }
    }
  };

  const buttonVariants = {
    hover: { scale: 1.05, transition: { type: 'spring' as const, stiffness: 400, damping: 10 } },
    tap: { scale: 0.95 }
  };

  const notificationVariants = {
    hidden: { opacity: 0, y: -10, scale: 0.95 },
    visible: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: -10, scale: 0.95 }
  };

  if (!mounted) {
    return null;
  }

  return (
    <motion.div
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="flex h-16 items-center justify-between px-4 lg:px-6 bg-white/80 dark:bg-dark-bg/80 backdrop-blur-md border-b border-light-border dark:border-dark-border"
    >
      {/* Left side - Search */}
      <div className="flex items-center space-x-4">
        <motion.div
          className="relative"
          variants={searchVariants}
          animate={isSearchFocused ? 'focused' : 'unfocused'}
        >
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-light-text-muted dark:text-dark-text-muted" />
          <Input
            type="search"
            placeholder="Søk i leads, kilder, kjøringer... (Ctrl+K)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setIsSearchFocused(true)}
            onBlur={() => setIsSearchFocused(false)}
            className="w-64 pl-10 pr-16 lg:w-96 bg-light-bg-secondary dark:bg-dark-bg-secondary border-light-border dark:border-dark-border focus:border-osint-primary dark:focus:border-osint-primary transition-all duration-200"
          />
          <motion.div
            className="absolute right-3 top-1/2 -translate-y-1/2"
            animate={{
              opacity: isSearchFocused ? 0.8 : 0.6,
              scale: isSearchFocused ? 1.1 : 1
            }}
          >
            <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-light-bg dark:bg-dark-bg-secondary px-1.5 font-mono text-[10px] font-medium text-light-text-muted dark:text-dark-text-muted opacity-100">
              <Command className="h-3 w-3" />K
            </kbd>
          </motion.div>
        </motion.div>
      </div>

      {/* Right side - Actions and User */}
      <div className="flex items-center space-x-3">
        {/* Quick Actions */}
        <div className="hidden md:flex items-center space-x-2">
          <motion.div variants={buttonVariants} whileHover="hover" whileTap="tap">
            <Button
              size="sm"
              variant="outline"
              className="gap-2 border-light-border dark:border-dark-border hover:bg-osint-primary/10 hover:border-osint-primary hover:text-osint-primary transition-all duration-200"
            >
              <Play className="h-4 w-4" />
              Start kjøring
            </Button>
          </motion.div>
          <motion.div variants={buttonVariants} whileHover="hover" whileTap="tap">
            <Button
              size="sm"
              variant="outline"
              className="gap-2 border-light-border dark:border-dark-border hover:bg-osint-secondary/10 hover:border-osint-secondary hover:text-osint-secondary transition-all duration-200"
            >
              <Download className="h-4 w-4" />
              Eksporter
            </Button>
          </motion.div>
          <motion.div variants={buttonVariants} whileHover="hover" whileTap="tap">
            <Button
              size="sm"
              className="gap-2 bg-gradient-to-r from-osint-primary to-osint-primary-dark hover:from-osint-primary-dark hover:to-osint-primary shadow-lg shadow-osint-primary/25 transition-all duration-200"
            >
              <Plus className="h-4 w-4" />
              Ny
            </Button>
          </motion.div>
        </div>

        {/* System Status Indicator */}
        <motion.div
          className="hidden lg:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-osint-success/10 border border-osint-success/20"
          animate={{ scale: [1, 1.02, 1] }}
          transition={{ duration: 3, repeat: Infinity }}
        >
          <motion.div
            animate={{ scale: [1, 1.3, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="h-2 w-2 rounded-full bg-osint-success"
          />
          <span className="text-xs font-medium text-osint-success">System Online</span>
        </motion.div>

        {/* Theme Toggle */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <motion.div variants={buttonVariants} whileHover="hover" whileTap="tap">
              <Button
                variant="ghost"
                size="icon"
                className="relative hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover"
              >
                <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                <span className="sr-only">Bytt tema</span>
              </Button>
            </motion.div>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="bg-white/95 dark:bg-dark-bg/95 backdrop-blur-md border-light-border dark:border-dark-border">
            <DropdownMenuItem onClick={() => setTheme('light')} className="hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover">
              <Sun className="mr-2 h-4 w-4" />
              Lys
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme('dark')} className="hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover">
              <Moon className="mr-2 h-4 w-4" />
              Mørk
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme('system')} className="hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover">
              <Monitor className="mr-2 h-4 w-4" />
              System
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <motion.div variants={buttonVariants} whileHover="hover" whileTap="tap">
              <Button
                variant="ghost"
                size="icon"
                className="relative hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover"
              >
                <Bell className="h-4 w-4" />
                <AnimatePresence>
                  {unreadCount > 0 && (
                    <motion.div
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0, opacity: 0 }}
                      className="absolute -top-1 -right-1"
                    >
                      <Badge
                        variant="destructive"
                        className="h-5 w-5 rounded-full p-0 text-xs bg-gradient-to-r from-osint-error to-red-500 border-0 shadow-lg"
                      >
                        {unreadCount}
                      </Badge>
                    </motion.div>
                  )}
                </AnimatePresence>
                <span className="sr-only">Varslinger</span>
              </Button>
            </motion.div>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="w-96 bg-white/95 dark:bg-dark-bg/95 backdrop-blur-md border-light-border dark:border-dark-border"
          >
            <DropdownMenuLabel className="flex items-center justify-between">
              <span>Varslinger</span>
              {unreadCount > 0 && (
                <Badge variant="secondary" className="bg-osint-primary/10 text-osint-primary">
                  {unreadCount} nye
                </Badge>
              )}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <AnimatePresence>
              {notifications.length === 0 ? (
                <motion.div
                  variants={notificationVariants}
                  initial="hidden"
                  animate="visible"
                  className="p-6 text-center text-sm text-light-text-muted dark:text-dark-text-muted"
                >
                  <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  Ingen nye varslinger
                </motion.div>
              ) : (
                notifications.map((notification, index) => (
                  <motion.div
                    key={notification.id}
                    variants={notificationVariants}
                    initial="hidden"
                    animate="visible"
                    exit="exit"
                    transition={{ delay: index * 0.05 }}
                  >
                    <DropdownMenuItem className="flex items-start space-x-3 p-4 hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover">
                      <div className={cn(
                        "flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0",
                        notification.type === 'success' && "bg-osint-success/10 text-osint-success",
                        notification.type === 'info' && "bg-osint-info/10 text-osint-info",
                        notification.type === 'update' && "bg-osint-warning/10 text-osint-warning"
                      )}>
                        <notification.icon className="h-4 w-4" />
                      </div>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-start justify-between">
                          <p className="text-sm font-medium text-light-text dark:text-dark-text">
                            {notification.title}
                          </p>
                          {notification.unread && (
                            <motion.div
                              animate={{ scale: [1, 1.2, 1] }}
                              transition={{ duration: 2, repeat: Infinity }}
                              className="h-2 w-2 rounded-full bg-osint-primary flex-shrink-0 ml-2 mt-1"
                            />
                          )}
                        </div>
                        <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary">
                          {notification.message}
                        </p>
                        <div className="flex items-center space-x-1 text-xs text-light-text-muted dark:text-dark-text-muted">
                          <Clock className="h-3 w-3" />
                          <span>{notification.time}</span>
                        </div>
                      </div>
                    </DropdownMenuItem>
                  </motion.div>
                ))
              )}
            </AnimatePresence>
            {notifications.length > 0 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-center p-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full hover:bg-osint-primary/10 hover:text-osint-primary"
                  >
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
            <motion.div variants={buttonVariants} whileHover="hover" whileTap="tap">
              <Button
                variant="ghost"
                className="relative h-10 w-auto rounded-lg px-3 hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover"
              >
                <div className="flex items-center space-x-3">
                  <Avatar className="h-8 w-8 ring-2 ring-osint-primary/20">
                    <AvatarImage src="/placeholder-avatar.jpg" alt="@user" />
                    <AvatarFallback className="bg-gradient-to-br from-osint-primary to-osint-secondary text-white font-semibold">
                      OA
                    </AvatarFallback>
                  </Avatar>
                  <div className="hidden md:flex flex-col items-start">
                    <span className="text-sm font-medium text-light-text dark:text-dark-text">
                      OSINT Analytiker
                    </span>
                    <div className="flex items-center space-x-1">
                      <Shield className="h-3 w-3 text-osint-success" />
                      <span className="text-xs text-light-text-muted dark:text-dark-text-muted">
                        Premium
                      </span>
                    </div>
                  </div>
                  <ChevronDown className="h-4 w-4 text-light-text-muted dark:text-dark-text-muted" />
                </div>
              </Button>
            </motion.div>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-64 bg-white/95 dark:bg-dark-bg/95 backdrop-blur-md border-light-border dark:border-dark-border"
            align="end"
            forceMount
          >
            <DropdownMenuLabel className="font-normal">
              <div className="flex items-center space-x-3">
                <Avatar className="h-10 w-10 ring-2 ring-osint-primary/20">
                  <AvatarImage src="/placeholder-avatar.jpg" alt="@user" />
                  <AvatarFallback className="bg-gradient-to-br from-osint-primary to-osint-secondary text-white font-semibold">
                    OA
                  </AvatarFallback>
                </Avatar>
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none text-light-text dark:text-dark-text">
                    OSINT Analytiker
                  </p>
                  <p className="text-xs leading-none text-light-text-muted dark:text-dark-text-muted">
                    analyst@osint.no
                  </p>
                  <div className="flex items-center space-x-1 mt-1">
                    <Sparkles className="h-3 w-3 text-osint-warning" />
                    <span className="text-xs text-osint-warning font-medium">Premium Plan</span>
                  </div>
                </div>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover">
              <User className="mr-3 h-4 w-4" />
              <span>Profil</span>
            </DropdownMenuItem>
            <DropdownMenuItem className="hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover">
              <Settings className="mr-3 h-4 w-4" />
              <span>Innstillinger</span>
            </DropdownMenuItem>
            <DropdownMenuItem className="hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover">
              <Activity className="mr-3 h-4 w-4" />
              <span>Aktivitetslogg</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-osint-error hover:bg-osint-error/10 hover:text-osint-error">
              <LogOut className="mr-3 h-4 w-4" />
              <span>Logg ut</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </motion.div>
  );
}
