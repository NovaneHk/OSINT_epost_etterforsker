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
import { api } from "@/lib/api"

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

function N8nAutomatiseringPanel() {
  const [webhookUrl, setWebhookUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [status, setStatus] = useState<'idle' | 'ok' | 'error'>('idle')
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const authHeader = () => {
    const token = typeof window !== 'undefined' ? window.localStorage.getItem('accessToken') : ''
    return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
  }

  const testConnection = async () => {
    setStatus('idle')
    try {
      const res = await fetch(`${apiBase}/api/integrations/status`, { headers: authHeader() })
      if (res.ok) { setStatus('ok'); toast.success('Tilkobling OK') }
      else { setStatus('error'); toast.error('Tilkobling mislyktes') }
    } catch { setStatus('error'); toast.error('Nettverksfeil') }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="n8n-webhook">n8n Webhook URL</Label>
        <Input
          id="n8n-webhook"
          placeholder="https://your-n8n.example.com/webhook/..."
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="n8n-apikey">API-nøkkel</Label>
        <Input
          id="n8n-apikey"
          type="password"
          placeholder="n8n API key"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
      </div>
      <Button onClick={testConnection} variant="outline">
        Test tilkobling {status === 'ok' ? '✅' : status === 'error' ? '❌' : ''}
      </Button>
    </div>
  )
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

  // MFA state
  const [mfaEnabled, setMfaEnabled] = useState(false)
  const [mfaSetupMode, setMfaSetupMode] = useState(false)
  const [mfaQrCode, setMfaQrCode] = useState('')
  const [mfaSecret, setMfaSecret] = useState('')
  const [mfaCode, setMfaCode] = useState('')
  const [mfaBackupCodes, setMfaBackupCodes] = useState<string[]>([])
  const [mfaMessage, setMfaMessage] = useState('')
  const [mfaLoading, setMfaLoading] = useState(false)

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const authHeader = () => {
    const token = typeof window !== 'undefined' ? window.localStorage.getItem('accessToken') : ''
    return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
  }

  const startMfaSetup = async () => {
    setMfaLoading(true); setMfaMessage('')
    try {
      const res = await fetch(`${apiBase}/api/auth/mfa/setup`, { method: 'POST', headers: authHeader() })
      const data = await res.json()
      if (!res.ok) { setMfaMessage(data.detail || 'Feil'); return }
      setMfaQrCode(data.qr_code_base64)
      setMfaSecret(data.secret)
      setMfaSetupMode(true)
    } finally { setMfaLoading(false) }
  }

  const activateMfa = async () => {
    setMfaLoading(true); setMfaMessage('')
    try {
      const res = await fetch(`${apiBase}/api/auth/mfa/activate`, {
        method: 'POST', headers: authHeader(), body: JSON.stringify({ secret: mfaSecret, code: mfaCode }),
      })
      const data = await res.json()
      if (!res.ok) { setMfaMessage(data.detail || 'Ugyldig kode'); return }
      setMfaEnabled(true); setMfaSetupMode(false); setMfaCode('')
      setMfaBackupCodes(data.backup_codes || [])
      setMfaMessage('2FA aktivert!')
    } finally { setMfaLoading(false) }
  }

  const disableMfa = async () => {
    const code = prompt('Skriv inn TOTP-koden din for å deaktivere 2FA:')
    if (!code) return
    setMfaLoading(true); setMfaMessage('')
    try {
      const res = await fetch(`${apiBase}/api/auth/mfa/disable`, {
        method: 'POST', headers: authHeader(), body: JSON.stringify({ code }),
      })
      const data = await res.json()
      if (!res.ok) { setMfaMessage(data.detail || 'Feil'); return }
      setMfaEnabled(false); setMfaBackupCodes([]); setMfaMessage('2FA deaktivert')
    } finally { setMfaLoading(false) }
  }

  const regenerateBackupCodes = async () => {
    setMfaLoading(true); setMfaMessage('')
    try {
      const res = await fetch(`${apiBase}/api/auth/mfa/backup-codes`, { method: 'POST', headers: authHeader() })
      const data = await res.json()
      if (!res.ok) { setMfaMessage(data.detail || 'Feil'); return }
      setMfaBackupCodes(data.backup_codes || [])
      setMfaMessage('Nye reservekoder generert')
    } finally { setMfaLoading(false) }
  }

  useEffect(() => {
    fetchSettings()
    fetchCategories()
  }, [])

  const fetchSettings = async () => {
    try {
      const data = (await api.getSettings() as unknown) as Setting[]
      setSettings(data)

      const grouped = data.reduce((acc: SettingCategory, setting: Setting) => {
        const category = setting.category || 'general'
        if (!acc[category]) acc[category] = []
        acc[category].push(setting)
        return acc
      }, {})

      setSettingsByCategory(grouped)
    } catch (error) {
      console.error('Error fetching settings:', error)
      toast.error('Feil ved lasting av innstillinger')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchCategories = async () => {
    try {
      const data = await api.getSettingsCategories()
      setCategories(data)
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
      const result = await api.updateSettingsBulk(pendingChanges) as any
      toast.success(`Innstillinger lagret: ${result.updated_count ?? 0} oppdatert`)
      setPendingChanges({})
      setHasChanges(false)
      fetchSettings()
    } catch (error) {
      console.error('Error saving settings:', error)
      toast.error('Feil ved lagring av innstillinger')
    } finally {
      setSaving(false)
    }
  }

  const handleResetToDefaults = async () => {
    if (!confirm('Er du sikker på at du vil tilbakestille alle innstillinger? Dette kan ikke angres.')) {
      return
    }

    try {
      setIsResetting(true)
      const result = await api.resetSettingsDefaults() as any
      toast.success(`Tilbakestilt: ${result.created_count ?? 0} standardverdier gjenopprettet`)
      setPendingChanges({})
      setHasChanges(false)
      fetchSettings()
      fetchCategories()
    } catch (error) {
      console.error('Error resetting settings:', error)
      toast.error('Feil ved tilbakestilling')
    } finally {
      setIsResetting(false)
    }
  }

  const handleExportSettings = async () => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiBase}/api/settings/export/all`)

      if (response.ok) {
        const data = await response.json()

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
          <TabsList className="grid w-full grid-cols-2 lg:grid-cols-7">
            {categories.map((category) => (
              <TabsTrigger key={category} value={category}>
                {formatCategoryName(category)}
              </TabsTrigger>
            ))}
            <TabsTrigger value="security">Sikkerhet</TabsTrigger>
            <TabsTrigger value="automatisering">Automatisering</TabsTrigger>
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

          {/* Security / MFA Tab */}
          <TabsContent value="security" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>To-faktor autentisering (2FA)</CardTitle>
                <CardDescription>
                  Beskytt kontoen din med en ekstra verifiseringsfaktor.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {mfaMessage && (
                  <div className="text-sm p-3 rounded bg-blue-50 text-blue-800">{mfaMessage}</div>
                )}

                {!mfaEnabled && !mfaSetupMode && (
                  <div className="space-y-4">
                    <p className="text-sm text-muted-foreground">
                      2FA er ikke aktivert. Bruk en autentiseringsapp som Google Authenticator eller Authy.
                    </p>
                    <Button onClick={startMfaSetup} disabled={mfaLoading}>
                      {mfaLoading ? 'Laster...' : 'Aktiver 2FA'}
                    </Button>
                  </div>
                )}

                {mfaSetupMode && (
                  <div className="space-y-4">
                    <p className="text-sm font-medium">1. Skann QR-koden med autentiseringsappen:</p>
                    {mfaQrCode && (
                      <img
                        src={`data:image/png;base64,${mfaQrCode}`}
                        alt="MFA QR code"
                        className="border rounded p-2 w-48 h-48"
                      />
                    )}
                    <p className="text-sm text-muted-foreground">
                      Manuell nøkkel: <code className="font-mono text-xs bg-gray-100 px-1 py-0.5 rounded">{mfaSecret}</code>
                    </p>
                    <p className="text-sm font-medium">2. Skriv inn koden fra appen for å bekrefte:</p>
                    <div className="flex space-x-3">
                      <Input
                        type="text"
                        inputMode="numeric"
                        maxLength={6}
                        placeholder="000000"
                        value={mfaCode}
                        onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))}
                        className="max-w-xs tracking-widest text-center"
                      />
                      <Button onClick={activateMfa} disabled={mfaLoading || mfaCode.length < 6}>
                        {mfaLoading ? 'Verifiserer...' : 'Bekreft og aktiver'}
                      </Button>
                    </div>
                    <Button variant="outline" onClick={() => { setMfaSetupMode(false); setMfaCode('') }}>
                      Avbryt
                    </Button>
                  </div>
                )}

                {mfaEnabled && (
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2">
                      <Badge className="bg-green-100 text-green-800">Aktivert</Badge>
                      <span className="text-sm">2FA er aktiv på kontoen din.</span>
                    </div>
                    <Button variant="outline" onClick={regenerateBackupCodes} disabled={mfaLoading}>
                      Generer nye reservekoder
                    </Button>
                    <Button variant="destructive" onClick={disableMfa} disabled={mfaLoading}>
                      Deaktiver 2FA
                    </Button>
                  </div>
                )}

                {mfaBackupCodes.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-orange-700">
                      Lagre disse reservekodene på et trygt sted. De vises kun én gang.
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {mfaBackupCodes.map((code, i) => (
                        <code key={i} className="font-mono text-sm bg-gray-100 px-2 py-1 rounded text-center">
                          {code}
                        </code>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="automatisering" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>n8n Automatisering</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <N8nAutomatiseringPanel />
              </CardContent>
            </Card>
          </TabsContent>        </Tabs>
      )}
    </div>
  )
}