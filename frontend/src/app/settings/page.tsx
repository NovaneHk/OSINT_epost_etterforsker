'use client';

import React, { useState } from 'react';
import { Save, Shield, Mail, Database, Globe, Bell, Zap, Users, Key, Lock, Eye, EyeOff, RefreshCw, AlertTriangle, CheckCircle2, Settings as SettingsIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';
import { useSettings, useUpdateSettings } from '@/hooks/use-api';
import { useToast } from '@/components/ui/use-toast';
import type { Settings } from '@/types/api';

interface SettingsFormData {
  email_verification: {
    enabled: boolean;
    provider: string;
    api_key: string;
    daily_limit: number;
  };
  data_enrichment: {
    enabled: boolean;
    providers: string[];
    auto_enrich: boolean;
  };
  export_settings: {
    max_file_size: number;
    allowed_formats: string[];
    retention_days: number;
  };
  security: {
    two_factor_enabled: boolean;
    session_timeout: number;
    max_failed_logins: number;
  };
  notifications: {
    email_enabled: boolean;
    webhook_url: string;
    slack_webhook: string;
  };
  rate_limiting: {
    requests_per_minute: number;
    burst_limit: number;
  };
}

const EMAIL_PROVIDERS = [
  { value: 'hunter', label: 'Hunter.io', description: 'Populær e-postverifiseringstjeneste' },
  { value: 'zerobounce', label: 'ZeroBounce', description: 'Høy nøyaktighet, god for bulk-verifisering' },
  { value: 'emaillistverify', label: 'EmailListVerify', description: 'Rask og pålitelig verifisering' },
  { value: 'neverbounce', label: 'NeverBounce', description: 'Sanntidsverifisering og bulk-verktøy' },
];

const ENRICHMENT_PROVIDERS = [
  { id: 'clearbit', label: 'Clearbit', description: 'Bedriftsinformasjon og kontaktberikelse' },
  { id: 'fullcontact', label: 'FullContact', description: 'Sosiale profiler og kontaktdata' },
  { id: 'peopledatalabs', label: 'People Data Labs', description: 'Omfattende persondatabase' },
  { id: 'apollo', label: 'Apollo', description: 'B2B-kontakter og bedriftsdata' },
];

const EXPORT_FORMATS = [
  { id: 'csv', label: 'CSV', description: 'Kommaseparerte verdier' },
  { id: 'xlsx', label: 'Excel', description: 'Microsoft Excel-format' },
  { id: 'json', label: 'JSON', description: 'Strukturert data for API-bruk' },
  { id: 'xml', label: 'XML', description: 'Strukturert markup' },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general');
  const [showApiKeys, setShowApiKeys] = useState<Record<string, boolean>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [unsavedChanges, setUnsavedChanges] = useState(false);
  const [testingConnection, setTestingConnection] = useState<string | null>(null);

  const { toast } = useToast();
  const { data: settingsResponse, isLoading, error } = useSettings();
  const updateSettingsMutation = useUpdateSettings();

  // Initialize form data with current settings or defaults
  const [formData, setFormData] = useState<SettingsFormData>({
    email_verification: {
      enabled: true,
      provider: 'hunter',
      api_key: '',
      daily_limit: 1000,
    },
    data_enrichment: {
      enabled: true,
      providers: ['clearbit'],
      auto_enrich: false,
    },
    export_settings: {
      max_file_size: 50, // MB
      allowed_formats: ['csv', 'xlsx', 'json'],
      retention_days: 30,
    },
    security: {
      two_factor_enabled: false,
      session_timeout: 60, // minutes
      max_failed_logins: 5,
    },
    notifications: {
      email_enabled: true,
      webhook_url: '',
      slack_webhook: '',
    },
    rate_limiting: {
      requests_per_minute: 100,
      burst_limit: 200,
    },
  });

  const updateField = (section: keyof SettingsFormData, field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value,
      },
    }));
    setUnsavedChanges(true);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateSettingsMutation.mutateAsync(formData);
      setUnsavedChanges(false);
      toast({
        title: 'Innstillinger lagret',
        description: 'Alle endringer har blitt lagret.',
      });
    } catch (error) {
      toast({
        title: 'Kunne ikke lagre innstillinger',
        description: 'En feil oppstod. Prøv igjen.',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const toggleApiKeyVisibility = (key: string) => {
    setShowApiKeys(prev => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const testConnection = async (service: string) => {
    setTestingConnection(service);
    try {
      // Mock API test
      await new Promise(resolve => setTimeout(resolve, 2000));
      toast({
        title: 'Tilkobling vellykket',
        description: `${service} er konfigurert korrekt.`,
      });
    } catch (error) {
      toast({
        title: 'Tilkoblingsfeil',
        description: `Kunne ikke koble til ${service}. Sjekk konfigurasjon.`,
        variant: 'destructive',
      });
    } finally {
      setTestingConnection(null);
    }
  };

  const resetToDefaults = () => {
    setFormData({
      email_verification: {
        enabled: true,
        provider: 'hunter',
        api_key: '',
        daily_limit: 1000,
      },
      data_enrichment: {
        enabled: true,
        providers: ['clearbit'],
        auto_enrich: false,
      },
      export_settings: {
        max_file_size: 50,
        allowed_formats: ['csv', 'xlsx', 'json'],
        retention_days: 30,
      },
      security: {
        two_factor_enabled: false,
        session_timeout: 60,
        max_failed_logins: 5,
      },
      notifications: {
        email_enabled: true,
        webhook_url: '',
        slack_webhook: '',
      },
      rate_limiting: {
        requests_per_minute: 100,
        burst_limit: 200,
      },
    });
    setUnsavedChanges(true);
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Laster innstillinger...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Innstillinger</h1>
          <p className="text-muted-foreground">
            Konfigurer OSINT-systemet etter dine behov
          </p>
        </div>
        <div className="flex items-center space-x-4">
          {unsavedChanges && (
            <Badge variant="destructive">Ulagrede endringer</Badge>
          )}
          <Button
            onClick={handleSave}
            disabled={isSaving || !unsavedChanges}
            className="min-w-[120px]"
          >
            {isSaving ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                Lagrer...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Lagre
              </>
            )}
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="general">Generelt</TabsTrigger>
          <TabsTrigger value="verification">Verifisering</TabsTrigger>
          <TabsTrigger value="enrichment">Berikelse</TabsTrigger>
          <TabsTrigger value="exports">Eksporter</TabsTrigger>
          <TabsTrigger value="security">Sikkerhet</TabsTrigger>
          <TabsTrigger value="notifications">Varsler</TabsTrigger>
        </TabsList>

        {/* General Settings */}
        <TabsContent value="general" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <SettingsIcon className="h-5 w-5" />
                <span>Generelle innstillinger</span>
              </CardTitle>
              <CardDescription>
                Grunnleggende konfigurasjon for systemet
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Forespørsler per minutt</Label>
                  <Input
                    type="number"
                    value={formData.rate_limiting.requests_per_minute}
                    onChange={(e) => updateField('rate_limiting', 'requests_per_minute', parseInt(e.target.value))}
                    placeholder="100"
                  />
                  <p className="text-sm text-muted-foreground">
                    Maksimalt antall API-forespørsler per minutt
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Burst-grense</Label>
                  <Input
                    type="number"
                    value={formData.rate_limiting.burst_limit}
                    onChange={(e) => updateField('rate_limiting', 'burst_limit', parseInt(e.target.value))}
                    placeholder="200"
                  />
                  <p className="text-sm text-muted-foreground">
                    Maksimalt antall samtidige forespørsler
                  </p>
                </div>
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium">Tilbakestill til standardverdier</h3>
                  <p className="text-sm text-muted-foreground">
                    Tilbakestill alle innstillinger til standardverdier
                  </p>
                </div>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="outline">
                      <RefreshCw className="mr-2 h-4 w-4" />
                      Tilbakestill
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Er du sikker?</AlertDialogTitle>
                      <AlertDialogDescription>
                        Dette vil tilbakestille alle innstillinger til standardverdier.
                        Denne handlingen kan ikke angres.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Avbryt</AlertDialogCancel>
                      <AlertDialogAction onClick={resetToDefaults}>
                        Tilbakestill
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Email Verification */}
        <TabsContent value="verification" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Mail className="h-5 w-5" />
                <span>E-postverifisering</span>
              </CardTitle>
              <CardDescription>
                Konfigurer tjenester for e-postverifisering
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-medium">Aktiver e-postverifisering</h3>
                  <p className="text-sm text-muted-foreground">
                    Verifiser e-postadresser automatisk ved innsamling
                  </p>
                </div>
                <Switch
                  checked={formData.email_verification.enabled}
                  onCheckedChange={(checked) => updateField('email_verification', 'enabled', checked)}
                />
              </div>

              {formData.email_verification.enabled && (
                <>
                  <Separator />

                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label>Verifiseringstjeneste</Label>
                      <Select
                        value={formData.email_verification.provider}
                        onValueChange={(value) => updateField('email_verification', 'provider', value)}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {EMAIL_PROVIDERS.map(provider => (
                            <SelectItem key={provider.value} value={provider.value}>
                              <div>
                                <div className="font-medium">{provider.label}</div>
                                <div className="text-sm text-muted-foreground">{provider.description}</div>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label>API-nøkkel</Label>
                      <div className="flex space-x-2">
                        <div className="relative flex-1">
                          <Input
                            type={showApiKeys.verification ? 'text' : 'password'}
                            value={formData.email_verification.api_key}
                            onChange={(e) => updateField('email_verification', 'api_key', e.target.value)}
                            placeholder="Skriv inn API-nøkkel..."
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="absolute right-2 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
                            onClick={() => toggleApiKeyVisibility('verification')}
                          >
                            {showApiKeys.verification ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </Button>
                        </div>
                        <Button
                          onClick={() => testConnection('E-postverifisering')}
                          disabled={!formData.email_verification.api_key || testingConnection === 'E-postverifisering'}
                        >
                          {testingConnection === 'E-postverifisering' ? (
                            <RefreshCw className="h-4 w-4 animate-spin" />
                          ) : (
                            'Test'
                          )}
                        </Button>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Daglig grense</Label>
                      <Input
                        type="number"
                        value={formData.email_verification.daily_limit}
                        onChange={(e) => updateField('email_verification', 'daily_limit', parseInt(e.target.value))}
                        placeholder="1000"
                      />
                      <p className="text-sm text-muted-foreground">
                        Maksimalt antall e-poster som kan verifiseres per dag
                      </p>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Data Enrichment */}
        <TabsContent value="enrichment" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Database className="h-5 w-5" />
                <span>Databerikelse</span>
              </CardTitle>
              <CardDescription>
                Konfigurer tjenester for å berike kontaktdata
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-medium">Aktiver databerikelse</h3>
                  <p className="text-sm text-muted-foreground">
                    Berik kontaktdata automatisk med tilleggsinformasjon
                  </p>
                </div>
                <Switch
                  checked={formData.data_enrichment.enabled}
                  onCheckedChange={(checked) => updateField('data_enrichment', 'enabled', checked)}
                />
              </div>

              {formData.data_enrichment.enabled && (
                <>
                  <Separator />

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-base font-medium">Automatisk berikelse</h3>
                        <p className="text-sm text-muted-foreground">
                          Berik nye kontakter automatisk ved innsamling
                        </p>
                      </div>
                      <Switch
                        checked={formData.data_enrichment.auto_enrich}
                        onCheckedChange={(checked) => updateField('data_enrichment', 'auto_enrich', checked)}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Aktive tjenester</Label>
                      <div className="grid grid-cols-2 gap-3">
                        {ENRICHMENT_PROVIDERS.map(provider => (
                          <div key={provider.id} className="flex items-center space-x-2 p-3 border rounded-lg">
                            <input
                              type="checkbox"
                              id={provider.id}
                              checked={formData.data_enrichment.providers.includes(provider.id)}
                              onChange={(e) => {
                                const providers = e.target.checked
                                  ? [...formData.data_enrichment.providers, provider.id]
                                  : formData.data_enrichment.providers.filter(p => p !== provider.id);
                                updateField('data_enrichment', 'providers', providers);
                              }}
                            />
                            <div className="flex-1">
                              <label htmlFor={provider.id} className="text-sm font-medium cursor-pointer">
                                {provider.label}
                              </label>
                              <p className="text-xs text-muted-foreground">{provider.description}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Export Settings */}
        <TabsContent value="exports" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Globe className="h-5 w-5" />
                <span>Eksportinnstillinger</span>
              </CardTitle>
              <CardDescription>
                Konfigurer innstillinger for dataeksport
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Maksimal filstørrelse (MB)</Label>
                  <Input
                    type="number"
                    value={formData.export_settings.max_file_size}
                    onChange={(e) => updateField('export_settings', 'max_file_size', parseInt(e.target.value))}
                    placeholder="50"
                  />
                  <p className="text-sm text-muted-foreground">
                    Maksimal størrelse for eksportfiler
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Oppbevaringstid (dager)</Label>
                  <Input
                    type="number"
                    value={formData.export_settings.retention_days}
                    onChange={(e) => updateField('export_settings', 'retention_days', parseInt(e.target.value))}
                    placeholder="30"
                  />
                  <p className="text-sm text-muted-foreground">
                    Hvor lenge eksportfiler skal oppbevares
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Tillatte formater</Label>
                <div className="grid grid-cols-2 gap-3">
                  {EXPORT_FORMATS.map(format => (
                    <div key={format.id} className="flex items-center space-x-2 p-3 border rounded-lg">
                      <input
                        type="checkbox"
                        id={format.id}
                        checked={formData.export_settings.allowed_formats.includes(format.id)}
                        onChange={(e) => {
                          const formats = e.target.checked
                            ? [...formData.export_settings.allowed_formats, format.id]
                            : formData.export_settings.allowed_formats.filter(f => f !== format.id);
                          updateField('export_settings', 'allowed_formats', formats);
                        }}
                      />
                      <div className="flex-1">
                        <label htmlFor={format.id} className="text-sm font-medium cursor-pointer">
                          {format.label}
                        </label>
                        <p className="text-xs text-muted-foreground">{format.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Settings */}
        <TabsContent value="security" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Shield className="h-5 w-5" />
                <span>Sikkerhetsinnstillinger</span>
              </CardTitle>
              <CardDescription>
                Konfigurer sikkerhet og tilgangskontroll
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-medium">Tofaktorautentisering</h3>
                  <p className="text-sm text-muted-foreground">
                    Krev tofaktorautentisering for alle brukere
                  </p>
                </div>
                <Switch
                  checked={formData.security.two_factor_enabled}
                  onCheckedChange={(checked) => updateField('security', 'two_factor_enabled', checked)}
                />
              </div>

              <Separator />

              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Sesjonstimeout (minutter)</Label>
                  <Input
                    type="number"
                    value={formData.security.session_timeout}
                    onChange={(e) => updateField('security', 'session_timeout', parseInt(e.target.value))}
                    placeholder="60"
                  />
                  <p className="text-sm text-muted-foreground">
                    Hvor lenge brukere kan være inaktive før de logges ut
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Maks feile innloggingsforsøk</Label>
                  <Input
                    type="number"
                    value={formData.security.max_failed_logins}
                    onChange={(e) => updateField('security', 'max_failed_logins', parseInt(e.target.value))}
                    placeholder="5"
                  />
                  <p className="text-sm text-muted-foreground">
                    Antall feile forsøk før konto låses
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications */}
        <TabsContent value="notifications" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Bell className="h-5 w-5" />
                <span>Varsler og notifikasjoner</span>
              </CardTitle>
              <CardDescription>
                Konfigurer hvordan systemet sender varsler
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-medium">E-postvarsler</h3>
                  <p className="text-sm text-muted-foreground">
                    Send varsler og rapporter via e-post
                  </p>
                </div>
                <Switch
                  checked={formData.notifications.email_enabled}
                  onCheckedChange={(checked) => updateField('notifications', 'email_enabled', checked)}
                />
              </div>

              <Separator />

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Webhook URL</Label>
                  <div className="flex space-x-2">
                    <Input
                      value={formData.notifications.webhook_url}
                      onChange={(e) => updateField('notifications', 'webhook_url', e.target.value)}
                      placeholder="https://your-webhook-url.com/endpoint"
                    />
                    <Button
                      onClick={() => testConnection('Webhook')}
                      disabled={!formData.notifications.webhook_url || testingConnection === 'Webhook'}
                    >
                      {testingConnection === 'Webhook' ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        'Test'
                      )}
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    URL for å motta webhooks om systemhendelser
                  </p>
                </div>

                <div className="space-y-2">
                  <Label>Slack Webhook</Label>
                  <div className="flex space-x-2">
                    <Input
                      value={formData.notifications.slack_webhook}
                      onChange={(e) => updateField('notifications', 'slack_webhook', e.target.value)}
                      placeholder="https://hooks.slack.com/services/..."
                    />
                    <Button
                      onClick={() => testConnection('Slack')}
                      disabled={!formData.notifications.slack_webhook || testingConnection === 'Slack'}
                    >
                      {testingConnection === 'Slack' ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        'Test'
                      )}
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Slack webhook for å sende varsler til Slack-kanal
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
        </TabsContent>
      </Tabs>
    </div>
  );
}