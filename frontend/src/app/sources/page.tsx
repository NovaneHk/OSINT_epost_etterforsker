'use client';

import React, { useState } from 'react';
import { Plus, Search, Settings, Play, Pause, Trash2, TestTube, AlertCircle, CheckCircle, Clock, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Progress } from '@/components/ui/progress';
import { useSources, useCreateSource, useUpdateSource, useDeleteSource, useTestSource } from '@/hooks/use-api';
import { useToast } from '@/components/ui/use-toast';
import { formatRelativeTime, formatNumber } from '@/lib/utils';
import type { Source } from '@/types/api';

interface SourceFormData {
  name: string;
  type: Source['type'];
  url: string;
  description: string;
  configuration: Record<string, unknown>;
  schedule?: string;
}

const SOURCE_TYPES = [
  { value: 'website', label: 'Nettside', description: 'Skraper e-poster fra nettsider' },
  { value: 'linkedin', label: 'LinkedIn', description: 'Henter kontakter fra LinkedIn' },
  { value: 'twitter', label: 'Twitter/X', description: 'Samler kontakter fra Twitter/X' },
  { value: 'directory', label: 'Katalog', description: 'Business-kataloger og lister' },
  { value: 'api', label: 'API', description: 'Tredjeparty API-integrasjon' },
  { value: 'upload', label: 'Opplasting', description: 'Manual filopplasting' },
] as const;

