'use client';

import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Users, Target, Download, Database, Sparkles, Zap } from 'lucide-react';
import { formatNumber, formatPercentage } from '@/lib/utils';
import { api } from '@/lib/api';
import type { KPIResponse } from '@/types/api';
import { cn } from '@/lib/utils';

export function KPICards() {
  const { data: kpis, isLoading, error } = useQuery({
    queryKey: ['kpis'],
    queryFn: api.getKPIs,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return <KPICardsSkeleton />;
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
      >
        <Card className="col-span-full bg-gradient-to-br from-osint-error/10 to-red-500/10 border-osint-error/20">
          <CardContent className="p-6 text-center">
            <div className="flex items-center justify-center space-x-2 text-osint-error">
              <Zap className="h-5 w-5" />
              <span className="font-medium">Kunne ikke laste KPI-data</span>
            </div>
            <p className="text-sm text-light-text-muted dark:text-dark-text-muted mt-2">
              Prøv å oppdatere siden eller kontakt support
            </p>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  if (!kpis) return null;

  const kpiData = [
    {
      title: 'Leads (7d)',
      value: kpis.leads7d || 0,
      format: 'number' as const,
      icon: Users,
      trend: '+12%',
      trendUp: true,
      description: 'Nye leads siste 7 dager',
      color: 'from-osint-primary to-osint-primary-dark',
      bgColor: 'bg-osint-primary/10',
      iconColor: 'text-osint-primary'
    },
    {
      title: 'Treff (7d)',
      value: kpis.hits7d || 0,
      format: 'number' as const,
      icon: Target,
      trend: '+8%',
      trendUp: true,
      description: 'Totalt antall treff',
      color: 'from-osint-secondary to-osint-secondary-dark',
      bgColor: 'bg-osint-secondary/10',
      iconColor: 'text-osint-secondary'
    },
    {
      title: 'Konverteringsrate',
      value: kpis.conversion_rate || 0,
      format: 'percentage' as const,
      icon: TrendingUp,
      trend: '+0.3%',
      trendUp: true,
      description: 'Leads til treff ratio',
      color: 'from-osint-success to-green-600',
      bgColor: 'bg-osint-success/10',
      iconColor: 'text-osint-success'
    },
    {
      title: 'Eksporter (7d)',
      value: kpis.exports7d || 0,
      format: 'number' as const,
      icon: Download,
      trend: '-2%',
      trendUp: false,
      description: 'Gjennomførte eksporter',
      color: 'from-osint-info to-blue-600',
      bgColor: 'bg-osint-info/10',
      iconColor: 'text-osint-info'
    }
  ];

  const sourceData = [
    {
      title: 'Totalt kilder',
      value: kpis.total_sources || 0,
      format: 'number' as const,
      icon: Database,
      trend: null,
      description: 'Konfigurerte datakilder',
      color: 'from-osint-warning to-orange-600',
      bgColor: 'bg-osint-warning/10',
      iconColor: 'text-osint-warning'
    },
    {
      title: 'Aktive kilder',
      value: kpis.active_sources || 0,
      format: 'number' as const,
      icon: Sparkles,
      trend: `${Math.round(((kpis.active_sources || 0) / (kpis.total_sources || 1)) * 100)}%`,
      trendUp: (kpis.active_sources || 0) / (kpis.total_sources || 1) > 0.8,
      description: 'Kilder i drift',
      color: 'from-purple-500 to-purple-700',
      bgColor: 'bg-purple-500/10',
      iconColor: 'text-purple-500'
    }
  ];

  const allKPIs = [...kpiData, ...sourceData];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.1,
      },
    },
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6"
    >
      {allKPIs.map((kpi, index) => (
        <KPICard key={index} index={index} {...kpi} />
      ))}
    </motion.div>
  );
}

interface KPICardProps {
  title: string;
  value: number;
  format: 'number' | 'percentage';
  icon: React.ComponentType<{ className?: string }>;
  trend?: string | null;
  trendUp?: boolean;
  description: string;
  color: string;
  bgColor: string;
  iconColor: string;
  index: number;
}

