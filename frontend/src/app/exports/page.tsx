"use client"

import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Plus, Download, FileText, Database, Calendar, BarChart3, RefreshCw, Trash2 } from 'lucide-react'
import { toast } from "sonner"

interface Export {
  id: number
  name: string
  type: string
  status: string
  filters: string
  file_path?: string
  file_size?: number
  leads_count?: number
  progress: number
  created_at: string
  completed_at?: string
  expires_at?: string
}

interface ExportStats {
  total_exports: number
  pending_exports: number
  completed_exports: number
  failed_exports: number
  recent_exports_7d: number
  total_file_size_bytes: number
  status_breakdown: Record<string, number>
  type_breakdown: Record<string, number>
}

export default function ExportsPage() {
  const [exports, setExports] = useState<Export[]>([])
  const [stats, setStats] = useState<ExportStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newExport, setNewExport] = useState({
    name: '',
    type: 'csv',
    filters: '{}'
  })
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    fetchExports()
    fetchStats()
  }, [])

  const fetchExports = async () => {
    try {
      const response = await fetch('/api/exports')
      if (response.ok) {
        const data = await response.json()
        setExports(data)
      } else {
        toast.error('Failed to fetch exports')
      }
    } catch (error) {
      console.error('Error fetching exports:', error)
      toast.error('Error loading exports')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/exports/stats')
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Error fetching export stats:', error)
    }
  }

  const handleCreateExport = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!newExport.name.trim()) {
      toast.error('Export name is required')
      return
    }

    try {
      setIsCreating(true)

      const response = await fetch('/api/exports', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newExport),
      })

      if (response.ok) {
        toast.success('Export created successfully')
        setShowCreateForm(false)
        setNewExport({ name: '', type: 'csv', filters: '{}' })
        fetchExports()
        fetchStats()
      } else {
        const error = await response.text()
        toast.error(`Failed to create export: ${error}`)
      }
    } catch (error) {
      console.error('Error creating export:', error)
      toast.error('Error creating export')
    } finally {
      setIsCreating(false)
    }
  }

  const handleProcessExport = async (exportId: number) => {
    try {
      const response = await fetch(`/api/exports/${exportId}/process`, {
        method: 'POST'
      })

      if (response.ok) {
        toast.success('Export processing started')
        fetchExports()
        fetchStats()
      } else {
        toast.error('Failed to process export')
      }
    } catch (error) {
      console.error('Error processing export:', error)
      toast.error('Error processing export')
    }
  }

  const handleDownloadExport = async (exportItem: Export) => {
    try {
      const response = await fetch(`/api/exports/${exportItem.id}/download`)

      if (response.ok) {
        const data = await response.json()
        toast.success('Download link generated')
        // In a real implementation, this would trigger a file download
        console.log('Download info:', data)
      } else {
        toast.error('Failed to download export')
      }
    } catch (error) {
      console.error('Error downloading export:', error)
      toast.error('Error downloading export')
    }
  }

  const handleDeleteExport = async (exportId: number) => {
    if (!confirm('Are you sure you want to delete this export?')) {
      return
    }

    try {
      const response = await fetch(`/api/exports/${exportId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        toast.success('Export deleted successfully')
        fetchExports()
        fetchStats()
      } else {
        toast.error('Failed to delete export')
      }
    } catch (error) {
      console.error('Error deleting export:', error)
      toast.error('Error deleting export')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500'
      case 'pending': return 'bg-yellow-500'
      case 'processing': return 'bg-blue-500'
      case 'failed': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Data Exports</h1>
          <p className="text-muted-foreground">
            Export and download your OSINT lead data
          </p>
        </div>
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Export
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Exports</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_exports}</div>
              <p className="text-xs text-muted-foreground">
                {stats.recent_exports_7d} in last 7 days
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completed</CardTitle>
              <Download className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.completed_exports}</div>
              <p className="text-xs text-muted-foreground">
                Ready for download
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending</CardTitle>
              <RefreshCw className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.pending_exports}</div>
              <p className="text-xs text-muted-foreground">
                In queue
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Size</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatFileSize(stats.total_file_size_bytes)}</div>
              <p className="text-xs text-muted-foreground">
                All export files
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Create Export Form */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Export</CardTitle>
            <CardDescription>
              Export your lead data in various formats
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateExport} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="export-name">Export Name</Label>
                  <Input
                    id="export-name"
                    value={newExport.name}
                    onChange={(e) => setNewExport(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Enter export name"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="export-type">Export Type</Label>
                  <Select
                    value={newExport.type}
                    onValueChange={(value) => setNewExport(prev => ({ ...prev, type: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select export type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="csv">CSV</SelectItem>
                      <SelectItem value="json">JSON</SelectItem>
                      <SelectItem value="xlsx">Excel (XLSX)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex space-x-2">
                <Button type="submit" disabled={isCreating}>
                  {isCreating ? 'Creating...' : 'Create Export'}
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

      {/* Exports List */}
      <Tabs defaultValue="all" className="space-y-4">
        <TabsList>
          <TabsTrigger value="all">All Exports</TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
          <TabsTrigger value="pending">Pending</TabsTrigger>
          <TabsTrigger value="failed">Failed</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          {isLoading ? (
            <div className="text-center py-8">Loading exports...</div>
          ) : exports.length === 0 ? (
            <Card>
              <CardContent className="text-center py-8">
                <p className="text-muted-foreground mb-4">No exports found</p>
                <Button onClick={() => setShowCreateForm(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create your first export
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {exports.map((exportItem) => (
                <Card key={exportItem.id}>
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <CardTitle>{exportItem.name}</CardTitle>
                          <Badge
                            variant="secondary"
                            className={`text-white ${getStatusColor(exportItem.status)}`}
                          >
                            {exportItem.status}
                          </Badge>
                          <Badge variant="outline">
                            {exportItem.type.toUpperCase()}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {exportItem.status === 'pending' && (
                          <Button
                            size="sm"
                            onClick={() => handleProcessExport(exportItem.id)}
                          >
                            <RefreshCw className="h-4 w-4 mr-1" />
                            Process
                          </Button>
                        )}
                        {exportItem.status === 'completed' && (
                          <Button
                            size="sm"
                            onClick={() => handleDownloadExport(exportItem)}
                          >
                            <Download className="h-4 w-4 mr-1" />
                            Download
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDeleteExport(exportItem.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Progress</p>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full transition-all"
                              style={{ width: `${exportItem.progress}%` }}
                            />
                          </div>
                          <span className="text-xs">{exportItem.progress}%</span>
                        </div>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Leads</p>
                        <p className="font-medium">{exportItem.leads_count || 0}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">File Size</p>
                        <p className="font-medium">
                          {exportItem.file_size ? formatFileSize(exportItem.file_size) : 'N/A'}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Created</p>
                        <p className="font-medium">{formatDate(exportItem.created_at)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Expires</p>
                        <p className="font-medium">
                          {exportItem.expires_at ? formatDate(exportItem.expires_at) : 'N/A'}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="completed">
          <div className="grid gap-4">
            {exports.filter(e => e.status === 'completed').map((exportItem) => (
              <Card key={exportItem.id}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle>{exportItem.name}</CardTitle>
                        <Badge variant="secondary" className="text-white bg-green-500">
                          {exportItem.status}
                        </Badge>
                        <Badge variant="outline">
                          {exportItem.type.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleDownloadExport(exportItem)}
                      >
                        <Download className="h-4 w-4 mr-1" />
                        Download
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDeleteExport(exportItem.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Leads</p>
                      <p className="font-medium">{exportItem.leads_count || 0}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">File Size</p>
                      <p className="font-medium">
                        {exportItem.file_size ? formatFileSize(exportItem.file_size) : 'N/A'}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Completed</p>
                      <p className="font-medium">
                        {exportItem.completed_at ? formatDate(exportItem.completed_at) : 'N/A'}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Expires</p>
                      <p className="font-medium">
                        {exportItem.expires_at ? formatDate(exportItem.expires_at) : 'N/A'}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="pending">
          <div className="grid gap-4">
            {exports.filter(e => e.status === 'pending').map((exportItem) => (
              <Card key={exportItem.id}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle>{exportItem.name}</CardTitle>
                        <Badge variant="secondary" className="text-white bg-yellow-500">
                          {exportItem.status}
                        </Badge>
                        <Badge variant="outline">
                          {exportItem.type.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleProcessExport(exportItem.id)}
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Process
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDeleteExport(exportItem.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Created</p>
                      <p className="font-medium">{formatDate(exportItem.created_at)}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Type</p>
                      <p className="font-medium">{exportItem.type.toUpperCase()}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="failed">
          <div className="grid gap-4">
            {exports.filter(e => e.status === 'failed').map((exportItem) => (
              <Card key={exportItem.id}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle>{exportItem.name}</CardTitle>
                        <Badge variant="secondary" className="text-white bg-red-500">
                          {exportItem.status}
                        </Badge>
                        <Badge variant="outline">
                          {exportItem.type.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleProcessExport(exportItem.id)}
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Retry
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDeleteExport(exportItem.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Failed</p>
                      <p className="font-medium">{formatDate(exportItem.created_at)}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Type</p>
                      <p className="font-medium">{exportItem.type.toUpperCase()}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
