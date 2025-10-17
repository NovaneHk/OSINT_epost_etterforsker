'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
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
  Zap,
  ChevronRight,
} from 'lucide-react';

export interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  shortcut?: string;
  badge?: string | number;
  description?: string;
}

const navigation: NavItem[] = [
  {
    href: '/',
    label: 'Dashboard',
    icon: BarChart3,
    shortcut: 'G D',
    description: 'Oversikt og KPI-er',
  },
  {
    href: '/leads',
    label: 'Leads',
    icon: Users,
    shortcut: 'G L',
    description: 'Administrer leads',
  },
  {
    href: '/sources',
    label: 'Kilder',
    icon: Database,
    shortcut: 'G S',
    description: 'Datakilde-konfigurasjon',
  },
  {
    href: '/runs',
    label: 'Kjøringer',
    icon: Play,
    shortcut: 'G R',
    description: 'OSINT-søk og analyser',
  },
  {
    href: '/campaigns',
    label: 'Segmenter',
    icon: Search,
    shortcut: 'G C',
    description: 'Målgruppe-segmentering',
  },
  {
    href: '/exports',
    label: 'Eksporter',
    icon: Download,
    shortcut: 'G E',
    description: 'Data-eksport og rapporter',
  },
  {
    href: '/playbooks',
    label: 'Playbooks',
    icon: Workflow,
    shortcut: 'G P',
    description: 'Automatiserte arbeidsflyter',
  },
  {
    href: '/settings',
    label: 'Innstillinger',
    icon: Settings,
    shortcut: 'G T',
    description: 'System-konfigurasjon',
  },
];

interface SidebarNavProps {
  className?: string;
}

const sidebarVariants = {
  open: {
    x: 0,
    transition: {
      type: 'spring' as const,
      stiffness: 300,
      damping: 30,
    },
  },
  closed: {
    x: '-100%',
    transition: {
      type: 'spring' as const,
      stiffness: 300,
      damping: 30,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: {
      delay: i * 0.05,
      duration: 0.3,
      ease: [0.4, 0.0, 0.2, 1] as const,
    },
  }),
};

