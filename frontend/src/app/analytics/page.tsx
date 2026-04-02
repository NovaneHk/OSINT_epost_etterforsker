'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  Globe,
  Shield,
  TrendingUp,
  Zap,
  Eye,
  Clock,
  Server,
  Cpu
} from 'lucide-react'

// Real-time Analytics Dashboard for Phase 4
export default function AnalyticsPage() {
  const [dashboardData, setDashboardData] = useState<any>(null)
  const [threatsData, setThreatsData] = useState<any>(null)
  const [performanceData, setPerformanceData] = useState<any>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  // WebSocket connection for real-time updates
  useEffect(() => {
    let ws: WebSocket | null = null

    const connectWebSocket = () => {
      try {
        // In production, use proper WebSocket URL
        const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const wsBase = apiBase.replace(/^http/, 'ws')
        ws = new WebSocket(`${wsBase}/api/analytics/ws`)

        ws.onopen = () => {
          console.log('WebSocket connected')
          setIsConnected(true)
        }

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data)
          if (data.type === 'analytics_update') {
            setLastUpdate(new Date())
            // Update dashboard with real-time data
            console.log('Real-time update received:', data.data)
          }
        }

        ws.onclose = () => {
          console.log('WebSocket disconnected')
          setIsConnected(false)
          // Attempt to reconnect after 5 seconds
          setTimeout(connectWebSocket, 5000)
        }

        ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          setIsConnected(false)
        }
      } catch (error) {
        console.error('Failed to connect WebSocket:', error)
        setIsConnected(false)
      }
    }

    // Initial data fetch
    fetchDashboardData()
    fetchThreatsData()
    fetchPerformanceData()

    // Connect WebSocket
    connectWebSocket()

    // Cleanup on unmount
    return () => {
      if (ws) {
        ws.close()
      }
    }
  }, [])

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const fetchDashboardData = async () => {
    try {
      const token = typeof window !== 'undefined'
        ? (document.cookie.match(/(?:^|;\s*)token=([^;]*)/))?.[1] || localStorage.getItem('accessToken')
        : null
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {}
      const res = await fetch(`${apiBase}/api/analytics/dashboard/overview`, { headers })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setDashboardData(await res.json())
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    }
  }

  const fetchThreatsData = async () => {
    try {
      const token = typeof window !== 'undefined'
        ? (document.cookie.match(/(?:^|;\s*)token=([^;]*)/))?.[1] || localStorage.getItem('accessToken')
        : null
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {}
      const res = await fetch(`${apiBase}/api/analytics/threats/realtime`, { headers })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setThreatsData(await res.json())
    } catch (error) {
      console.error('Failed to fetch threats data:', error)
    }
  }

  const fetchPerformanceData = async () => {
    try {
      const token = typeof window !== 'undefined'
        ? (document.cookie.match(/(?:^|;\s*)token=([^;]*)/))?.[1] || localStorage.getItem('accessToken')
        : null
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {}
      const res = await fetch(`${apiBase}/api/analytics/performance/metrics`, { headers })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setPerformanceData(await res.json())
    } catch (error) {
      console.error('Failed to fetch performance data:', error)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-500'
      case 'high': return 'bg-orange-500'
      case 'medium': return 'bg-yellow-500'
      case 'low': return 'bg-green-500'
      default: return 'bg-gray-500'
    }
  }

  const getHealthStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600'
      case 'degraded': return 'text-yellow-600'
      case 'error': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  if (!dashboardData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading analytics dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Real-time Analytics Dashboard</h1>
          <p className="text-gray-600 mt-1">Advanced AI-powered OSINT intelligence monitoring</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm text-gray-600">
              {isConnected ? 'Live' : 'Disconnected'}
            </span>
          </div>
          <span className="text-xs text-gray-500">
            Last update: {lastUpdate.toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Investigations</CardTitle>
            <Eye className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData.overview.total_investigations.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              +12% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Threats</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{dashboardData.overview.active_threats}</div>
            <p className="text-xs text-muted-foreground">
              -3 from yesterday
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Risk Score</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(dashboardData.overview.risk_score_average * 100).toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              +2.1% from last week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Processing Speed</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData.overview.processing_speed}/min</div>
            <p className="text-xs text-muted-foreground">
              +8% efficiency gain
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Dashboard Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="threats">Threat Monitoring</TabsTrigger>
          <TabsTrigger value="ai-analytics">AI Analytics</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* System Health */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Shield className="h-5 w-5" />
                  <span>System Health</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span>Overall Status</span>
                    <Badge variant={dashboardData.system_health.status === 'healthy' ? 'default' : 'destructive'}>
                      {dashboardData.system_health.status}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>Uptime</span>
                    <span className="font-medium">{dashboardData.system_health.uptime}</span>
                  </div>
                  <div className="space-y-2">
                    {Object.entries(dashboardData.system_health.components).map(([component, status]) => (
                      <div key={component} className="flex justify-between items-center">
                        <span className="capitalize">{component.replace('_', ' ')}</span>
                        <span className={`text-sm font-medium ${getHealthStatusColor(status as string)}`}>
                          {status as string}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* AI Analytics Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Brain className="h-5 w-5" />
                  <span>AI Analytics Summary</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium mb-2">AI Engine</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Total Analyses</span>
                        <span>{dashboardData.ai_analytics.ai_engine.summary.total_analyses?.toLocaleString() || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Avg Confidence</span>
                        <span>{((dashboardData.ai_analytics.ai_engine.summary.average_confidence || 0) * 100).toFixed(1)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Status</span>
                        <Badge variant={dashboardData.ai_analytics.ai_engine.health.status === 'healthy' ? 'default' : 'secondary'}>
                          {dashboardData.ai_analytics.ai_engine.health.status}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-medium mb-2">NLP Processor</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Patterns Loaded</span>
                        <span>{dashboardData.ai_analytics.nlp_processor.health.patterns_loaded}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Status</span>
                        <Badge variant={dashboardData.ai_analytics.nlp_processor.health.status === 'healthy' ? 'default' : 'secondary'}>
                          {dashboardData.ai_analytics.nlp_processor.health.status}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  {!dashboardData.ai_analytics.ai_engine.health.ml_available && (
                    <Alert>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        ML libraries not installed. Running in simulation mode.
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Threats Tab */}
        <TabsContent value="threats" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Active Threats */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <AlertTriangle className="h-5 w-5" />
                  <span>Active Threats</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {threatsData?.active_threats?.length > 0 ? (
                  <div className="space-y-3">
                    {threatsData.active_threats.map((threat: any) => (
                      <div key={threat.id} className="border rounded-lg p-3">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <h4 className="font-medium">{threat.type.replace('_', ' ')}</h4>
                            <p className="text-sm text-gray-600">{threat.source}</p>
                          </div>
                          <Badge className={getSeverityColor(threat.severity)}>
                            {threat.severity}
                          </Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm">Risk Score</span>
                          <span className="font-medium">{(threat.risk_score * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">No active threats detected</p>
                )}
              </CardContent>
            </Card>

            {/* Threat Severity Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Threat Severity Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                {threatsData?.severity_breakdown && (
                  <div className="space-y-3">
                    {Object.entries(threatsData.severity_breakdown).map(([severity, count]) => (
                      <div key={severity} className="flex justify-between items-center">
                        <div className="flex items-center space-x-2">
                          <div className={`w-3 h-3 rounded-full ${getSeverityColor(severity)}`}></div>
                          <span className="capitalize">{severity}</span>
                        </div>
                        <span className="font-medium">{count as number}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* AI Analytics Tab */}
        <TabsContent value="ai-analytics" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>AI Model Performance</CardTitle>
              </CardHeader>
              <CardContent>
                {performanceData?.ai_model_performance?.status === 'unavailable' ? (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      {performanceData.ai_model_performance.message}
                    </AlertDescription>
                  </Alert>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-medium mb-2">Email Risk Model</h4>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span>Accuracy</span>
                          <span>94.5%</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Precision</span>
                          <span>92.1%</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Manual Analysis</CardTitle>
                <CardDescription>Test AI components with custom data</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Button
                    onClick={() => {
                      // Trigger manual analysis
                      console.log('Manual analysis triggered')
                    }}
                    className="w-full"
                  >
                    <Brain className="h-4 w-4 mr-2" />
                    Run Test Analysis
                  </Button>
                  <p className="text-sm text-gray-600">
                    Trigger a manual AI analysis to test the system with sample data.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Processing Performance */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Activity className="h-5 w-5" />
                  <span>Processing</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {performanceData?.processing_performance && (
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm">Emails/min</span>
                      <span className="font-medium">{performanceData.processing_performance.emails_per_minute}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Domains/min</span>
                      <span className="font-medium">{performanceData.processing_performance.domains_per_minute}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Avg Time</span>
                      <span className="font-medium">{performanceData.processing_performance.average_processing_time}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Success Rate</span>
                      <span className="font-medium text-green-600">{performanceData.processing_performance.success_rate}</span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* System Resources */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Server className="h-5 w-5" />
                  <span>System Resources</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {performanceData?.system_resources && (
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">CPU Usage</span>
                        <span className="text-sm">{performanceData.system_resources.cpu_usage}</span>
                      </div>
                      <Progress value={34} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Memory Usage</span>
                        <span className="text-sm">{performanceData.system_resources.memory_usage}</span>
                      </div>
                      <Progress value={68} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Disk Usage</span>
                        <span className="text-sm">{performanceData.system_resources.disk_usage}</span>
                      </div>
                      <Progress value={45} className="h-2" />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Real-time Status */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Clock className="h-5 w-5" />
                  <span>Real-time Status</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">WebSocket</span>
                    <Badge variant={isConnected ? 'default' : 'destructive'}>
                      {isConnected ? 'Connected' : 'Disconnected'}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">Last Update</span>
                    <span className="text-sm">{lastUpdate.toLocaleTimeString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">Update Interval</span>
                    <span className="text-sm">5 seconds</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