export default function SourcesPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [sourceToDelete, setSourceToDelete] = useState<Source | null>(null);
  const [formData, setFormData] = useState<SourceFormData>({
    name: '',
    type: 'website',
    url: '',
    description: '',
    configuration: {},
    schedule: '',
  });

  const { toast } = useToast();
  const { data: sourcesResponse, isLoading, error } = useSources();
  const createSourceMutation = useCreateSource();
  const updateSourceMutation = useUpdateSource();
  const deleteSourceMutation = useDeleteSource();
  const testSourceMutation = useTestSource();

  const sources = sourcesResponse?.data || [];

  // Filter sources
  const filteredSources = sources.filter(source => {
    const matchesSearch = source.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         source.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         source.url?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = typeFilter === 'all' || source.type === typeFilter;
    const matchesStatus = statusFilter === 'all' || source.status === statusFilter;

    return matchesSearch && matchesType && matchesStatus;
  });

  const handleCreateSource = async () => {
    try {
      await createSourceMutation.mutateAsync(formData);
      setIsCreateDialogOpen(false);
      resetForm();
      toast({
        title: 'Kilde opprettet',
        description: 'Den nye kilden har blitt lagt til systemet.',
      });
    } catch (error) {
      toast({
        title: 'Kunne ikke opprette kilde',
        description: 'En feil oppstod. Prøv igjen.',
        variant: 'destructive',
      });
    }
  };

  const handleUpdateSource = async () => {
    if (!selectedSource) return;

    try {
      await updateSourceMutation.mutateAsync({
        id: selectedSource.id,
        data: formData,
      });
      setIsEditDialogOpen(false);
      setSelectedSource(null);
      resetForm();
      toast({
        title: 'Kilde oppdatert',
        description: 'Endringene har blitt lagret.',
      });
    } catch (error) {
      toast({
        title: 'Kunne ikke oppdatere kilde',
        description: 'En feil oppstod. Prøv igjen.',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteSource = async () => {
    if (!sourceToDelete) return;

    try {
      await deleteSourceMutation.mutateAsync(sourceToDelete.id);
      setIsDeleteDialogOpen(false);
      setSourceToDelete(null);
      toast({
        title: 'Kilde slettet',
        description: 'Kilden har blitt fjernet fra systemet.',
      });
    } catch (error) {
      toast({
        title: 'Kunne ikke slette kilde',
        description: 'En feil oppstod. Prøv igjen.',
        variant: 'destructive',
      });
    }
  };

  const handleTestSource = async (source: Source) => {
    try {
      await testSourceMutation.mutateAsync(source.id);
      toast({
        title: 'Kildetest startet',
        description: 'Tester kildens konfigurasjon...',
      });
    } catch (error) {
      toast({
        title: 'Kildetest feilet',
        description: 'Kunne ikke teste kilden. Sjekk konfigurasjonen.',
        variant: 'destructive',
      });
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      type: 'website',
      url: '',
      description: '',
      configuration: {},
      schedule: '',
    });
  };

  const openEditDialog = (source: Source) => {
    setSelectedSource(source);
    setFormData({
      name: source.name,
      type: source.type,
      url: source.url || '',
      description: source.description || '',
      configuration: source.configuration,
      schedule: source.schedule || '',
    });
    setIsEditDialogOpen(true);
  };

  const openDeleteDialog = (source: Source) => {
    setSourceToDelete(source);
    setIsDeleteDialogOpen(true);
  };

  const getStatusIcon = (status: Source['status']) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'inactive':
        return <Pause className="h-4 w-4 text-gray-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'testing':
        return <Clock className="h-4 w-4 text-yellow-600" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusVariant = (status: Source['status']): 'default' | 'secondary' | 'destructive' => {
    switch (status) {
      case 'active':
        return 'default';
      case 'inactive':
        return 'secondary';
      case 'error':
        return 'destructive';
      default:
        return 'secondary';
    }
  };

  const getTypeLabel = (type: Source['type']) => {
    return SOURCE_TYPES.find(t => t.value === type)?.label || type;
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Laster kilder...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 text-red-600 mx-auto mb-4" />
            <p className="text-red-600">Kunne ikke laste kilder. Prøv igjen senere.</p>
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
          <h1 className="text-3xl font-bold tracking-tight">Kilder</h1>
          <p className="text-muted-foreground">
            Administrer datakilder for OSINT-innsamling
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => resetForm()}>
              <Plus className="mr-2 h-4 w-4" />
              Ny kilde
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Opprett ny kilde</DialogTitle>
              <DialogDescription>
                Legg til en ny datakilde for å samle kontaktinformasjon.
              </DialogDescription>
            </DialogHeader>
            <Tabs defaultValue="basic" className="space-y-4">
              <TabsList>
                <TabsTrigger value="basic">Grunnleggende</TabsTrigger>
                <TabsTrigger value="configuration">Konfigurasjon</TabsTrigger>
                <TabsTrigger value="schedule">Planlegging</TabsTrigger>
              </TabsList>

              <TabsContent value="basic" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Navn</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="f.eks. LinkedIn Norge"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="type">Type</Label>
                    <Select value={formData.type} onValueChange={(value: Source['type']) => setFormData({ ...formData, type: value })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {SOURCE_TYPES.map(type => (
                          <SelectItem key={type.value} value={type.value}>
                            <div>
                              <div className="font-medium">{type.label}</div>
                              <div className="text-sm text-muted-foreground">{type.description}</div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="url">URL</Label>
                  <Input
                    id="url"
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    placeholder="https://example.com"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">Beskrivelse</Label>
                  <Textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Beskrivelse av datakilden..."
                    rows={3}
                  />
                </div>
              </TabsContent>

              <TabsContent value="configuration" className="space-y-4">
                <div className="space-y-2">
                  <Label>Konfigurasjon</Label>
                  <Textarea
                    value={JSON.stringify(formData.configuration, null, 2)}
                    onChange={(e) => {
                      try {
                        const config = JSON.parse(e.target.value);
                        setFormData({ ...formData, configuration: config });
                      } catch {
                        // Ignore invalid JSON
                      }
                    }}
                    placeholder='{"key": "value"}'
                    rows={10}
                    className="font-mono text-sm"
                  />
                  <p className="text-sm text-muted-foreground">
                    JSON-konfigurasjon for kilden. Vil variere basert på type.
                  </p>
                </div>
              </TabsContent>

              <TabsContent value="schedule" className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="schedule">Cron-planlegging</Label>
                  <Input
                    id="schedule"
                    value={formData.schedule}
                    onChange={(e) => setFormData({ ...formData, schedule: e.target.value })}
                    placeholder="0 */6 * * * (hver 6. time)"
                  />
                  <p className="text-sm text-muted-foreground">
                    Cron-uttrykk for automatisk kjøring. La stå tom for manuell kjøring.
                  </p>
                </div>
              </TabsContent>
            </Tabs>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Avbryt
              </Button>
              <Button
                onClick={handleCreateSource}
                disabled={createSourceMutation.isPending || !formData.name.trim()}
              >
                {createSourceMutation.isPending ? 'Oppretter...' : 'Opprett kilde'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="flex items-center space-x-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
          <Input
            placeholder="Søk kilder..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Alle typer" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Alle typer</SelectItem>
            {SOURCE_TYPES.map(type => (
              <SelectItem key={type.value} value={type.value}>
                {type.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Alle statuser" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Alle statuser</SelectItem>
            <SelectItem value="active">Aktiv</SelectItem>
            <SelectItem value="inactive">Inaktiv</SelectItem>
            <SelectItem value="error">Feil</SelectItem>
            <SelectItem value="testing">Tester</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Sources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredSources.map((source) => (
          <Card key={source.id} className="h-full">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="space-y-1 flex-1">
                <CardTitle className="text-lg">{source.name}</CardTitle>
                <div className="flex items-center space-x-2">
                  <Badge variant={getStatusVariant(source.status)} className="flex items-center gap-1">
                    {getStatusIcon(source.status)}
                    {source.status}
                  </Badge>
                  <Badge variant="outline">{getTypeLabel(source.type)}</Badge>
                </div>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <Settings className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => openEditDialog(source)}>
                    <Settings className="mr-2 h-4 w-4" />
                    Rediger
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleTestSource(source)}>
                    <TestTube className="mr-2 h-4 w-4" />
                    Test kilde
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => openDeleteDialog(source)}
                    className="text-red-600"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Slett
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </CardHeader>

            <CardContent className="space-y-4">
              {source.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {source.description}
                </p>
              )}

              {source.url && (
                <div className="text-sm">
                  <span className="font-medium">URL: </span>
                  <span className="text-muted-foreground truncate">{source.url}</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Leads: </span>
                  <span className="text-muted-foreground">{formatNumber(source.leads_count)}</span>
                </div>
                <div>
                  <span className="font-medium">Suksess: </span>
                  <span className="text-muted-foreground">{source.success_rate.toFixed(1)}%</span>
                </div>
              </div>

              {source.success_rate > 0 && (
                <Progress value={source.success_rate} className="h-2" />
              )}

              {source.last_run && (
                <div className="text-sm text-muted-foreground">
                  Sist kjørt: {formatRelativeTime(source.last_run)}
                </div>
              )}

              {source.error_message && (
                <div className="text-sm text-red-600 bg-red-50 p-2 rounded border">
                  {source.error_message}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredSources.length === 0 && (
        <div className="text-center py-12">
          <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-medium">Ingen kilder funnet</h3>
          <p className="mt-2 text-muted-foreground">
            {searchTerm || typeFilter !== 'all' || statusFilter !== 'all'
              ? 'Prøv å justere filtreringsinnstillingene dine.'
              : 'Kom i gang ved å opprette din første datakilde.'
            }
          </p>
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Rediger kilde</DialogTitle>
            <DialogDescription>
              Oppdater innstillingene for denne datakilden.
            </DialogDescription>
          </DialogHeader>
          <Tabs defaultValue="basic" className="space-y-4">
            <TabsList>
              <TabsTrigger value="basic">Grunnleggende</TabsTrigger>
              <TabsTrigger value="configuration">Konfigurasjon</TabsTrigger>
              <TabsTrigger value="schedule">Planlegging</TabsTrigger>
            </TabsList>

            <TabsContent value="basic" className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-name">Navn</Label>
                  <Input
                    id="edit-name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="f.eks. LinkedIn Norge"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-type">Type</Label>
                  <Select value={formData.type} onValueChange={(value: Source['type']) => setFormData({ ...formData, type: value })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SOURCE_TYPES.map(type => (
                        <SelectItem key={type.value} value={type.value}>
                          <div>
                            <div className="font-medium">{type.label}</div>
                            <div className="text-sm text-muted-foreground">{type.description}</div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-url">URL</Label>
                <Input
                  id="edit-url"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  placeholder="https://example.com"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-description">Beskrivelse</Label>
                <Textarea
                  id="edit-description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Beskrivelse av datakilden..."
                  rows={3}
                />
              </div>
            </TabsContent>

            <TabsContent value="configuration" className="space-y-4">
              <div className="space-y-2">
                <Label>Konfigurasjon</Label>
                <Textarea
                  value={JSON.stringify(formData.configuration, null, 2)}
                  onChange={(e) => {
                    try {
                      const config = JSON.parse(e.target.value);
                      setFormData({ ...formData, configuration: config });
                    } catch {
                      // Ignore invalid JSON
                    }
                  }}
                  placeholder='{"key": "value"}'
                  rows={10}
                  className="font-mono text-sm"
                />
                <p className="text-sm text-muted-foreground">
                  JSON-konfigurasjon for kilden. Vil variere basert på type.
                </p>
              </div>
            </TabsContent>

            <TabsContent value="schedule" className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="edit-schedule">Cron-planlegging</Label>
                <Input
                  id="edit-schedule"
                  value={formData.schedule}
                  onChange={(e) => setFormData({ ...formData, schedule: e.target.value })}
                  placeholder="0 */6 * * * (hver 6. time)"
                />
                <p className="text-sm text-muted-foreground">
                  Cron-uttrykk for automatisk kjøring. La stå tom for manuell kjøring.
                </p>
              </div>
            </TabsContent>
          </Tabs>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              Avbryt
            </Button>
            <Button
              onClick={handleUpdateSource}
              disabled={updateSourceMutation.isPending || !formData.name.trim()}
            >
              {updateSourceMutation.isPending ? 'Lagrer...' : 'Lagre endringer'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Er du sikker?</AlertDialogTitle>
            <AlertDialogDescription>
              Dette vil permanent slette kilden "{sourceToDelete?.name}" og alle tilhørende data.
              Denne handlingen kan ikke angres.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Avbryt</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteSource}
              className="bg-red-600 hover:bg-red-700"
              disabled={deleteSourceMutation.isPending}
            >
              {deleteSourceMutation.isPending ? 'Sletter...' : 'Slett'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}