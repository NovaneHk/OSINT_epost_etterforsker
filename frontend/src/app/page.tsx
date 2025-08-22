import { Suspense } from 'react';
import { KPICards } from '@/components/dashboard/kpi-cards';
import { ActivityCharts } from '@/components/dashboard/activity-charts';
import { SystemStatus } from '@/components/dashboard/system-status';

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Oversikt over OSINT aktivitet og systemstatus
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <Suspense fallback={<KPICardsSkeleton />}>
        <KPICards />
      </Suspense>

      {/* Activity Charts */}
      <Suspense fallback={<ActivityChartsSkeleton />}>
        <ActivityCharts />
      </Suspense>

      {/* System Status */}
      <Suspense fallback={<SystemStatusSkeleton />}>
        <SystemStatus />
      </Suspense>
    </div>
  );
}

// Loading skeletons
function KPICardsSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="metric-card">
          <div className="p-6 space-y-2">
            <div className="flex items-center justify-between">
              <div className="h-4 w-20 skeleton"></div>
              <div className="h-4 w-4 skeleton"></div>
            </div>
            <div className="h-8 w-16 skeleton"></div>
            <div className="flex items-center justify-between">
              <div className="h-3 w-24 skeleton"></div>
              <div className="h-3 w-12 skeleton"></div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function ActivityChartsSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
      <div className="col-span-4">
        <div className="metric-card p-6">
          <div className="space-y-4">
            <div className="h-6 w-48 skeleton"></div>
            <div className="h-80 w-full skeleton"></div>
          </div>
        </div>
      </div>

      <div className="col-span-3">
        <div className="metric-card p-6">
          <div className="space-y-4">
            <div className="h-6 w-32 skeleton"></div>
            <div className="h-80 w-full skeleton"></div>
          </div>
        </div>
      </div>

      <div className="col-span-4">
        <div className="metric-card p-6">
          <div className="space-y-4">
            <div className="h-6 w-32 skeleton"></div>
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center space-x-4">
                  <div className="w-2 h-2 skeleton rounded-full"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-full skeleton"></div>
                    <div className="h-3 w-24 skeleton"></div>
                  </div>
                  <div className="h-4 w-12 skeleton"></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="col-span-3">
        <div className="metric-card p-6">
          <div className="space-y-4">
            <div className="h-6 w-24 skeleton"></div>
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="h-4 w-20 skeleton"></div>
                    <div className="h-3 w-12 skeleton"></div>
                  </div>
                  <div className="h-4 w-12 skeleton"></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SystemStatusSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="metric-card">
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="h-4 w-24 skeleton"></div>
              <div className="h-4 w-4 skeleton"></div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="h-8 w-16 skeleton"></div>
                <div className="h-6 w-20 skeleton"></div>
              </div>
              <div className="h-2 w-full skeleton"></div>
              <div className="grid grid-cols-3 gap-2">
                {Array.from({ length: 3 }).map((_, j) => (
                  <div key={j} className="text-center space-y-1">
                    <div className="h-4 w-4 skeleton mx-auto"></div>
                    <div className="h-3 w-8 skeleton mx-auto"></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ))}

      <div className="md:col-span-2 lg:col-span-3 metric-card">
        <div className="p-6 space-y-4">
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 skeleton"></div>
            <div className="h-6 w-32 skeleton"></div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="h-4 w-16 skeleton"></div>
                  <div className="h-4 w-8 skeleton"></div>
                </div>
                <div className="h-2 w-full skeleton"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}