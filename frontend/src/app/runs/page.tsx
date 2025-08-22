'use client';

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/components/ui/use-toast';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  ScrollArea,
} from '@/components/ui/scroll-area';
import {
  Play,
  Square,
  RefreshCw,
  MoreHorizontal,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Activity,
  FileText,
  TrendingUp,
  Users,
  Target,
  Download,
  Calendar,
  Filter,
  Eye
} from 'lucide-react';
import { formatDate, formatNumber, formatRelativeTime } from '@/lib/utils';
import type { Run, RunsResponse, CreateRunRequest } from '@/types/api';

// API functions
async function fetchRuns(): Promise<RunsResponse> {
  const response = await fetch('/api/runs');
  if (!response.ok) {
    throw new Error('Failed to fetch runs');
  }
  return response.json();
}

async function createRun(request: CreateRunRequest): Promise<{ runId: string }> {
  const response = await fetch('/api/runs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error('Failed to create run');
  }
  return response.json();
}

async function stopRun(runId: string): Promise<void> {
  const response = await fetch(`/api/runs/${runId}/stop`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Failed to stop run');
  }
}

async function fetchRunLogs(runId: string): Promise<{ logs: string[] }> {
  const response = await fetch(`/api/runs/${runId}/logs`);
  if (!response.ok) {
    throw new Error('Failed to fetch run logs');
  }
  return response.json();
}

