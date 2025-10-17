'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Plus,
  Play,
  Download,
  Search,
  Users,
  Database,
  Zap,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface FloatingAction {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  shortcut?: string;
  onClick: () => void;
}

const quickActions: FloatingAction[] = [
  {
    id: 'new-search',
    label: 'Ny OSINT-søk',
    icon: Search,
    color: 'from-osint-primary to-osint-primary-dark',
    shortcut: 'Ctrl+N',
    onClick: () => console.log('New search'),
  },
  {
    id: 'start-run',
    label: 'Start kjøring',
    icon: Play,
    color: 'from-osint-success to-green-600',
    shortcut: 'Ctrl+R',
    onClick: () => console.log('Start run'),
  },
  {
    id: 'add-leads',
    label: 'Legg til leads',
    icon: Users,
    color: 'from-osint-secondary to-green-500',
    shortcut: 'Ctrl+L',
    onClick: () => console.log('Add leads'),
  },
  {
    id: 'export-data',
    label: 'Eksporter data',
    icon: Download,
    color: 'from-osint-info to-blue-600',
    shortcut: 'Ctrl+E',
    onClick: () => console.log('Export data'),
  },
  {
    id: 'add-source',
    label: 'Ny datakilde',
    icon: Database,
    color: 'from-osint-warning to-orange-600',
    shortcut: 'Ctrl+S',
    onClick: () => console.log('Add source'),
  },
];

export function FloatingActions() {
  const [isOpen, setIsOpen] = useState(false);
  const [hoveredAction, setHoveredAction] = useState<string | null>(null);

  const containerVariants = {
    open: {
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.1,
      },
    },
    closed: {
      transition: {
        staggerChildren: 0.05,
        staggerDirection: -1,
      },
    },
  };

  const itemVariants = {
    open: {
      y: 0,
      opacity: 1,
      scale: 1,
      transition: {
        type: 'spring' as const,
        stiffness: 300,
        damping: 20,
      },
    },
    closed: {
      y: 20,
      opacity: 0,
      scale: 0.8,
      transition: {
        type: 'spring' as const,
        stiffness: 300,
        damping: 20,
      },
    },
  };

  const mainButtonVariants = {
    open: {
      rotate: 45,
      scale: 1.1,
      transition: {
        type: 'spring' as const,
        stiffness: 300,
        damping: 20,
      },
    },
    closed: {
      rotate: 0,
      scale: 1,
      transition: {
        type: 'spring' as const,
        stiffness: 300,
        damping: 20,
      },
    },
  };

  const backdropVariants = {
    open: {
      opacity: 1,
      transition: {
        duration: 0.2,
      },
    },
    closed: {
      opacity: 0,
      transition: {
        duration: 0.2,
      },
    },
  };

  return (
    <TooltipProvider>
      <div className="fixed bottom-6 right-6 z-50">
        {/* Backdrop */}
        <AnimatePresence>
          {isOpen && (
            <motion.div
              variants={backdropVariants}
              initial="closed"
              animate="open"
              exit="closed"
              className="fixed inset-0 bg-black/20 backdrop-blur-sm"
              onClick={() => setIsOpen(false)}
            />
          )}
        </AnimatePresence>

        {/* Action Items */}
        <motion.div
          variants={containerVariants}
          initial="closed"
          animate={isOpen ? 'open' : 'closed'}
          className="flex flex-col-reverse items-end space-y-reverse space-y-3 mb-3"
        >
          <AnimatePresence>
            {isOpen &&
              quickActions.map((action, index) => (
                <motion.div
                  key={action.id}
                  variants={itemVariants}
                  className="relative"
                  onHoverStart={() => setHoveredAction(action.id)}
                  onHoverEnd={() => setHoveredAction(null)}
                >
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <motion.div
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        <Button
                          size="lg"
                          onClick={action.onClick}
                          className={cn(
                            'h-12 w-12 rounded-full shadow-lg border-0 text-white',
                            `bg-gradient-to-r ${action.color}`,
                            'hover:shadow-xl transition-all duration-200'
                          )}
                        >
                          <action.icon className="h-5 w-5" />
                        </Button>
                      </motion.div>
                    </TooltipTrigger>
                    <TooltipContent side="left" className="bg-dark-bg text-dark-text border-dark-border">
                      <div className="flex items-center space-x-2">
                        <span>{action.label}</span>
                        {action.shortcut && (
                          <kbd className="px-2 py-1 text-xs bg-dark-bg-secondary rounded border border-dark-border">
                            {action.shortcut}
                          </kbd>
                        )}
                      </div>
                    </TooltipContent>
                  </Tooltip>

                  {/* Label for mobile */}
                  <AnimatePresence>
                    {hoveredAction === action.id && (
                      <motion.div
                        initial={{ opacity: 0, x: 10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 10 }}
                        className="absolute right-14 top-1/2 -translate-y-1/2 md:hidden"
                      >
                        <div className="bg-dark-bg text-dark-text px-3 py-2 rounded-lg shadow-lg border border-dark-border text-sm whitespace-nowrap">
                          {action.label}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              ))}
          </AnimatePresence>
        </motion.div>

        {/* Main Toggle Button */}
        <motion.div
          variants={mainButtonVariants}
          animate={isOpen ? 'open' : 'closed'}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Button
            size="lg"
            onClick={() => setIsOpen(!isOpen)}
            className="h-14 w-14 rounded-full bg-gradient-to-r from-osint-primary to-osint-primary-dark hover:from-osint-primary-dark hover:to-osint-primary shadow-xl border-0 text-white relative overflow-hidden"
          >
            {/* Animated background */}
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-osint-secondary to-osint-primary"
              animate={{
                scale: isOpen ? 1 : 0,
                opacity: isOpen ? 1 : 0,
              }}
              transition={{ duration: 0.2 }}
            />

            {/* Icon */}
            <div className="relative z-10">
              <AnimatePresence mode="wait">
                {isOpen ? (
                  <motion.div
                    key="close"
                    initial={{ rotate: -90, opacity: 0 }}
                    animate={{ rotate: 0, opacity: 1 }}
                    exit={{ rotate: 90, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <X className="h-6 w-6" />
                  </motion.div>
                ) : (
                  <motion.div
                    key="plus"
                    initial={{ rotate: 90, opacity: 0 }}
                    animate={{ rotate: 0, opacity: 1 }}
                    exit={{ rotate: -90, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Plus className="h-6 w-6" />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Pulse effect */}
            <motion.div
              className="absolute inset-0 rounded-full bg-white/20"
              animate={{
                scale: [1, 1.2, 1],
                opacity: [0.5, 0, 0.5],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          </Button>
        </motion.div>

        {/* Quick access hint */}
        <AnimatePresence>
          {!isOpen && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              transition={{ delay: 2, duration: 0.5 }}
              className="absolute -top-12 right-0 bg-dark-bg text-dark-text px-3 py-1 rounded-lg shadow-lg border border-dark-border text-xs whitespace-nowrap"
            >
              <div className="flex items-center space-x-1">
                <Zap className="h-3 w-3 text-osint-warning" />
                <span>Quick Actions</span>
              </div>
              <div className="absolute top-full right-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-dark-border"></div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </TooltipProvider>
  );
}
