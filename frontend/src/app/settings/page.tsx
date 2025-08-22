"use client"

import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import { Settings as SettingsIcon, Save, RotateCcw, Download, Upload, AlertTriangle } from 'lucide-react'
import { toast } from "sonner"

interface Setting {
  id: number
  key: string
  value: any
  category: string
  description: string
  data_type: string
  is_public: boolean
  created_at: string
  updated_at?: string
}

interface SettingCategory {
  [key: string]: Setting[]
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Setting[]>([])
  const [settingsByCategory, setSettingsByCategory] = useState<SettingCategory>({})
  const [categories, setCategories] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setSaving] = useState(false)
  const [isResetting, setIsResetting] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [pendingChanges, setPendingChanges] = useState<Record<string, any>>({})

  useEffect(() => {
    fetchSettings()
    fetchCategories()
  }, [])

  const fetchSettings = async () => {
    try {
      const response = await fetch('/api/settings')
      if (response.ok) {
        const data = await response.json()
        setSettings(data)

        // Group by category
        const grouped = data.reduce((acc: SettingCategory, setting: Setting) => {
          const category = setting.category || 'general'
          if (!acc[category]) acc[category] = []
          acc[category].push(setting)
          return acc
        }, {})

        setSettingsByCategory(grouped)
      } else {
        toast.error('Failed to fetch settings')
      }
    } catch (error) {
      console.error('Error fetching settings:', error)
      toast.error('Error loading settings')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchCategories = async () => {
    try {
      const response = await fetch('/api/settings/categories')
      if (response.ok) {
        const data = await response.json()
        setCategories(data)
      }
    } catch (error) {
      console.error('Error fetching categories:', error)
    }
  }

  const handleSettingChange = (key: string, value: any) => {
    setPendingChanges(prev => ({
      ...prev,
      [key]: value
    }))
    setHasChanges(true)
  }

  const handleSaveSettings = async () => {
    if (!hasChanges || Object.keys(pendingChanges).length === 0) {
      return
    }

    try {
      setSaving(true)

      const response = await fetch('/api/settings/bulk', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(pendingChanges),
      })

      if (response.ok) {
        const result = await response.json()
        toast.success(`Settings saved: ${result.updated_count} updated, ${result.created_count} created`)

        // Reset changes
        setPendingChanges({})
        setHasChanges(false)

        // Refresh settings
        fetchSettings()
      } else {
        const error = await response.text()
        toast.error(`Failed to save settings: ${error}`)
      }
    } catch (error) {
      console.error('Error saving settings:', error)
      toast.error('Error saving settings')
    } finally {
      setSaving(false)
    }
  }

  const handleResetToDefaults = async () => {
    if (!confirm('Are you sure you want to reset all settings to defaults? This action cannot be undone.')) {
      return
    }

    try {
      setIsResetting(true)

      const response = await fetch('/api/settings/defaults/reset')

      if (response.ok) {
        const result = await response.json()
        toast.success(`Settings reset: ${result.created_count} default settings restored`)

        // Reset changes
        setPendingChanges({})
        setHasChanges(false)

        // Refresh settings
        fetchSettings()
        fetchCategories()
      } else {
        toast.error('Failed to reset settings')
      }
    } catch (error) {
      console.error('Error resetting settings:', error)
      toast.error('Error resetting settings')
    } finally {
      setIsResetting(false)
    }
  }

  const handleExportSettings = async () => {
    try {
      const response = await fetch('/api/settings/export/all')

      if (response.ok) {
        const data = await response.json()

        // Create and download file
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `osint-settings-${new Date().toISOString().split('T')[0]}.json`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)

        toast.success('Settings exported successfully')
      } else {
        toast.error('Failed to export settings')
      }
    } catch (error) {
      console.error('Error exporting settings:', error)
      toast.error('Error exporting settings')
    }
  }

  const renderSettingInput = (setting: Setting) => {
    const currentValue = pendingChanges[setting.key] !== undefined
      ? pendingChanges[setting.key]
      : setting.value

    switch (setting.data_type) {
      case 'boolean':
        return (
          <Switch
            checked={currentValue === true || currentValue === 'true'}
            onCheckedChange={(checked) => handleSettingChange(setting.key, checked)}
          />
        )

      case 'number':
        return (
          <Input
            type="number"
            value={currentValue}
            onChange={(e) => handleSettingChange(setting.key, parseFloat(e.target.value) || 0)}
            className="max-w-xs"
          />
        )

      case 'json':
        return (
          <Textarea
            value={typeof currentValue === 'object' ? JSON.stringify(currentValue, null, 2) : currentValue}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value)
                handleSettingChange(setting.key, parsed)
              } catch {
                handleSettingChange(setting.key, e.target.value)
              }
            }}
            rows={4}
            className="font-mono text-sm"
          />
        )

      default:
        return (
          <Input
            value={String(currentValue)}
            onChange={(e) => handleSettingChange(setting.key, e.target.value)}
            className="max-w-lg"
          />
        )
    }
  }

  const formatCategoryName = (category: string) => {
    return category.charAt(0).toUpperCase() + category.slice(1).replace('_', ' ')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground">
            Configure system preferences and application behavior
          </p>
        </div>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            onClick={handleExportSettings}
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button
            variant="outline"
            onClick={handleResetToDefaults}
            disabled={isResetting}
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            {isResetting ? 'Resetting...' : 'Reset to Defaults'}
          </Button>
          <Button
            onClick={handleSaveSettings}
            disabled={!hasChanges || isSaving}
          >
            <Save className="h-4 w-4 mr-2" />
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      {/* Unsaved Changes Warning */}
      {hasChanges && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <p className="text-yellow-800">
                You have unsaved changes. Remember to save your settings.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Settings Content */}
      {isLoading ? (
        <div className="text-center py-8">Loading settings...</div>
      ) : (
        <Tabs defaultValue={categories[0] || 'general'} className="space-y-4">
          <TabsList className="grid w-full grid-cols-2 lg:grid-cols-6">
            {categories.map((category) => (
              <TabsTrigger key={category} value={category}>
                {formatCategoryName(category)}
              </TabsTrigger>
            ))}
          </TabsList>

          {categories.map((category) => (
            <TabsContent key={category} value={category} className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>{formatCategoryName(category)} Settings</CardTitle>
                  <CardDescription>
                    Configure {category} related preferences and behavior
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {settingsByCategory[category]?.map((setting) => (
                    <div key={setting.key} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="space-y-1">
                          <Label htmlFor={setting.key} className="text-sm font-medium">
                            {setting.key.split('.').pop()?.replace(/_/g, ' ')}
                          </Label>
                          {setting.description && (
                            <p className="text-xs text-muted-foreground">
                              {setting.description}
                            </p>
                          )}
                          <div className="flex items-center space-x-2">
                            <Badge variant="outline" className="text-xs">
                              {setting.data_type}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {setting.key}
                            </span>
                          </div>
                        </div>
                        <div className="flex-shrink-0">
                          {renderSettingInput(setting)}
                        </div>
                      </div>

                      {pendingChanges[setting.key] !== undefined && (
                        <div className="text-xs text-blue-600 bg-blue-50 p-2 rounded">
                          Changed from: {String(setting.value)}
                        </div>
                      )}
                    </div>
                  )) || (
                    <p className="text-center text-muted-foreground py-8">
                      No settings found in this category
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          ))}

          {/* System Info Tab */}
          <TabsContent value="system" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>System Information</CardTitle>
                <CardDescription>
                  View system status and configuration details
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h4 className="font-medium">Application</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Version:</span>
                        <span>1.0.0</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Environment:</span>
                        <span>Development</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Build Date:</span>
                        <span>2025-01-22</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h4 className="font-medium">Database</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Type:</span>
                        <span>SQLite</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Status:</span>
                        <Badge variant="outline" className="bg-green-50 text-green-700">
                          Connected
                        </Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Total Settings:</span>
                        <span>{settings.length}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}