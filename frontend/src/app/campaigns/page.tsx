"use client"

import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Plus, Play, Pause, Settings, BarChart3, Calendar, Target } from 'lucide-react'
import { toast } from "sonner"
import CreateCampaignDialog from './create-campaign-dialog'
import CampaignDetails from './campaign-details'
import { api } from '@/lib/api'

interface Campaign {
  id: string
  name: string
  description: string
  status: string
  type: string
  sources: string
  filter_criteria: string
  leads_target: number
  leads_found: number
  progress: number
  created_at: string
  started_at?: string
  completed_at?: string
}

interface CampaignStats {
  total_campaigns: number
  active_campaigns: number
  completed_campaigns: number
  draft_campaigns: number
  total_leads_generated: number
  avg_completion_rate: number
  status_breakdown: Record<string, number>
  type_breakdown: Record<string, number>
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [stats, setStats] = useState<CampaignStats | null>(null)
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    fetchCampaigns()
    fetchStats()
  }, [])

  const mapCampaign = (campaign: any): Campaign => ({
    id: String(campaign.id),
    name: campaign.name,
    description: campaign.description || '',
    status: campaign.status,
    type: String(campaign.filter_criteria?.type || 'targeted'),
    sources: JSON.stringify(campaign.target_sources || []),
    filter_criteria: JSON.stringify(campaign.filter_criteria || {}),
    leads_target: Number(campaign.target_count || 0),
    leads_found: Number(campaign.leads_count || 0),
    progress: Number(campaign.progress || 0),
    created_at: campaign.created_at,
    started_at: campaign.started_at,
    completed_at: campaign.ended_at,
  })

  const fetchCampaigns = async () => {
    try {
      const data = await api.getCampaigns()
      setCampaigns(data.data.map(mapCampaign))
    } catch (error) {
      console.error('Error fetching campaigns:', error)
      toast.error('Error loading campaigns')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const data = await api.getCampaignStatistics()
      const statusBreakdown = data.campaigns_by_status || {}
      setStats({
        total_campaigns: Number(data.total_campaigns || 0),
        active_campaigns: Number(data.active_campaigns || 0),
        completed_campaigns: Number(statusBreakdown.completed || 0),
        draft_campaigns: Number(statusBreakdown.draft || 0),
        total_leads_generated: Number(data.total_leads_generated || 0),
        avg_completion_rate: Math.round(Number(data.success_rate || 0) * 100),
        status_breakdown: statusBreakdown,
        type_breakdown: data.campaigns_by_type || {},
      })
    } catch (error) {
      console.error('Error fetching campaign stats:', error)
    }
  }

  const handleStartCampaign = async (campaignId: string) => {
    try {
      await api.startCampaign(campaignId)
      toast.success('Campaign started successfully')
      fetchCampaigns()
      fetchStats()
    } catch (error) {
      console.error('Error starting campaign:', error)
      toast.error('Error starting campaign')
    }
  }

  const handlePauseCampaign = async (campaignId: string) => {
    try {
      await api.pauseCampaign(campaignId)
      toast.success('Campaign paused successfully')
      fetchCampaigns()
      fetchStats()
    } catch (error) {
      console.error('Error pausing campaign:', error)
      toast.error('Error pausing campaign')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500'
      case 'completed': return 'bg-blue-500'
      case 'paused': return 'bg-yellow-500'
      case 'draft': return 'bg-gray-500'
      default: return 'bg-gray-500'
    }
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString()
  }

  if (selectedCampaign) {
    return (
      <CampaignDetails
        campaign={selectedCampaign}
        onBack={() => setSelectedCampaign(null)}
        onUpdate={fetchCampaigns}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Campaigns</h1>
          <p className="text-muted-foreground">
            Manage and monitor your OSINT search campaigns
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Campaign
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Campaigns</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_campaigns}</div>
              <p className="text-xs text-muted-foreground">
                {stats.active_campaigns} currently active
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Campaigns</CardTitle>
              <Play className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.active_campaigns}</div>
              <p className="text-xs text-muted-foreground">
                Running searches
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Leads Generated</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_leads_generated}</div>
              <p className="text-xs text-muted-foreground">
                From all campaigns
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completion Rate</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.avg_completion_rate}%</div>
              <p className="text-xs text-muted-foreground">
                Average success rate
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Campaigns List */}
      <Tabs defaultValue="all" className="space-y-4">
        <TabsList>
          <TabsTrigger value="all">All Campaigns</TabsTrigger>
          <TabsTrigger value="active">Active</TabsTrigger>
          <TabsTrigger value="draft">Draft</TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          {isLoading ? (
            <div className="text-center py-8">Laster kampanjer...</div>
          ) : campaigns.length === 0 ? (
            <Card>
              <CardContent className="text-center py-16">
                <p className="text-4xl mb-4">📢</p>
                <p className="text-muted-foreground mb-4">Ingen kampanjer ennå</p>
                <Button onClick={() => setShowCreateDialog(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Opprett din første kampanje
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {campaigns.map((campaign) => (
                <Card key={campaign.id} className="cursor-pointer hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <CardTitle
                            className="hover:text-blue-600 transition-colors"
                            onClick={() => setSelectedCampaign(campaign)}
                          >
                            {campaign.name}
                          </CardTitle>
                          <Badge
                            variant="secondary"
                            className={`text-white ${getStatusColor(campaign.status)}`}
                          >
                            {campaign.status}
                          </Badge>
                        </div>
                        <CardDescription>{campaign.description}</CardDescription>
                      </div>
                      <div className="flex gap-2">
                        {campaign.status === 'draft' && (
                          <Button
                            size="sm"
                            onClick={() => handleStartCampaign(campaign.id)}
                          >
                            <Play className="h-4 w-4 mr-1" />
                            Start
                          </Button>
                        )}
                        {campaign.status === 'active' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handlePauseCampaign(campaign.id)}
                          >
                            <Pause className="h-4 w-4 mr-1" />
                            Pause
                          </Button>
                        )}
                        <Button size="sm" variant="outline">
                          <Settings className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Type</p>
                        <p className="font-medium">{campaign.type}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Progress</p>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full transition-all"
                              style={{ width: `${campaign.progress}%` }}
                            />
                          </div>
                          <span className="text-xs">{campaign.progress}%</span>
                        </div>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Leads</p>
                        <p className="font-medium">{campaign.leads_found} / {campaign.leads_target}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Created</p>
                        <p className="font-medium">{formatDate(campaign.created_at)}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="active">
          <div className="grid gap-4">
            {campaigns.filter(c => c.status === 'active').map((campaign) => (
              <Card key={campaign.id} className="cursor-pointer hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle
                          className="hover:text-blue-600 transition-colors"
                          onClick={() => setSelectedCampaign(campaign)}
                        >
                          {campaign.name}
                        </CardTitle>
                        <Badge variant="secondary" className="text-white bg-green-500">
                          {campaign.status}
                        </Badge>
                      </div>
                      <CardDescription>{campaign.description}</CardDescription>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handlePauseCampaign(campaign.id)}
                    >
                      <Pause className="h-4 w-4 mr-1" />
                      Pause
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Type</p>
                      <p className="font-medium">{campaign.type}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Progress</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-green-600 h-2 rounded-full transition-all"
                            style={{ width: `${campaign.progress}%` }}
                          />
                        </div>
                        <span className="text-xs">{campaign.progress}%</span>
                      </div>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Leads</p>
                      <p className="font-medium">{campaign.leads_found} / {campaign.leads_target}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Started</p>
                      <p className="font-medium">{campaign.started_at ? formatDate(campaign.started_at) : 'N/A'}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="draft">
          <div className="grid gap-4">
            {campaigns.filter(c => c.status === 'draft').map((campaign) => (
              <Card key={campaign.id} className="cursor-pointer hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle
                          className="hover:text-blue-600 transition-colors"
                          onClick={() => setSelectedCampaign(campaign)}
                        >
                          {campaign.name}
                        </CardTitle>
                        <Badge variant="secondary" className="text-white bg-gray-500">
                          {campaign.status}
                        </Badge>
                      </div>
                      <CardDescription>{campaign.description}</CardDescription>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleStartCampaign(campaign.id)}
                    >
                      <Play className="h-4 w-4 mr-1" />
                      Start
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Type</p>
                      <p className="font-medium">{campaign.type}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Target</p>
                      <p className="font-medium">{campaign.leads_target} leads</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Sources</p>
                      <p className="font-medium">
                        {JSON.parse(campaign.sources || '[]').length} selected
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Created</p>
                      <p className="font-medium">{formatDate(campaign.created_at)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="completed">
          <div className="grid gap-4">
            {campaigns.filter(c => c.status === 'completed').map((campaign) => (
              <Card key={campaign.id} className="cursor-pointer hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle
                          className="hover:text-blue-600 transition-colors"
                          onClick={() => setSelectedCampaign(campaign)}
                        >
                          {campaign.name}
                        </CardTitle>
                        <Badge variant="secondary" className="text-white bg-blue-500">
                          {campaign.status}
                        </Badge>
                      </div>
                      <CardDescription>{campaign.description}</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Type</p>
                      <p className="font-medium">{campaign.type}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Success Rate</p>
                      <p className="font-medium">{campaign.progress}%</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Leads Found</p>
                      <p className="font-medium">{campaign.leads_found} / {campaign.leads_target}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Completed</p>
                      <p className="font-medium">{campaign.completed_at ? formatDate(campaign.completed_at) : 'N/A'}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Create Campaign Dialog */}
      <CreateCampaignDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={() => {
          fetchCampaigns()
          fetchStats()
        }}
      />
    </div>
  )
}