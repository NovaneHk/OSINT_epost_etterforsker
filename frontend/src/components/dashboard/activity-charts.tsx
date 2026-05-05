'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import { Calendar, TrendingUp, Target, Users } from 'lucide-react';
import { formatNumber, formatDate } from '@/lib/utils';
import type { ActivityResponse } from '@/types/api';

async function fetchActivity(): Promise<ActivityResponse> {
  const response = await fetch('/api/activity');
  if (!response.ok) {
    throw new Error('Failed to fetch activity data');
  }
  return response.json();
}

export function ActivityCharts() {
  const { data: activity, isLoading, error } = useQuery({
    queryKey: ['activity'],
    queryFn: fetchActivity,
    refetchInterval: 60000, // Refresh every minute
  });

  if (isLoading) {
    return <ActivityChartsSkeleton />;
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-muted-foreground">
          Kunne ikke laste aktivitetsdata. Prøv å oppdatere siden.
        </CardContent>
      </Card>
    );
  }

  if (!activity) return null;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
      <Card className="col-span-4">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Aktivitet siste 30 dager
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="leads" className="w-full">
            <TabsList>
              <TabsTrigger value="leads">Leads</TabsTrigger>
              <TabsTrigger value="runs">Kjøringer</TabsTrigger>
              <TabsTrigger value="exports">Eksporter</TabsTrigger>
            </TabsList>

            <TabsContent value="leads" className="mt-4">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={activity.data?.leads_timeline || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value) => formatDate(new Date(value), 'short')}
                  />
                  <YAxis tickFormatter={(value) => formatNumber(value)} />
                  <Tooltip
                    labelFormatter={(label) => formatDate(new Date(label), 'long')}
                    formatter={(value: number) => [formatNumber(value), 'Leads']}
                  />
                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </TabsContent>

            <TabsContent value="runs" className="mt-4">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={activity.data?.runs_timeline || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value) => formatDate(new Date(value), 'short')}
                  />
                  <YAxis tickFormatter={(value) => formatNumber(value)} />
                  <Tooltip
                    labelFormatter={(label) => formatDate(new Date(label), 'long')}
                    formatter={(value: number) => [formatNumber(value), 'Kjøringer']}
                  />
                  <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </TabsContent>

            <TabsContent value="exports" className="mt-4">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={activity.data?.exports_timeline || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value) => formatDate(new Date(value), 'short')}
                  />
                  <YAxis tickFormatter={(value) => formatNumber(value)} />
                  <Tooltip
                    labelFormatter={(label) => formatDate(new Date(label), 'long')}
                    formatter={(value: number) => [formatNumber(value), 'Eksporter']}
                  />
                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke="hsl(var(--destructive))"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <Card className="col-span-3">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Kilder fordeling
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={activity.data?.sources_distribution || []}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={120}
                paddingAngle={5}
                dataKey="count"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {(activity.data?.sources_distribution || []).map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getSourceColor(entry.name)}
                  />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => [formatNumber(value), 'Leads']} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="col-span-4">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Siste aktivitet
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {(activity.data?.recent_activity || []).map((item, index) => (
              <div key={index} className="flex items-center space-x-4">
                <div className={`w-2 h-2 rounded-full ${getActivityColor(item.type)}`} />
                <div className="flex-1 space-y-1">
                  <p className="text-sm font-medium leading-none">
                    {item.description}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {formatDate(new Date(item.timestamp), 'long')}
                  </p>
                </div>
                <div className="text-sm text-muted-foreground">
                  {item.details}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="col-span-3">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Top domener
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {(activity.data?.top_domains || []).map((domain, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="text-sm font-medium">{domain.domain}</div>
                  <div className="text-xs text-muted-foreground">
                    ({domain.percentage}%)
                  </div>
                </div>
                <div className="text-sm text-muted-foreground">
                  {formatNumber(domain.count)}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function getSourceColor(sourceName: string): string {
  const colors = {
    'LinkedIn': 'hsl(200, 100%, 50%)',
    'Hunter.io': 'hsl(120, 100%, 40%)',
    'Apollo': 'hsl(280, 100%, 50%)',
    'ZoomInfo': 'hsl(45, 100%, 50%)',
    'Clearbit': 'hsl(15, 100%, 50%)',
    'default': 'hsl(var(--muted))'
  };

  return colors[sourceName as keyof typeof colors] || colors.default;
}

function getActivityColor(type: string): string {
  const colors = {
    'lead': 'bg-blue-500',
    'run': 'bg-green-500',
    'export': 'bg-orange-500',
    'error': 'bg-red-500',
    'default': 'bg-gray-500'
  };

  return colors[type as keyof typeof colors] || colors.default;
}

function ActivityChartsSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
      <Card className="col-span-4">
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 skeleton"></div>
            <div className="h-6 w-48 skeleton"></div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-80 w-full skeleton"></div>
        </CardContent>
      </Card>

      <Card className="col-span-3">
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 skeleton"></div>
            <div className="h-6 w-32 skeleton"></div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-80 w-full skeleton"></div>
        </CardContent>
      </Card>

      <Card className="col-span-4">
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 skeleton"></div>
            <div className="h-6 w-32 skeleton"></div>
          </div>
        </CardHeader>
        <CardContent>
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
        </CardContent>
      </Card>

      <Card className="col-span-3">
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 skeleton"></div>
            <div className="h-6 w-24 skeleton"></div>
          </div>
        </CardHeader>
        <CardContent>
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
        </CardContent>
      </Card>
    </div>
  );
}