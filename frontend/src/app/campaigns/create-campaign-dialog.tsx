"use client"

import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Checkbox } from "@/components/ui/checkbox"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { api } from '@/lib/api'

interface Source {
  id: string
  name: string
  type: string
  status: string
  description?: string
}

interface CreateCampaignDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export default function CreateCampaignDialog({ open, onOpenChange, onSuccess }: CreateCampaignDialogProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    type: 'manual',
    sources: [] as string[],
    filter_criteria: {
      keywords: '',
      industries: '',
      locations: '',
      job_titles: '',
      company_size: '',
      exclude_keywords: ''
    },
    leads_target: 100
  })

  const [sources, setSources] = useState<Source[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (open) {
      fetchSources()
    }
  }, [open])

  const fetchSources = async () => {
    try {
      setIsLoading(true)
      const data = await api.getSources()
      setSources(data.data.filter((source) => source.status === 'active'))
    } catch (error) {
      console.error('Error fetching sources:', error)
      toast.error('Failed to load sources')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name.trim()) {
      toast.error('Campaign name is required')
      return
    }

    if (formData.sources.length === 0) {
      toast.error('At least one source must be selected')
      return
    }

    try {
      setIsSubmitting(true)
      await api.createCampaign({
        name: formData.name,
        description: formData.description,
        filter_criteria: {
          ...formData.filter_criteria,
          type: formData.type,
        },
        target_count: formData.leads_target,
        target_sources: formData.sources,
      })
      toast.success('Campaign created successfully')
      onSuccess()
      onOpenChange(false)

      setFormData({
        name: '',
        description: '',
        type: 'manual',
        sources: [],
        filter_criteria: {
          keywords: '',
          industries: '',
          locations: '',
          job_titles: '',
          company_size: '',
          exclude_keywords: ''
        },
        leads_target: 100
      })
    } catch (error) {
      console.error('Error creating campaign:', error)
      toast.error(error instanceof Error ? error.message : 'Error creating campaign')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSourceToggle = (sourceId: string) => {
    setFormData(prev => ({
      ...prev,
      sources: prev.sources.includes(sourceId)
        ? prev.sources.filter(id => id !== sourceId)
        : [...prev.sources, sourceId]
    }))
  }

  const handleFilterChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      filter_criteria: {
        ...prev.filter_criteria,
        [field]: value
      }
    }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Campaign</DialogTitle>
          <DialogDescription>
            Set up a new OSINT search campaign to find targeted leads
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Campaign Name *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Enter campaign name"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="type">Campaign Type</Label>
              <Select
                value={formData.type}
                onValueChange={(value) => setFormData(prev => ({ ...prev, type: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select campaign type" />
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
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Describe the campaign objectives and target audience"
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="leads_target">Target Leads</Label>
            <Input
              id="leads_target"
              type="number"
              min="1"
              max="10000"
              value={formData.leads_target}
              onChange={(e) => setFormData(prev => ({ ...prev, leads_target: parseInt(e.target.value) || 100 }))}
              placeholder="Number of leads to find"
            />
          </div>

          {/* Source Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Select Sources *</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="text-center py-4">Loading sources...</div>
              ) : sources.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground">
                  No active sources available
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {sources.map((source) => (
                    <div key={source.id} className="flex items-center space-x-3 p-3 border rounded-lg">
                      <Checkbox
                        id={`source-${source.id}`}
                        checked={formData.sources.includes(source.id)}
                        onCheckedChange={() => handleSourceToggle(source.id)}
                      />
                      <div className="flex-1">
                        <Label
                          htmlFor={`source-${source.id}`}
                          className="cursor-pointer font-medium"
                        >
                          {source.name}
                        </Label>
                        <p className="text-sm text-muted-foreground">
                          {source.description}
                        </p>
                        <Badge variant="outline" className="mt-1">
                          {source.type}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {formData.sources.length > 0 && (
                <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-700">
                    {formData.sources.length} source(s) selected
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Filter Criteria */}
          <Card>
            <CardHeader>
              <CardTitle>Search Filters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="keywords">Keywords</Label>
                  <Input
                    id="keywords"
                    value={formData.filter_criteria.keywords}
                    onChange={(e) => handleFilterChange('keywords', e.target.value)}
                    placeholder="e.g., software, tech, startup"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="industries">Industries</Label>
                  <Input
                    id="industries"
                    value={formData.filter_criteria.industries}
                    onChange={(e) => handleFilterChange('industries', e.target.value)}
                    placeholder="e.g., Technology, Finance, Healthcare"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="locations">Locations</Label>
                  <Input
                    id="locations"
                    value={formData.filter_criteria.locations}
                    onChange={(e) => handleFilterChange('locations', e.target.value)}
                    placeholder="e.g., San Francisco, New York, Remote"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="job_titles">Job Titles</Label>
                  <Input
                    id="job_titles"
                    value={formData.filter_criteria.job_titles}
                    onChange={(e) => handleFilterChange('job_titles', e.target.value)}
                    placeholder="e.g., CEO, CTO, Engineer, Manager"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="company_size">Company Size</Label>
                  <Input
                    id="company_size"
                    value={formData.filter_criteria.company_size}
                    onChange={(e) => handleFilterChange('company_size', e.target.value)}
                    placeholder="e.g., 1-10, 11-50, 51-200, 200+"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="exclude_keywords">Exclude Keywords</Label>
                  <Input
                    id="exclude_keywords"
                    value={formData.filter_criteria.exclude_keywords}
                    onChange={(e) => handleFilterChange('exclude_keywords', e.target.value)}
                    placeholder="Keywords to exclude from results"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            onClick={handleSubmit}
            disabled={isSubmitting || !formData.name.trim() || formData.sources.length === 0}
          >
            {isSubmitting ? 'Creating...' : 'Create Campaign'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}