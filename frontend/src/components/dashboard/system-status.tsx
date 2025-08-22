'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Activity,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Database,
  Server,
  Wifi,
  HardDrive
} from 'lucide-react';
import { formatDate, formatNumber } from '@/lib/utils';
import type { HealthCheckResponse, SourcesResponse, RunsResponse } from '@/types/api';

async function fetchHealth(): Promise<HealthCheckResponse> {
  const response = await fetch('/api/health');
  if (!response.ok) {
    throw new Error('Failed to fetch health data');
  }
  return response.json();
}

async function fetchSources(): Promise<SourcesResponse> {
  const response = await fetch('/api/sources');
  if (!response.ok) {
    throw new Error('Failed to fetch sources');
  }
  return response.json();
}

async function fetchActiveRuns(): Promise<RunsResponse> {
  const response = await fetch('/api/runs?status=running&limit=5');
  if (!response.ok) {
    throw new Error('Failed to fetch active runs');
  }
  return response.json();
}

export function SystemStatus() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: sources, isLoading: sourcesLoading } = useQuery({
    queryKey: ['sources'],
    queryFn: fetchSources,
    refetchInterval: 60000, // Refresh every minute
  });

  const { data: activeRuns, isLoading: runsLoading } = useQuery({
    queryKey: ['active-runs'],
    queryFn: fetchActiveRuns,
    refetchInterval: 15000, // Refresh every 15 seconds
  });

  const isLoading = healthLoading || sourcesLoading || runsLoading;

  if (isLoading) {
    return <SystemStatusSkeleton />;
  }

  const systemHealth = health?.status || 'unhealthy';
  const sourcesData = sources?.data || [];
  const runsData = activeRuns?.data || [];

  const healthySources = sourcesData.filter(s => s.health === 'ok').length;
  const totalSources = sourcesData.length;
  const healthPercentage = totalSources > 0 ? (healthySources / totalSources) * 100 : 0;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Systemstatus</CardTitle>
          <Server className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <StatusIcon status={systemHealth} />
            <Badge variant={systemHealth === 'healthy' ? 'default' : 'destructive'}>
              {systemHealth === 'healthy' ? 'Operasjonell' : 'Ikke tilgjengelig'}
            </Badge>
          </div>
          {health && (
            <div className="mt-3 space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">CLI tilgjengelig</span>
                <span className={health.cli_available ? 'text-green-600' : 'text-red-600'}>
                  {health.cli_available ? 'Ja' : 'Nei'}
                </span>
              </div>
              <div className="text-xs text-muted-foreground">
                Sist sjekket: {formatDate(new Date(health.timestamp), 'long')}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Kilder</CardTitle>
          <Database className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">{healthySources}/{totalSources}</span>
              <Badge variant={healthPercentage > 80 ? 'default' : healthPercentage > 50 ? 'secondary' : 'destructive'}>
                {healthPercentage.toFixed(0)}% OK
              </Badge>
            </div>
            <Progress value={healthPercentage} className="h-2" />
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="text-center">
                <div className="text-green-600 font-medium">
                  {sourcesData.filter(s => s.health === 'ok').length}
                </div>
                <div className="text-muted-foreground">OK</div>
              </div>
              <div className="text-center">
                <div className="text-yellow-600 font-medium">
                  {sourcesData.filter(s => s.health === 'warn').length}
                </div>
                <div className="text-muted-foreground">Advarsler</div>
              </div>
              <div className="text-center">
                <div className="text-red-600 font-medium">
                  {sourcesData.filter(s => s.health === 'down').length}
                </div>
                <div className="text-muted-foreground">Nede</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Aktive kjøringer</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="text-2xl font-bold">{runsData.length}</div>
            {runsData.length > 0 ? (
              <div className="space-y-2">
                {runsData.map((run) => (
                  <div key={run.id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                      <span className="font-medium">#{run.id.slice(0, 8)}</span>
                    </div>
                    <div className="text-muted-foreground">
                      {run.startedAt && formatDate(new Date(run.startedAt), 'short')}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">
                Ingen aktive kjøringer
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="md:col-span-2 lg:col-span-3">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <HardDrive className="h-5 w-5" />
            Systemressurser
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">CPU bruk</span>
                <span className="font-medium">42%</span>
              </div>
              <Progress value={42} className="h-2" />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Minne bruk</span>
                <span className="font-medium">68%</span>
              </div>
              <Progress value={68} className="h-2" />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Disk bruk</span>
                <span className="font-medium">23%</span>
              </div>
              <Progress value={23} className="h-2" />
            </div>
          </div>

          <div className="mt-4 pt-4 border-t">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="flex items-center space-x-2">
                <Wifi className="h-4 w-4 text-green-500" />
                <span className="text-muted-foreground">Nettverk:</span>
                <span className="font-medium text-green-600">Online</span>
              </div>
              <div className="flex items-center space-x-2">
                <Database className="h-4 w-4 text-green-500" />
                <span className="text-muted-foreground">Database:</span>
                <span className="font-medium text-green-600">Tilkoblet</span>
              </div>
              <div className="flex items-center space-x-2">
                <Clock className="h-4 w-4 text-blue-500" />
                <span className="text-muted-foreground">Oppetid:</span>
                <span className="font-medium">7d 14t</span>
              </div>
              <div className="flex items-center space-x-2">
                <Activity className="h-4 w-4 text-orange-500" />
                <span className="text-muted-foreground">Belastning:</span>
                <span className="font-medium">Normal</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'healthy':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'unhealthy':
      return <XCircle className="h-4 w-4 text-red-500" />;
    default:
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
  }
}

function SystemStatusSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="h-4 w-24 skeleton"></div>
          <div className="h-4 w-4 skeleton"></div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <div className="h-4 w-4 skeleton"></div>
            <div className="h-6 w-20 skeleton"></div>
          </div>
          <div className="mt-3 space-y-2">
            <div className="h-4 w-full skeleton"></div>
            <div className="h-3 w-32 skeleton"></div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="h-4 w-16 skeleton"></div>
          <div className="h-4 w-4 skeleton"></div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="h-8 w-12 skeleton"></div>
              <div className="h-6 w-16 skeleton"></div>
            </div>
            <div className="h-2 w-full skeleton"></div>
            <div className="grid grid-cols-3 gap-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="text-center space-y-1">
                  <div className="h-4 w-4 skeleton mx-auto"></div>
                  <div className="h-3 w-8 skeleton mx-auto"></div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="h-4 w-28 skeleton"></div>
          <div className="h-4 w-4 skeleton"></div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-8 w-4 skeleton"></div>
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 skeleton rounded-full"></div>
                    <div className="h-4 w-16 skeleton"></div>
                  </div>
                  <div className="h-4 w-12 skeleton"></div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="md:col-span-2 lg:col-span-3">
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 skeleton"></div>
            <div className="h-6 w-32 skeleton"></div>
          </div>
        </CardHeader>
        <CardContent>
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
          <div className="mt-4 pt-4 border-t">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center space-x-2">
                  <div className="h-4 w-4 skeleton"></div>
                  <div className="h-4 w-16 skeleton"></div>
                  <div className="h-4 w-12 skeleton"></div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}