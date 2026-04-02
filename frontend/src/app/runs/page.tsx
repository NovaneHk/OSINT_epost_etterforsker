"use client"

import { useState, useEffect, useRef } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Plus, Play, StopCircle, BarChart3, Clock, CheckCircle, AlertCircle, Search, Users, Eye } from 'lucide-react'
import { toast } from "sonner"
import { api } from '@/lib/api'

interface Run {
  id: string
  name: string
  type: string
  status: string
  sources: string
  search_terms: string
  filters: string
  leads_found: number
  progress: number
  error_message?: string
  created_at: string
  started_at?: string
  completed_at?: string
}

interface RunStats {
  total_runs: number
  pending_runs: number
  running_runs: number
  completed_runs: number
  failed_runs: number
  success_rate_percent: number
  total_leads_found: number
  recent_runs_7d: number
  avg_duration_minutes: number
  status_breakdown: Record<string, number>
  type_breakdown: Record<string, number>
}

interface RunResults {
  run_info: Run
  leads_found: any[]
  leads_count: number
  sources_used: number[]
  message?: string
  summary: {
    total_leads: number
    high_confidence: number
    verified_emails: number
    unique_companies: number
    avg_confidence: number
  }
}

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([])
  const [stats, setStats] = useState<RunStats | null>(null)
  const [selectedRun, setSelectedRun] = useState<Run | null>(null)
  const [runResults, setRunResults] = useState<RunResults | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [newRun, setNewRun] = useState({
    name: '',
    type: 'manual',
    target_domains: '',   // comma-separated domains e.g. "acme.com, example.no"
    keywords: '',         // comma-separated keywords
    max_results: '100',
  })
  const [isCreating, setIsCreating] = useState(false)

  const pollerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    fetchRuns()
    fetchStats()
  }, [])

  // WebSocket: receive run_completed / run_failed broadcasts and refresh immediately
  useEffect(() => {
    const wsUrl = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
      .replace(/^http/, 'ws') + '/api/ws/notifications';
    const connect = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data);
            if (msg.type === 'run_completed' || msg.type === 'run_failed') {
              fetchRuns();
              fetchStats();
            }
          } catch { /* ignore parse errors */ }
        };
        ws.onclose = () => {
          // reconnect after 5s if page is still mounted
          setTimeout(() => { if (wsRef.current === ws) connect(); }, 5000);
        };
      } catch { /* WebSocket not available (SSR) */ }
    };
    connect();
    return () => {
      const ws = wsRef.current;
      wsRef.current = null;
      ws?.close();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Poll every 5 seconds while any run is active (fallback if WS unavailable)
  useEffect(() => {
    const hasActive = runs.some(r => r.status === 'running' || r.status === 'pending');
    if (hasActive) {
      if (!pollerRef.current) {
        pollerRef.current = setInterval(() => {
          fetchRuns();
        }, 5000);
      }
    } else {
      if (pollerRef.current) {
        clearInterval(pollerRef.current);
        pollerRef.current = null;
      }
    }
    return () => {
      if (pollerRef.current) {
        clearInterval(pollerRef.current);
        pollerRef.current = null;
      }
    };
  }, [runs]);

  const mapRun = (run: any): Run => ({
    id: String(run.id),
    name: run.name || `Run ${run.id}`,
    type: String(run.configuration?.run_type || 'manual'),
    sources: JSON.stringify(run.source_ids || []),
    search_terms: JSON.stringify(run.configuration?.search_terms || {}),
    filters: JSON.stringify(run.filters || {}),
    status: run.status,
    leads_found: Number(run.leads_found || 0),
    progress: Number(run.progress || 0),
    error_message: run.error_message,
    created_at: run.created_at,
    started_at: run.started_at,
    completed_at: run.completed_at,
  })

  const fetchRuns = async () => {
    try {
      const data = await api.getRuns()
      setRuns(data.data.map(mapRun))
    } catch (error) {
      console.error('Error fetching runs:', error)
      toast.error('Error loading runs')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const data = await api.getRunStatistics()
      setStats({
        total_runs: Number(data.total_runs || 0),
        pending_runs: Number(data.pending_runs || 0),
        running_runs: Number(data.running_runs || 0),
        completed_runs: Number(data.completed_runs || 0),
        failed_runs: Number(data.failed_runs || 0),
        success_rate_percent: Math.round(Number(data.success_rate || 0) * 100),
        total_leads_found: Number(data.total_leads_found || 0),
        recent_runs_7d: 0,
        avg_duration_minutes: Number(data.average_duration_seconds || 0) / 60,
        status_breakdown: {
          pending: Number(data.pending_runs || 0),
          running: Number(data.running_runs || 0),
          completed: Number(data.completed_runs || 0),
          failed: Number(data.failed_runs || 0),
          cancelled: Number(data.cancelled_runs || 0),
        },
        type_breakdown: data.runs_by_type || {},
      })
    } catch (error) {
      console.error('Error fetching run stats:', error)
    }
  }

  const fetchRunResults = async (runId: string) => {
    try {
      const data = await api.getRunResults(runId)
      setRunResults({
        run_info: selectedRun || runs.find((run) => run.id === runId) || mapRun({ id: runId, name: `Run ${runId}`, status: 'completed', progress: 100, leads_found: 0, created_at: new Date().toISOString() }),
        leads_found: Array.isArray(data.results) ? data.results : [],
        leads_count: Number(data.total || 0),
        sources_used: [],
        message: typeof data.message === 'string' ? data.message : undefined,
        summary: {
          total_leads: Number(data.total || 0),
          high_confidence: 0,
          verified_emails: 0,
          unique_companies: 0,
          avg_confidence: 0,
        },
      })
    } catch (error) {
      console.error('Error fetching run results:', error)
      toast.error('Error loading run results')
    }
  }

  const handleCreateRun = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!newRun.name.trim()) {
      toast.error('Run name is required')
      return
    }

    const domains = newRun.target_domains
      .split(',')
      .map(d => d.trim())
      .filter(Boolean)
    const keywords = newRun.keywords
      .split(',')
      .map(k => k.trim())
      .filter(Boolean)

    try {
      setIsCreating(true)
      await api.createRun({
        name: newRun.name,
        source_ids: [],
        filters: {},
        configuration: {
          run_type: newRun.type,
          max_results: parseInt(newRun.max_results) || 100,
          search_terms: {
            domains,
            keywords,
          },
        },
      })
      toast.success('Kjøring opprettet')
      setShowCreateForm(false)
      setNewRun({ name: '', type: 'manual', target_domains: '', keywords: '', max_results: '100' })
      fetchRuns()
      fetchStats()
    } catch (error) {
      console.error('Error creating run:', error)
      toast.error(error instanceof Error ? error.message : 'Kunne ikke opprette kjøring')
    } finally {
      setIsCreating(false)
    }
  }

  const handleStartRun = async (runId: string) => {
    try {
      await api.startRun(runId)
      toast.success('Run started successfully')
      fetchRuns()
      fetchStats()
    } catch (error) {
      console.error('Error starting run:', error)
      toast.error('Error starting run')
    }
  }

  const handleStopRun = async (runId: string) => {
    try {
      await api.stopRun(runId)
      toast.success('Run stopped successfully')
      fetchRuns()
      fetchStats()
    } catch (error) {
      console.error('Error stopping run:', error)
      toast.error('Error stopping run')
    }
  }

  const handleViewResults = (run: Run) => {
    setSelectedRun(run)
    fetchRunResults(run.id)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500'
      case 'running': return 'bg-blue-500'
      case 'pending': return 'bg-yellow-500'
      case 'failed': return 'bg-red-500'
      case 'cancelled': return 'bg-gray-500'
      default: return 'bg-gray-500'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4" />
      case 'running': return <Play className="h-4 w-4" />
      case 'pending': return <Clock className="h-4 w-4" />
      case 'failed': return <AlertCircle className="h-4 w-4" />
      case 'cancelled': return <StopCircle className="h-4 w-4" />
      default: return <Clock className="h-4 w-4" />
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${Math.round(minutes)}m`
    const hours = Math.floor(minutes / 60)
    const mins = Math.round(minutes % 60)
    return `${hours}h ${mins}m`
  }

  if (selectedRun && runResults) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button variant="outline" size="sm" onClick={() => {
              setSelectedRun(null)
              setRunResults(null)
            }}>
              ← Back to Runs
            </Button>
            <div>
              <div className="flex items-center space-x-3">
                <h1 className="text-3xl font-bold">{selectedRun.name}</h1>
                <Badge
                  variant="secondary"
                  className={`text-white ${getStatusColor(selectedRun.status)}`}
                >
                  {getStatusIcon(selectedRun.status)}
                  <span className="ml-1">{selectedRun.status}</span>
                </Badge>
              </div>
              <p className="text-muted-foreground">Run Results & Analysis</p>
            </div>
          </div>
        </div>

        {/* Results Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Leads</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{runResults.summary.total_leads}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">High Confidence</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{runResults.summary.high_confidence}</div>
              <p className="text-xs text-muted-foreground">80%+ confidence</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Verified Emails</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{runResults.summary.verified_emails}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Confidence</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{runResults.summary.avg_confidence}%</div>
            </CardContent>
          </Card>
        </div>

        {/* Leads Results */}
        <Card>
          <CardHeader>
            <CardTitle>Found Leads ({runResults.leads_count})</CardTitle>
            {runResults.message && (
              <CardDescription>{runResults.message}</CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {runResults.leads_found.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">No leads found</p>
            ) : (
              <div className="space-y-4">
                {runResults.leads_found.map((lead: any, index: number) => (
                  <div key={index} className="border rounded-lg p-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-medium">{lead.name || 'Unknown'}</h4>
                        <p className="text-sm text-muted-foreground">{lead.email}</p>
                        <p className="text-sm">{lead.job_title} at {lead.company}</p>
                      </div>
                      <div className="text-right">
                        <Badge variant="outline">
                          {lead.confidence_score}% confidence
                        </Badge>
                        <p className="text-xs text-muted-foreground mt-1">
                          {lead.verification_status}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Search Runs</h1>
          <p className="text-muted-foreground">
            Execute and monitor OSINT search operations
          </p>
        </div>
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Run
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
              <Search className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_runs}</div>
              <p className="text-xs text-muted-foreground">
                {stats.recent_runs_7d} in last 7 days
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.success_rate_percent}%</div>
              <p className="text-xs text-muted-foreground">
                Completion rate
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Leads</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_leads_found}</div>
              <p className="text-xs text-muted-foreground">
                From all runs
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatDuration(stats.avg_duration_minutes)}</div>
              <p className="text-xs text-muted-foreground">
                Per completed run
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Create Run Form */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Search Run</CardTitle>
            <CardDescription>
              Configure and start a new OSINT search operation
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateRun} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="run-name">Run Name</Label>
                  <Input
                    id="run-name"
                    value={newRun.name}
                    onChange={(e) => setNewRun(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Enter run name"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="run-type">Run Type</Label>
                  <Select
                    value={newRun.type}
                    onValueChange={(value) => setNewRun(prev => ({ ...prev, type: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select run type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="manual">Manual</SelectItem>
                      <SelectItem value="automated">Automated</SelectItem>
                      <SelectItem value="scheduled">Scheduled</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="target-domains">Måldomener</Label>
                <Input
                  id="target-domains"
                  value={newRun.target_domains}
                  onChange={(e) => setNewRun(prev => ({ ...prev, target_domains: e.target.value }))}
                  placeholder="acme.com, example.no, company.org"
                />
                <p className="text-xs text-muted-foreground">Kommaseparerte domener som skal søkes gjennom</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="keywords">Nøkkelord (valgfritt)</Label>
                  <Input
                    id="keywords"
                    value={newRun.keywords}
                    onChange={(e) => setNewRun(prev => ({ ...prev, keywords: e.target.value }))}
                    placeholder="CTO, ingeniør, procurement"
                  />
                  <p className="text-xs text-muted-foreground">Kommaseparerte nøkkelord for filtrering</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="max-results">Maks resultater</Label>
                  <Input
                    id="max-results"
                    type="number"
                    min={1}
                    max={1000}
                    value={newRun.max_results}
                    onChange={(e) => setNewRun(prev => ({ ...prev, max_results: e.target.value }))}
                  />
                </div>
              </div>

              <div className="flex space-x-2">
                <Button type="submit" disabled={isCreating}>
                  {isCreating ? 'Creating...' : 'Create Run'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCreateForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Runs List */}
      <Tabs defaultValue="all" className="space-y-4">
        <TabsList>
          <TabsTrigger value="all">All Runs</TabsTrigger>
          <TabsTrigger value="running">Running</TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
          <TabsTrigger value="failed">Failed</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          {isLoading ? (
            <div className="text-center py-8">Laster kjøringer...</div>
          ) : runs.length === 0 ? (
            <Card>
              <CardContent className="text-center py-16">
                <p className="text-4xl mb-4">🔍</p>
                <p className="text-muted-foreground mb-4">Ingen kjøringer ennå</p>
                <Button onClick={() => setShowCreateForm(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Start din første kjøring
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {runs.map((run) => (
                <Card key={run.id}>
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <CardTitle>{run.name}</CardTitle>
                          <Badge
                            variant="secondary"
                            className={`text-white ${getStatusColor(run.status)}`}
                          >
                            {getStatusIcon(run.status)}
                            <span className="ml-1">{run.status}</span>
                          </Badge>
                          <Badge variant="outline">
                            {run.type}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {run.status === 'pending' && (
                          <Button
                            size="sm"
                            onClick={() => handleStartRun(run.id)}
                          >
                            <Play className="h-4 w-4 mr-1" />
                            Start
                          </Button>
                        )}
                        {run.status === 'running' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleStopRun(run.id)}
                          >
                            <StopCircle className="h-4 w-4 mr-1" />
                            Stop
                          </Button>
                        )}
                        {run.status === 'completed' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleViewResults(run)}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            View Results
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Progress</p>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full transition-all"
                              style={{ width: `${run.progress}%` }}
                            />
                          </div>
                          <span className="text-xs">{run.progress}%</span>
                        </div>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Leads Found</p>
                        <p className="font-medium">{run.leads_found}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Created</p>
                        <p className="font-medium">{formatDate(run.created_at)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">
                          {run.status === 'completed' ? 'Completed' :
                           run.status === 'running' ? 'Started' : 'Status'}
                        </p>
                        <p className="font-medium">
                          {run.completed_at ? formatDate(run.completed_at) :
                           run.started_at ? formatDate(run.started_at) :
                           run.status}
                        </p>
                      </div>
                    </div>

                    {run.error_message && (
                      <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-sm text-red-700">{run.error_message}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Similar structure for other tabs... */}
        <TabsContent value="running">
          <div className="grid gap-4">
            {runs.filter(r => r.status === 'running').map((run) => (
              <Card key={run.id}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle>{run.name}</CardTitle>
                        <Badge variant="secondary" className="text-white bg-blue-500">
                          <Play className="h-4 w-4 mr-1" />
                          {run.status}
                        </Badge>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleStopRun(run.id)}
                    >
                      <StopCircle className="h-4 w-4 mr-1" />
                      Stop
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Progress</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${run.progress}%` }}
                          />
                        </div>
                        <span className="text-xs">{run.progress}%</span>
                      </div>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Leads Found</p>
                      <p className="font-medium">{run.leads_found}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Started</p>
                      <p className="font-medium">{run.started_at ? formatDate(run.started_at) : 'N/A'}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="completed">
          <div className="grid gap-4">
            {runs.filter(r => r.status === 'completed').map((run) => (
              <Card key={run.id}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle>{run.name}</CardTitle>
                        <Badge variant="secondary" className="text-white bg-green-500">
                          <CheckCircle className="h-4 w-4 mr-1" />
                          {run.status}
                        </Badge>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleViewResults(run)}
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      View Results
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Leads Found</p>
                      <p className="font-medium">{run.leads_found}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Started</p>
                      <p className="font-medium">{run.started_at ? formatDate(run.started_at) : 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Completed</p>
                      <p className="font-medium">{run.completed_at ? formatDate(run.completed_at) : 'N/A'}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="failed">
          <div className="grid gap-4">
            {runs.filter(r => r.status === 'failed').map((run) => (
              <Card key={run.id}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle>{run.name}</CardTitle>
                        <Badge variant="secondary" className="text-white bg-red-500">
                          <AlertCircle className="h-4 w-4 mr-1" />
                          {run.status}
                        </Badge>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleStartRun(run.id)}
                    >
                      <Play className="h-4 w-4 mr-1" />
                      Retry
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                    <div>
                      <p className="text-muted-foreground">Created</p>
                      <p className="font-medium">{formatDate(run.created_at)}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Type</p>
                      <p className="font-medium">{run.type}</p>
                    </div>
                  </div>

                  {run.error_message && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-700">{run.error_message}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}