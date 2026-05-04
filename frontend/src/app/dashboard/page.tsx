'use client'

import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { AlertCircle, CheckCircle, Clock, TrendingUp, Users, Target } from 'lucide-react'
import { api } from '@/lib/api'
import { formatNumber } from '@/lib/utils'

export default function DashboardPage() {
  const { data: kpis, isLoading: kpisLoading, error: kpisError } = useQuery({
    queryKey: ['kpis'],
    queryFn: api.getKPIs,
    refetchInterval: 30000 // Refresh every 30 seconds
  })

  const { data: leads, isLoading: leadsLoading } = useQuery({
    queryKey: ['leads', { limit: 5 }],
    queryFn: () => api.getLeads({ limit: 5 }),
  })

  if (kpisLoading) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold tracking-tight mb-6">Dashboard</h1>
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (kpisError) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold tracking-tight mb-6">Dashboard</h1>
        <div className="flex items-center gap-2 text-red-600 mb-4">
          <AlertCircle className="h-5 w-5" />
          <span>Feil ved lasting av dashboard data</span>
        </div>
        <p className="text-gray-600">Prøv å laste siden på nytt</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Oversikt over OSINT lead generering aktivitet</p>
      </div>

      <Separator />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Leads (7 dager)</CardTitle>
            <Users className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(kpis?.leads7d || 0)}</div>
            <p className="text-xs text-muted-foreground">Nye leads denne uken</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Søk (7 dager)</CardTitle>
            <Target className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(kpis?.hits7d || 0)}</div>
            <p className="text-xs text-muted-foreground">Søketreff denne uken</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Konverteringsrate</CardTitle>
            <TrendingUp className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(kpis?.conversion_rate || 0).toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">Av totale søk</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Eksporter (7 dager)</CardTitle>
            <CheckCircle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(kpis?.exports7d || 0)}</div>
            <p className="text-xs text-muted-foreground">Fullførte eksporter</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Totale kilder</CardTitle>
            <Clock className="h-4 w-4 text-indigo-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(kpis?.total_sources || 0)}</div>
            <p className="text-xs text-muted-foreground">Konfigurerte kilder</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Aktive kilder</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(kpis?.active_sources || 0)}</div>
            <p className="text-xs text-muted-foreground">Kilder i bruk</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Leads */}
      <Card>
        <CardHeader>
          <CardTitle>Siste leads</CardTitle>
          <CardDescription>De 5 nyeste genererte leads</CardDescription>
        </CardHeader>
        <CardContent>
          {leadsLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="animate-pulse flex items-center space-x-4">
                  <div className="rounded-full bg-gray-200 h-10 w-10"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : leads?.data && leads.data.length > 0 ? (
            <div className="space-y-4">
              {leads.data.slice(0, 5).map((lead) => (
                <div key={lead.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                      <Users className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium">{lead.name}</p>
                      <p className="text-sm text-gray-600">{lead.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge variant={lead.verification_status === 'verified' ? 'default' : 'secondary'}>
                      {lead.verification_status}
                    </Badge>
                    <span className="text-sm text-gray-500">
                      Score: {lead.score || 0}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6 text-gray-500">
              <Users className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Ingen leads funnet</p>
              <p className="text-sm">Start din første søkekampanje for å generere leads</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle>System status</CardTitle>
          <CardDescription>Aktuelle systemtilstand</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm">Backend API</span>
            <Badge variant="default" className="bg-green-100 text-green-800">
              <CheckCircle className="h-3 w-3 mr-1" />
              Aktiv
            </Badge>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm">Database</span>
            <Badge variant="default" className="bg-green-100 text-green-800">
              <CheckCircle className="h-3 w-3 mr-1" />
              Tilkoblet
            </Badge>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm">Aktive kilder</span>
            <Badge variant="default" className="bg-blue-100 text-blue-800">
              {kpis?.active_sources || 0} av {kpis?.total_sources || 0}
            </Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}