function KPICard({
  title,
  value,
  format,
  icon: Icon,
  trend,
  trendUp,
  description,
  color,
  bgColor,
  iconColor,
  index
}: KPICardProps) {
  const formattedValue = format === 'percentage'
    ? formatPercentage(value)
    : formatNumber(value);

  const cardVariants = {
    hidden: {
      opacity: 0,
      y: 20,
      scale: 0.95
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: 'spring' as const,
        stiffness: 300,
        damping: 20,
        delay: index * 0.05,
      },
    },
  };

  const iconVariants = {
    hover: {
      scale: 1.1,
      rotate: 5,
      transition: { type: 'spring' as const, stiffness: 400, damping: 10 }
    },
  };

  const valueVariants = {
    hidden: { scale: 0.8, opacity: 0 },
    visible: {
      scale: 1,
      opacity: 1,
      transition: {
        delay: index * 0.05 + 0.2,
        type: 'spring' as const,
        stiffness: 300,
        damping: 20
      }
    },
  };

  return (
    <motion.div
      variants={cardVariants}
      whileHover={{
        y: -4,
        transition: { type: 'spring', stiffness: 400, damping: 10 }
      }}
      className="group"
    >
      <Card className="relative overflow-hidden bg-white/80 dark:bg-dark-bg/80 backdrop-blur-md border-light-border dark:border-dark-border hover:border-osint-primary/50 dark:hover:border-osint-primary/50 transition-all duration-300 shadow-sm hover:shadow-lg hover:shadow-osint-primary/10">
        {/* Gradient background overlay */}
        <div className={cn(
          "absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300",
          `bg-gradient-to-br ${color}`
        )} />

        {/* Animated border glow */}
        <motion.div
          className="absolute inset-0 rounded-lg"
          animate={{
            boxShadow: [
              '0 0 0 0px rgba(10, 132, 255, 0)',
              '0 0 0 2px rgba(10, 132, 255, 0.1)',
              '0 0 0 0px rgba(10, 132, 255, 0)',
            ],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />

        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="text-sm font-medium text-light-text-secondary dark:text-dark-text-secondary group-hover:text-light-text dark:group-hover:text-dark-text transition-colors">
            {title}
          </CardTitle>
          <motion.div
            variants={iconVariants}
            whileHover="hover"
            className={cn(
              "p-2 rounded-lg transition-all duration-200",
              bgColor
            )}
          >
            <Icon className={cn("h-4 w-4", iconColor)} />
          </motion.div>
        </CardHeader>

        <CardContent className="space-y-3">
          <motion.div
            variants={valueVariants}
            className="text-2xl font-bold text-light-text dark:text-dark-text"
          >
            {formattedValue}
          </motion.div>

          <div className="flex items-center justify-between">
            <p className="text-xs text-light-text-muted dark:text-dark-text-muted">
              {description}
            </p>
            {trend && (
              <motion.div
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 + 0.3 }}
                className={cn(
                  "flex items-center text-xs font-medium px-2 py-1 rounded-full",
                  trendUp
                    ? 'text-osint-success bg-osint-success/10'
                    : 'text-osint-error bg-osint-error/10'
                )}
              >
                <motion.div
                  animate={{
                    y: trendUp ? [-1, 1, -1] : [1, -1, 1],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: 'easeInOut'
                  }}
                >
                  {trendUp ? (
                    <TrendingUp className="h-3 w-3 mr-1" />
                  ) : (
                    <TrendingDown className="h-3 w-3 mr-1" />
                  )}
                </motion.div>
                {trend}
              </motion.div>
            )}
          </div>

          {/* Progress bar for visual appeal */}
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: '100%' }}
            transition={{
              delay: index * 0.05 + 0.4,
              duration: 0.8,
              ease: 'easeOut'
            }}
            className="h-1 bg-light-bg-secondary dark:bg-dark-bg-secondary rounded-full overflow-hidden"
          >
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${Math.min((value / 1000) * 100, 100)}%` }}
              transition={{
                delay: index * 0.05 + 0.6,
                duration: 1,
                ease: 'easeOut'
              }}
              className={cn(
                "h-full rounded-full",
                `bg-gradient-to-r ${color}`
              )}
            />
          </motion.div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function KPICardsSkeleton() {
  const skeletonVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: 'spring' as const,
        stiffness: 300,
        damping: 20,
      },
    },
  };

  return (
    <motion.div
      variants={skeletonVariants}
      initial="hidden"
      animate="visible"
      className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6"
    >
      {Array.from({ length: 6 }).map((_, i) => (
        <motion.div key={i} variants={itemVariants}>
          <Card className="bg-white/80 dark:bg-dark-bg/80 backdrop-blur-md border-light-border dark:border-dark-border">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <motion.div
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="h-4 w-20 bg-light-bg-secondary dark:bg-dark-bg-secondary rounded"
              />
              <motion.div
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity, delay: 0.2 }}
                className="h-8 w-8 bg-light-bg-secondary dark:bg-dark-bg-secondary rounded-lg"
              />
            </CardHeader>
            <CardContent className="space-y-3">
              <motion.div
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity, delay: 0.4 }}
                className="h-8 w-16 bg-light-bg-secondary dark:bg-dark-bg-secondary rounded"
              />
              <div className="flex items-center justify-between">
                <motion.div
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 2, repeat: Infinity, delay: 0.6 }}
                  className="h-3 w-24 bg-light-bg-secondary dark:bg-dark-bg-secondary rounded"
                />
                <motion.div
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 2, repeat: Infinity, delay: 0.8 }}
                  className="h-3 w-12 bg-light-bg-secondary dark:bg-dark-bg-secondary rounded"
                />
              </div>
              <motion.div
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity, delay: 1 }}
                className="h-1 w-full bg-light-bg-secondary dark:bg-dark-bg-secondary rounded-full"
              />
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </motion.div>
  );
}