export default function RunsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // State
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [showLogsDialog, setShowLogsDialog] = useState(false);
  const [activeTab, setActiveTab] = useState('timeline');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Fetch runs
  const {
    data: runsResponse,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['runs'],
    queryFn: fetchRuns,
    refetchInterval: 5000, // Refresh every 5 seconds for real-time updates
  });

  // Fetch logs for selected run
  const {
    data: logsData,
    isLoading: logsLoading
  } = useQuery({
    queryKey: ['run-logs', selectedRun?.id],
    queryFn: () => selectedRun ? fetchRunLogs(selectedRun.id) : Promise.resolve({ logs: [] }),
    enabled: !!selectedRun && showLogsDialog,
    refetchInterval: 2000, // Refresh logs every 2 seconds
  });

  // Mutations
  const createRunMutation = useMutation({
    mutationFn: createRun,
    onSuccess: () => {
      toast({
        title: 'Kjøring startet',
        description: 'En ny OSINT-kjøring har blitt startet',
      });
      queryClient.invalidateQueries(['runs']);
    },
    onError: (error: Error) => {
      toast({
        title: 'Kunne ikke starte kjøring',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  const stopRunMutation = useMutation({
    mutationFn: stopRun,
    onSuccess: () => {
      toast({
        title: 'Kjøring stoppet',
        description: 'Kjøringen har blitt stoppet',
      });
      queryClient.invalidateQueries(['runs']);
    },
    onError: (error: Error) => {
      toast({
        title: 'Kunne ikke stoppe kjøring',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Event handlers
  const handleStartRun = useCallback(() => {
    createRunMutation.mutate({});
  }, [createRunMutation]);

  const handleStopRun = useCallback((runId: string) => {
    stopRunMutation.mutate(runId);
  }, [stopRunMutation]);

  const handleViewLogs = useCallback((run: Run) => {
    setSelectedRun(run);
    setShowLogsDialog(true);
  }, []);

  // Computed values
  const runs = runsResponse?.data || [];

  const stats = useMemo(() => {
    const total = runs.length;
    const running = runs.filter(r => r.status === 'running').length;
    const success = runs.filter(r => r.status === 'success').length;
    const failed = runs.filter(r => r.status === 'error').length;
    const queued = runs.filter(r => r.status === 'queued').length;

    const totalLeads = runs.reduce((sum, run) => sum + (run.stats?.newLeads || 0), 0);
    const totalHits = runs.reduce((sum, run) => sum + (run.stats?.hits || 0), 0);

    return { total, running, success, failed, queued, totalLeads, totalHits };
  }, [runs]);

  const filteredRuns = useMemo(() => {
    if (statusFilter === 'all') return runs;
    return runs.filter(run => run.status === statusFilter);
  }, [runs, statusFilter]);

  const groupedRuns = useMemo(() => {
    const groups: Record<string, Run[]> = {};

    filteredRuns.forEach(run => {
      const date = new Date(run.startedAt || run.finishedAt || new Date()).toDateString();
      if (!groups[date]) groups[date] = [];
      groups[date].push(run);
    });

    // Sort by date (newest first)
    const sortedGroups = Object.entries(groups).sort((a, b) =>
      new Date(b[0]).getTime() - new Date(a[0]).getTime()
    );

    return sortedGroups;
  }, [filteredRuns]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws`);

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'run_update' || message.type === 'run_complete') {
        queryClient.invalidateQueries(['runs']);
      }
    };

    return () => ws.close();
  }, [queryClient]);

  if (isLoading && runs.length === 0) {
    return <RunsPageSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Kjøringer</h1>
          <p className="text-muted-foreground">
            Overvåk og administrer OSINT-kjøringer
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Oppdater
          </Button>

          <Button
            size="sm"
            onClick={handleStartRun}
            disabled={createRunMutation.isLoading || stats.running > 0}
          >
            <Play className="mr-2 h-4 w-4" />
            Start kjøring
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Totalt</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(stats.total)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Aktive</CardTitle>
            <Clock className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{formatNumber(stats.running)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Vellykket</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{formatNumber(stats.success)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Feilet</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{formatNumber(stats.failed)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">I kø</CardTitle>
            <Calendar className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{formatNumber(stats.queued)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Nye leads</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(stats.totalLeads)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Totalt treff</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(stats.totalHits)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="timeline">Tidslinje</TabsTrigger>
            <TabsTrigger value="table">Tabell</TabsTrigger>
          </TabsList>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Filter className="mr-2 h-4 w-4" />
                Filter: {getStatusDisplayName(statusFilter)}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Filtrer etter status</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setStatusFilter('all')}>
                Alle
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter('running')}>
                Aktive
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter('queued')}>
                I kø
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter('success')}>
                Vellykket
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter('error')}>
                Feilet
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <TabsContent value="timeline" className="mt-6">
          <div className="space-y-6">
            {groupedRuns.map(([date, dayRuns]) => (
              <div key={date}>
                <h3 className="text-lg font-semibold mb-4">
                  {formatDate(new Date(date), 'long')}
                </h3>

                <div className="space-y-4">
                  {dayRuns.map((run) => (
                    <RunCard
                      key={run.id}
                      run={run}
                      onStop={handleStopRun}
                      onViewLogs={handleViewLogs}
                      isStopping={stopRunMutation.isLoading}
                    />
                  ))}
                </div>
              </div>
            ))}

            {filteredRuns.length === 0 && (
              <div className="text-center py-12">
                <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Ingen kjøringer</h3>
                <p className="text-muted-foreground mb-4">
                  {statusFilter === 'all'
                    ? 'Ingen kjøringer funnet. Start en ny kjøring for å komme i gang.'
                    : `Ingen kjøringer med status "${getStatusDisplayName(statusFilter)}".`
                  }
                </p>
                {statusFilter === 'all' && (
                  <Button onClick={handleStartRun} disabled={createRunMutation.isLoading}>
                    <Play className="mr-2 h-4 w-4" />
                    Start første kjøring
                  </Button>
                )}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="table" className="mt-6">
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="p-4 text-left font-medium">Status</th>
                      <th className="p-4 text-left font-medium">Startet</th>
                      <th className="p-4 text-left font-medium">Varighet</th>
                      <th className="p-4 text-left font-medium">Nye leads</th>
                      <th className="p-4 text-left font-medium">Treff</th>
                      <th className="p-4 text-left font-medium">Handlinger</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRuns.map((run) => (
                      <tr key={run.id} className="border-b">
                        <td className="p-4">
                          <RunStatusBadge status={run.status} />
                        </td>
                        <td className="p-4 text-sm">
                          {run.startedAt ? formatRelativeTime(run.startedAt) : '—'}
                        </td>
                        <td className="p-4 text-sm">
                          {getDuration(run)}
                        </td>
                        <td className="p-4 text-sm">
                          {formatNumber(run.stats?.newLeads || 0)}
                        </td>
                        <td className="p-4 text-sm">
                          {formatNumber(run.stats?.hits || 0)}
                        </td>
                        <td className="p-4">
                          <div className="flex items-center space-x-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleViewLogs(run)}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            {run.status === 'running' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleStopRun(run.id)}
                                disabled={stopRunMutation.isLoading}
                              >
                                <Square className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Logs Dialog */}
      <Dialog open={showLogsDialog} onOpenChange={setShowLogsDialog}>
        <DialogContent className="sm:max-w-[800px] h-[600px]">
          <DialogHeader>
            <DialogTitle>Kjøring #{selectedRun?.id.slice(0, 8)}</DialogTitle>
            <DialogDescription>
              Logger og detaljer for kjøringen
            </DialogDescription>
          </DialogHeader>

          {selectedRun && (
            <div className="space-y-4 flex-1">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">Status</label>
                  <div className="mt-1">
                    <RunStatusBadge status={selectedRun.status} />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium">Startet</label>
                  <p className="text-sm text-muted-foreground mt-1">
                    {selectedRun.startedAt ? formatDate(new Date(selectedRun.startedAt), 'long') : '—'}
                  </p>
                </div>
              </div>

              {selectedRun.stats && (
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <label className="text-sm font-medium">Skannet</label>
                    <p className="text-lg font-bold">{formatNumber(selectedRun.stats.scanned)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Treff</label>
                    <p className="text-lg font-bold">{formatNumber(selectedRun.stats.hits)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Nye leads</label>
                    <p className="text-lg font-bold">{formatNumber(selectedRun.stats.newLeads)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Duplikater</label>
                    <p className="text-lg font-bold">{formatNumber(selectedRun.stats.duplicates)}</p>
                  </div>
                </div>
              )}

              <Separator />

              <div className="flex-1">
                <label className="text-sm font-medium">Logger</label>
                <ScrollArea className="h-[300px] w-full border rounded-md p-4 mt-2">
                  {logsLoading ? (
                    <div className="flex items-center justify-center h-full">
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      <span className="ml-2 text-sm">Laster logger...</span>
                    </div>
                  ) : logsData?.logs && logsData.logs.length > 0 ? (
                    <div className="space-y-1">
                      {logsData.logs.map((log, index) => (
                        <div key={index} className="text-sm font-mono text-muted-foreground">
                          {log}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center text-muted-foreground">
                      Ingen logger tilgjengelig
                    </div>
                  )}
                </ScrollArea>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface RunCardProps {
  run: Run;
  onStop: (runId: string) => void;
  onViewLogs: (run: Run) => void;
  isStopping: boolean;
}

function RunCard({ run, onStop, onViewLogs, isStopping }: RunCardProps) {
  const progress = useMemo(() => {
    if (run.status === 'success') return 100;
    if (run.status === 'error') return 100;
    if (run.status === 'running' && run.stats) {
      // Simple progress calculation based on stats
      const totalExpected = 1000; // This would come from run configuration
      return Math.min((run.stats.scanned / totalExpected) * 100, 95);
    }
    return 0;
  }, [run]);

  return (
    <Card className="relative">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <RunStatusBadge status={run.status} />
            <div>
              <div className="font-medium">Kjøring #{run.id.slice(0, 8)}</div>
              <div className="text-sm text-muted-foreground">
                {run.startedAt ? formatRelativeTime(run.startedAt) : 'Ikke startet'}
              </div>
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onViewLogs(run)}>
                <FileText className="mr-2 h-4 w-4" />
                Vis logger
              </DropdownMenuItem>
              {run.status === 'running' && (
                <DropdownMenuItem
                  onClick={() => onStop(run.id)}
                  disabled={isStopping}
                  className="text-destructive"
                >
                  <Square className="mr-2 h-4 w-4" />
                  Stopp kjøring
                </DropdownMenuItem>
              )}
              {run.logUrl && (
                <DropdownMenuItem onClick={() => window.open(run.logUrl, '_blank')}>
                  <Download className="mr-2 h-4 w-4" />
                  Last ned logger
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {run.status === 'running' && (
          <div>
            <div className="flex items-center justify-between text-sm mb-2">
              <span>Fremdrift</span>
              <span>{progress.toFixed(0)}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}

        {run.stats && (
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <div className="font-medium">{formatNumber(run.stats.scanned)}</div>
              <div className="text-muted-foreground">Skannet</div>
            </div>
            <div>
              <div className="font-medium">{formatNumber(run.stats.hits)}</div>
              <div className="text-muted-foreground">Treff</div>
            </div>
            <div>
              <div className="font-medium">{formatNumber(run.stats.newLeads)}</div>
              <div className="text-muted-foreground">Nye leads</div>
            </div>
            <div>
              <div className="font-medium">{formatNumber(run.stats.duplicates)}</div>
              <div className="text-muted-foreground">Duplikater</div>
            </div>
          </div>
        )}

        {run.error && (
          <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm">
            <div className="font-medium mb-1">Feil oppstod:</div>
            <div>{run.error}</div>
          </div>
        )}

        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>Varighet: {getDuration(run)}</span>
          {run.finishedAt && (
            <span>Fullført: {formatRelativeTime(run.finishedAt)}</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function RunStatusBadge({ status }: { status: string }) {
  const variants = {
    queued: 'secondary',
    running: 'default',
    success: 'default',
    error: 'destructive',
    partial: 'secondary'
  } as const;

  const icons = {
    queued: Clock,
    running: Activity,
    success: CheckCircle,
    error: XCircle,
    partial: AlertTriangle
  };

  const Icon = icons[status as keyof typeof icons] || Clock;

  return (
    <Badge variant={variants[status as keyof typeof variants] || 'secondary'} className="flex items-center gap-1">
      <Icon className="h-3 w-3" />
      {getStatusDisplayName(status)}
    </Badge>
  );
}

function getStatusDisplayName(status: string): string {
  const names = {
    all: 'Alle',
    queued: 'I kø',
    running: 'Aktiv',
    success: 'Vellykket',
    error: 'Feilet',
    partial: 'Delvis'
  };
  return names[status as keyof typeof names] || status;
}

function getDuration(run: Run): string {
  if (!run.startedAt) return '—';

  const start = new Date(run.startedAt);
  const end = run.finishedAt ? new Date(run.finishedAt) : new Date();
  const diff = end.getTime() - start.getTime();

  const minutes = Math.floor(diff / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);

  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

function RunsPageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="h-8 w-48 skeleton mb-2"></div>
          <div className="h-4 w-64 skeleton"></div>
        </div>
        <div className="flex space-x-2">
          <div className="h-9 w-24 skeleton"></div>
          <div className="h-9 w-32 skeleton"></div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        {Array.from({ length: 7 }).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="h-4 w-16 skeleton"></div>
                <div className="h-4 w-4 skeleton"></div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-8 w-12 skeleton"></div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="h-6 w-16 skeleton"></div>
                  <div>
                    <div className="h-4 w-32 skeleton mb-1"></div>
                    <div className="h-3 w-24 skeleton"></div>
                  </div>
                </div>
                <div className="h-8 w-8 skeleton"></div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-4 gap-4">
                <div className="h-4 w-12 skeleton"></div>
                <div className="h-4 w-12 skeleton"></div>
                <div className="h-4 w-12 skeleton"></div>
                <div className="h-4 w-12 skeleton"></div>
              </div>
              <div className="flex items-center justify-between">
                <div className="h-3 w-24 skeleton"></div>
                <div className="h-3 w-24 skeleton"></div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}