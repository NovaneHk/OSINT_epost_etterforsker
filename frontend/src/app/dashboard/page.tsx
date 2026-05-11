'use client';

import { useState, useEffect, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { Users, Search, TrendingUp, Download } from 'lucide-react';
import { KpiCard } from '@/components/dashboard/kpi-card';
import { ActiveRunsTable } from '@/components/dashboard/active-runs-table';
import { SourceHealthGrid } from '@/components/dashboard/source-health-grid';
import { RecentLeads } from '@/components/dashboard/recent-leads';
import { ActivityFeed } from '@/components/dashboard/activity-feed';
import { QuickActions } from '@/components/dashboard/quick-actions';
import { SkeletonBlock } from '@/components/shared/skeleton-block';
import { formatCompact, formatPercentage } from '@/lib/format';
import { getDashboardMetrics, getDashboardTrends, getDashboardActivity } from '@/lib/data/dashboard';
import { getActiveRuns } from '@/lib/data/runs';
import { getSourceHealth } from '@/lib/data/sources';
import { getLeads } from '@/lib/data/leads';
import type { DashboardMetrics, TrendDataPoint, ActivityEvent, Run, SourceHealth, Lead } from '@/lib/types';

// Lazy-load the heavy Recharts chart — keeps initial JS parse lean
const DashboardTrendChart = dynamic(
  () =>
    import('@/components/dashboard/dashboard-trend-chart').then((m) => ({
      default: m.DashboardTrendChart,
    })),
  { ssr: false, loading: () => <SkeletonBlock className="h-72 rounded-xl" /> }
);

interface DashboardState {
  metrics: DashboardMetrics | null;
  trends: TrendDataPoint[];
  activity: ActivityEvent[];
  activeRuns: Run[];
  sourceHealth: SourceHealth[];
  recentLeads: Lead[];
  isLoading: boolean;
  error: string | null;
}

const INITIAL_STATE: DashboardState = {
  metrics: null,
  trends: [],
  activity: [],
  activeRuns: [],
  sourceHealth: [],
  recentLeads: [],
  isLoading: true,
  error: null,
};

export default function DashboardPage() {
  const [state, setState] = useState<DashboardState>(INITIAL_STATE);

  useEffect(() => {
    let cancelled = false;

    async function loadAll() {
      try {
        const [metricsRes, trendsRes, activityRes, runsRes, healthRes, leadsRes] =
          await Promise.all([
            getDashboardMetrics(),
            getDashboardTrends('30d'),
            getDashboardActivity(),
            getActiveRuns(),
            getSourceHealth(),
            getLeads({ pageSize: 8 }),
          ]);

        if (cancelled) return;

        setState({
          metrics: metricsRes.ok ? metricsRes.data : null,
          trends: trendsRes.ok ? trendsRes.data : [],
          activity: activityRes.ok ? activityRes.data : [],
          activeRuns: runsRes.ok ? runsRes.data : [],
          sourceHealth: healthRes.ok ? healthRes.data : [],
          recentLeads: leadsRes.ok ? leadsRes.data.items : [],
          isLoading: false,
          error: null,
        });
      } catch (err) {
        if (cancelled) return;
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: err instanceof Error ? err.message : 'Failed to load dashboard',
        }));
      }
    }

    loadAll();
    return () => { cancelled = true; };
  }, []);

  const leadSparkline = useMemo(
    () => state.trends.slice(-7).map((d) => d.leads),
    [state.trends]
  );
  const searchSparkline = useMemo(
    () => state.trends.slice(-7).map((d) => d.searches),
    [state.trends]
  );

  if (state.error) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 text-center">
        <p className="text-sm font-medium text-[var(--nt-danger)]">Failed to load dashboard</p>
        <p className="text-xs text-[var(--nt-text-secondary)]">{state.error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── KPI row ──────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {state.isLoading || !state.metrics ? (
          Array.from({ length: 4 }).map((_, i) => (
            <SkeletonBlock key={i} className="h-32 rounded-xl" />
          ))
        ) : (
          <>
            <KpiCard
              label="Leads 7d"
              value={formatCompact(state.metrics.leads7d)}
              delta={state.metrics.leads7dChange}
              icon={Users}
              sparklineData={leadSparkline}
              accentColor="var(--nt-accent)"
            />
            <KpiCard
              label="Searches 7d"
              value={formatCompact(state.metrics.searches7d)}
              delta={state.metrics.searches7dChange}
              icon={Search}
              sparklineData={searchSparkline}
              accentColor="var(--nt-ai)"
            />
            <KpiCard
              label="Conversion Rate"
              value={formatPercentage(state.metrics.conversionRate)}
              delta={state.metrics.conversionRateChange}
              icon={TrendingUp}
              accentColor="var(--nt-success)"
            />
            <KpiCard
              label="Exports 7d"
              value={String(state.metrics.exports7d)}
              delta={state.metrics.exports7dChange}
              icon={Download}
              accentColor="var(--nt-warning)"
            />
          </>
        )}
      </div>

      {/* ── Main trend chart ──────────────────────────────────────────────────── */}
      {state.isLoading ? (
        <SkeletonBlock className="h-72 rounded-xl" />
      ) : (
        <DashboardTrendChart data={state.trends} />
      )}

      {/* ── Active runs + source health ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {state.isLoading ? (
          <>
            <SkeletonBlock className="h-48 rounded-xl" />
            <SkeletonBlock className="h-48 rounded-xl" />
          </>
        ) : (
          <>
            <ActiveRunsTable runs={state.activeRuns} />
            <SourceHealthGrid sources={state.sourceHealth} />
          </>
        )}
      </div>

      {/* ── Recent leads + quick actions ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          {state.isLoading ? (
            <SkeletonBlock className="h-64 rounded-xl" />
          ) : (
            <RecentLeads leads={state.recentLeads} />
          )}
        </div>
        <QuickActions />
      </div>

      {/* ── Activity feed ─────────────────────────────────────────────────────── */}
      {state.isLoading ? (
        <SkeletonBlock className="h-48 rounded-xl" />
      ) : (
        <ActivityFeed events={state.activity} limit={10} />
      )}
    </div>
  );
}
