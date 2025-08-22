'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Users, Target, Download, Database } from 'lucide-react';
import { formatNumber, formatPercentage } from '@/lib/utils';
import { api } from '@/lib/api';
import type { KPIResponse } from '@/types/api';

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
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="col-span-full">
          <CardContent className="p-6 text-center text-muted-foreground">
            Kunne ikke laste KPI-data. Prøv å oppdatere siden.
          </CardContent>
        </Card>
      </div>
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
      description: 'Nye leads siste 7 dager'
    },
    {
      title: 'Treff (7d)',
      value: kpis.hits7d || 0,
      format: 'number' as const,
      icon: Target,
      trend: '+8%',
      trendUp: true,
      description: 'Totalt antall treff'
    },
    {
      title: 'Konverteringsrate',
      value: kpis.conversion_rate || 0,
      format: 'percentage' as const,
      icon: TrendingUp,
      trend: '+0.3%',
      trendUp: true,
      description: 'Leads til treff ratio'
    },
    {
      title: 'Eksporter (7d)',
      value: kpis.exports7d || 0,
      format: 'number' as const,
      icon: Download,
      trend: '-2%',
      trendUp: false,
      description: 'Gjennomførte eksporter'
    }
  ];

  const sourceData = [
    {
      title: 'Totalt kilder',
      value: kpis.total_sources || 0,
      format: 'number' as const,
      icon: Database,
      trend: null,
      description: 'Konfigurerte datakilder'
    },
    {
      title: 'Aktive kilder',
      value: kpis.active_sources || 0,
      format: 'number' as const,
      icon: Database,
      trend: `${Math.round(((kpis.active_sources || 0) / (kpis.total_sources || 1)) * 100)}%`,
      trendUp: (kpis.active_sources || 0) / (kpis.total_sources || 1) > 0.8,
      description: 'Kilder i drift'
    }
  ];

  const allKPIs = [...kpiData, ...sourceData];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {allKPIs.map((kpi, index) => (
        <KPICard key={index} {...kpi} />
      ))}
    </div>
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
}

function KPICard({ title, value, format, icon: Icon, trend, trendUp, description }: KPICardProps) {
  const formattedValue = format === 'percentage'
    ? formatPercentage(value)
    : formatNumber(value);

  return (
    <Card className="metric-card">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {formattedValue}
        </div>
        <div className="flex items-center justify-between mt-2">
          <p className="text-xs text-muted-foreground">
            {description}
          </p>
          {trend && (
            <div className={`flex items-center text-xs ${
              trendUp ? 'text-green-600' : 'text-red-600'
            }`}>
              {trendUp ? (
                <TrendingUp className="h-3 w-3 mr-1" />
              ) : (
                <TrendingDown className="h-3 w-3 mr-1" />
              )}
              {trend}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function KPICardsSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {Array.from({ length: 6 }).map((_, i) => (
        <Card key={i} className="metric-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="h-4 w-20 skeleton"></div>
            <div className="h-4 w-4 skeleton"></div>
          </CardHeader>
          <CardContent>
            <div className="h-8 w-16 skeleton mb-2"></div>
            <div className="flex items-center justify-between">
              <div className="h-3 w-24 skeleton"></div>
              <div className="h-3 w-12 skeleton"></div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}