export function SidebarNav({ className }: SidebarNavProps) {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  return (
    <>
      {/* Mobile menu button */}
      <div className="flex items-center justify-between p-4 lg:hidden bg-white/80 dark:bg-dark-bg/80 backdrop-blur-md border-b border-light-border dark:border-dark-border">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center space-x-2"
        >
          <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-br from-osint-primary to-osint-primary-dark rounded-lg">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <span className="text-lg font-bold bg-gradient-to-r from-osint-primary to-osint-secondary bg-clip-text text-transparent">
            OSINT Pro
          </span>
        </motion.div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="inline-flex items-center justify-center rounded-lg p-2 text-light-text-secondary dark:text-dark-text-secondary hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover transition-colors"
          aria-expanded="false"
        >
          <span className="sr-only">Åpne hovedmeny</span>
          <AnimatePresence mode="wait">
            {isMobileMenuOpen ? (
              <motion.div
                key="close"
                initial={{ rotate: -90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: 90, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <X className="h-6 w-6" aria-hidden="true" />
              </motion.div>
            ) : (
              <motion.div
                key="menu"
                initial={{ rotate: 90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: -90, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Menu className="h-6 w-6" aria-hidden="true" />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.button>
      </div>

      {/* Desktop sidebar */}
      <motion.nav
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className={cn(
          'hidden h-full flex-col border-r border-light-border dark:border-dark-border bg-white/80 dark:bg-dark-bg/80 backdrop-blur-md lg:flex',
          className
        )}
      >
        {/* Logo */}
        <motion.div
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1, duration: 0.5 }}
          className="flex h-16 items-center border-b border-light-border dark:border-dark-border px-6"
        >
          <Link href="/" className="flex items-center space-x-3 group">
            <motion.div
              whileHover={{ scale: 1.1, rotate: 5 }}
              className="flex items-center justify-center w-8 h-8 bg-gradient-to-br from-osint-primary to-osint-primary-dark rounded-lg shadow-lg"
            >
              <Zap className="h-4 w-4 text-white" />
            </motion.div>
            <span className="text-xl font-bold bg-gradient-to-r from-osint-primary to-osint-secondary bg-clip-text text-transparent">
              OSINT Pro
            </span>
          </Link>
        </motion.div>

        {/* Navigation Links */}
        <div className="flex-1 space-y-2 p-4 overflow-y-auto custom-scrollbar">
          {navigation.map((item, index) => {
            const isActive = pathname === item.href;
            return (
              <motion.div
                key={item.href}
                custom={index}
                initial="hidden"
                animate="visible"
                variants={itemVariants}
                onHoverStart={() => setHoveredItem(item.href)}
                onHoverEnd={() => setHoveredItem(null)}
              >
                <Link
                  href={item.href}
                  className={cn(
                    'group relative flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 ease-out',
                    isActive
                      ? 'bg-gradient-to-r from-osint-primary to-osint-primary-dark text-white shadow-lg shadow-osint-primary/25'
                      : 'text-light-text-secondary dark:text-dark-text-secondary hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover hover:text-light-text dark:hover:text-dark-text'
                  )}
                >
                  {/* Active indicator */}
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 bg-gradient-to-r from-osint-primary to-osint-primary-dark rounded-xl"
                      initial={false}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  )}

                  <div className="relative flex items-center space-x-3 z-10">
                    <motion.div
                      whileHover={{ scale: 1.1 }}
                      transition={{ type: 'spring', stiffness: 400, damping: 10 }}
                    >
                      <item.icon
                        className={cn(
                          'h-5 w-5 transition-colors',
                          isActive ? 'text-white' : 'text-light-text-muted dark:text-dark-text-muted group-hover:text-osint-primary'
                        )}
                      />
                    </motion.div>
                    <span className="relative">{item.label}</span>
                  </div>

                  <div className="relative flex items-center space-x-2 z-10">
                    {item.shortcut && (
                      <motion.span
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{
                          opacity: hoveredItem === item.href ? 1 : 0.6,
                          scale: hoveredItem === item.href ? 1 : 0.8
                        }}
                        className={cn(
                          'hidden text-xs font-mono xl:block px-2 py-1 rounded-md',
                          isActive
                            ? 'bg-white/20 text-white'
                            : 'bg-light-bg-secondary dark:bg-dark-bg-secondary text-light-text-muted dark:text-dark-text-muted'
                        )}
                      >
                        {item.shortcut}
                      </motion.span>
                    )}
                    {item.badge && (
                      <motion.span
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="flex items-center justify-center min-w-[20px] h-5 rounded-full bg-osint-secondary text-white text-xs font-medium"
                      >
                        {item.badge}
                      </motion.span>
                    )}
                    <motion.div
                      animate={{
                        x: hoveredItem === item.href ? 2 : 0,
                        opacity: hoveredItem === item.href ? 1 : 0
                      }}
                      transition={{ type: 'spring', stiffness: 400, damping: 20 }}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </motion.div>
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>

        {/* Footer */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="border-t border-light-border dark:border-dark-border p-4 space-y-3"
        >
          <div className="flex items-center space-x-3">
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="h-2 w-2 rounded-full bg-osint-success"
            />
            <span className="text-sm text-light-text-secondary dark:text-dark-text-secondary">
              System aktiv
            </span>
          </div>
          <div className="text-xs text-light-text-muted dark:text-dark-text-muted">
            Versjon 1.0.0 • Premium
          </div>
        </motion.div>
      </motion.nav>

      {/* Mobile menu overlay */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
              onClick={() => setIsMobileMenuOpen(false)}
            />
            <motion.nav
              variants={sidebarVariants}
              initial="closed"
              animate="open"
              exit="closed"
              className="fixed inset-y-0 left-0 z-50 w-80 bg-white/95 dark:bg-dark-bg/95 backdrop-blur-md shadow-2xl lg:hidden border-r border-light-border dark:border-dark-border"
            >
              <div className="flex h-16 items-center justify-between border-b border-light-border dark:border-dark-border px-6">
                <Link href="/" className="flex items-center space-x-3">
                  <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-br from-osint-primary to-osint-primary-dark rounded-lg">
                    <Zap className="h-4 w-4 text-white" />
                  </div>
                  <span className="text-xl font-bold bg-gradient-to-r from-osint-primary to-osint-secondary bg-clip-text text-transparent">
                    OSINT Pro
                  </span>
                </Link>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="rounded-lg p-2 text-light-text-secondary dark:text-dark-text-secondary hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover"
                >
                  <X className="h-5 w-5" />
                </motion.button>
              </div>
              <div className="space-y-2 p-4 overflow-y-auto custom-scrollbar">
                {navigation.map((item, index) => {
                  const isActive = pathname === item.href;
                  return (
                    <motion.div
                      key={item.href}
                      custom={index}
                      initial="hidden"
                      animate="visible"
                      variants={itemVariants}
                    >
                      <Link
                        href={item.href}
                        onClick={() => setIsMobileMenuOpen(false)}
                        className={cn(
                          'group flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200',
                          isActive
                            ? 'bg-gradient-to-r from-osint-primary to-osint-primary-dark text-white shadow-lg'
                            : 'text-light-text-secondary dark:text-dark-text-secondary hover:bg-light-surface-hover dark:hover:bg-dark-surface-hover'
                        )}
                      >
                        <div className="flex items-center space-x-3">
                          <item.icon className="h-5 w-5" />
                          <div>
                            <div>{item.label}</div>
                            {item.description && (
                              <div className={cn(
                                'text-xs mt-0.5',
                                isActive ? 'text-white/80' : 'text-light-text-muted dark:text-dark-text-muted'
                              )}>
                                {item.description}
                              </div>
                            )}
                          </div>
                        </div>
                        {item.shortcut && (
                          <span className={cn(
                            'text-xs font-mono px-2 py-1 rounded-md',
                            isActive
                              ? 'bg-white/20 text-white'
                              : 'bg-light-bg-secondary dark:bg-dark-bg-secondary text-light-text-muted dark:text-dark-text-muted'
                          )}>
                            {item.shortcut}
                          </span>
                        )}
                      </Link>
                    </motion.div>
                  );
                })}
              </div>
            </motion.nav>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
