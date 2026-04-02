"use client"

import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArrowLeft, Play, Pause, Edit, BarChart3, Users, Target, Calendar, Settings, Download } from 'lucide-react'
import { toast } from "sonner"
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

interface Lead {
  id: number
  email: string
  name: string
  company: string
  job_title: string
  confidence_score: number
  verification_status: string
  created_at: string
}

interface CampaignDetailsProps {
  campaign: Campaign
  onBack: () => void
  onUpdate: () => void
}

export default function CampaignDetails({ campaign, onBack, onUpdate }: CampaignDetailsProps) {
  const [leads, setLeads] = useState<Lead[]>([])
  const [stats, setStats] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    fetchCampaignLeads()
  }, [campaign.id])

  const fetchCampaignLeads = async () => {
    try {
      const data = await api.getLeads({ campaign_id: String(campaign.id) })
      setLeads(data.data.map((lead) => ({
        id: Number(lead.id),
        email: lead.email,
        name: lead.name || '',
        company: lead.company || '',
        job_title: lead.job_title || lead.title || '',
        confidence_score: Number(lead.confidence_score || lead.score || 0),
        verification_status: lead.verification_status,
        created_at: lead.created_at,
      })))
    } catch (error) {
      console.error('Error fetching campaign leads:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleStart = async () => {
    try {
      await api.startCampaign(String(campaign.id))
      toast.success('Campaign started successfully')
      onUpdate()
    } catch (error) {
      console.error('Error starting campaign:', error)
      toast.error('Error starting campaign')
    }
  }

  const handlePause = async () => {
    try {
      await api.pauseCampaign(String(campaign.id))
      toast.success('Campaign paused successfully')
      onUpdate()
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  const getVerificationColor = (status: string) => {
    switch (status) {
      case 'verified': return 'text-green-600 bg-green-100'
      case 'pending': return 'text-yellow-600 bg-yellow-100'
      case 'failed': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const sources = JSON.parse(campaign.sources || '[]')
  const filterCriteria = JSON.parse(campaign.filter_criteria || '{}')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="outline" size="sm" onClick={onBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-3xl font-bold">{campaign.name}</h1>
              <Badge
                variant="secondary"
                className={`text-white ${getStatusColor(campaign.status)}`}
              >
                {campaign.status}
              </Badge>
            </div>
            <p className="text-muted-foreground">{campaign.description}</p>
          </div>
        </div>

        <div className="flex space-x-2">
          {campaign.status === 'draft' && (
            <Button onClick={handleStart}>
              <Play className="h-4 w-4 mr-2" />
              Start Campaign
            </Button>
          )}
          {campaign.status === 'active' && (
            <Button variant="outline" onClick={handlePause}>
              <Pause className="h-4 w-4 mr-2" />
              Pause
            </Button>
          )}
          <Button variant="outline">
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button variant="outline">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Progress</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{campaign.progress}%</div>
            <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${campaign.progress}%` }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Leads Found</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{campaign.leads_found}</div>
            <p className="text-xs text-muted-foreground">
              of {campaign.leads_target} target
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {campaign.leads_target > 0 ? Math.round((campaign.leads_found / campaign.leads_target) * 100) : 0}%
            </div>
            <p className="text-xs text-muted-foreground">
              vs target goal
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Runtime</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {campaign.started_at ?
                Math.ceil((new Date().getTime() - new Date(campaign.started_at).getTime()) / (1000 * 60 * 60 * 24)) :
                0
              }d
            </div>
            <p className="text-xs text-muted-foreground">
              {campaign.status === 'active' ? 'running' : 'total time'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Information */}
      <Tabs defaultValue="leads" className="space-y-4">
        <TabsList>
          <TabsTrigger value="leads">Leads ({leads.length})</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="leads" className="space-y-4">
          {isLoading ? (
            <div className="text-center py-8">Loading leads...</div>
          ) : leads.length === 0 ? (
            <Card>
              <CardContent className="text-center py-8">
                <p className="text-muted-foreground">No leads found yet</p>
                {campaign.status === 'draft' && (
                  <p className="text-sm text-muted-foreground mt-2">
                    Start the campaign to begin finding leads
                  </p>
                )}
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold">Found Leads</h3>
                <Button variant="outline" size="sm">
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
              </div>

              <div className="grid gap-4">
                {leads.map((lead) => (
                  <Card key={lead.id}>
                    <CardContent className="pt-4">
                      <div className="flex justify-between items-start">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <h4 className="font-medium">{lead.name || 'Unknown'}</h4>
                            <Badge
                              variant="secondary"
                              className={getVerificationColor(lead.verification_status)}
                            >
                              {lead.verification_status}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">{lead.email}</p>
                          <p className="text-sm">
                            {lead.job_title} at {lead.company}
                          </p>
                        </div>
                        <div className="text-right space-y-1">
                          <div className="text-sm font-medium">
                            {lead.confidence_score}% confidence
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {formatDate(lead.created_at)}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        <TabsContent value="settings">
          <div className="grid gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Campaign Configuration</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Type</label>
                    <p className="font-medium">{campaign.type}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Target Leads</label>
                    <p className="font-medium">{campaign.leads_target}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Created</label>
                    <p className="font-medium">{formatDate(campaign.created_at)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Status</label>
                    <p className="font-medium">{campaign.status}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Sources ({sources.length})</CardTitle>
              </CardHeader>
              <CardContent>
                {sources.length > 0 ? (
                  <div className="space-y-2">
                    {sources.map((sourceId: number, index: number) => (
                      <Badge key={index} variant="outline">
                        Source ID: {sourceId}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground">No sources configured</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Filter Criteria</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(filterCriteria).map(([key, value]) => (
                    <div key={key}>
                      <label className="text-sm font-medium text-muted-foreground capitalize">
                        {key.replace('_', ' ')}
                      </label>
                      <p className="font-medium">{String(value) || 'Not specified'}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="activity">
          <Card>
            <CardHeader>
              <CardTitle>Campaign Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <div>
                    <p className="font-medium">Campaign created</p>
                    <p className="text-sm text-muted-foreground">{formatDate(campaign.created_at)}</p>
                  </div>
                </div>

                {campaign.started_at && (
                  <div className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <div>
                      <p className="font-medium">Campaign started</p>
                      <p className="text-sm text-muted-foreground">{formatDate(campaign.started_at)}</p>
                    </div>
                  </div>
                )}

                {campaign.completed_at && (
                  <div className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
                    <div>
                      <p className="font-medium">Campaign completed</p>
                      <p className="text-sm text-muted-foreground">{formatDate(campaign.completed_at)}</p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}