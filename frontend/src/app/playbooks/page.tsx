'use client';

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Play, Edit, Trash2, Copy, BookOpen, ArrowRight, MoreHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/components/ui/use-toast';
import { formatRelativeTime, formatNumber } from '@/lib/utils';
import { api } from '@/lib/api';
import type { Playbook, PlaybookStep } from '@/types/api';

interface PlaybookFormData {
  name: string;
  description: string;
  steps: Omit<PlaybookStep, 'id'>[];
}

const STEP_TYPES = [
  {
    type: 'data_collection',
    label: 'Datainnsamling',
    description: 'Samle data fra kilder',
    icon: '📊',
    color: 'bg-blue-100 text-blue-800',
  },
  {
    type: 'validation',
    label: 'Validering',
    description: 'Valider og bekreft data',
    icon: '✅',
    color: 'bg-green-100 text-green-800',
  },
  {
    type: 'enrichment',
    label: 'Berikelse',
    description: 'Berik data med tilleggsinformasjon',
    icon: '🔍',
    color: 'bg-purple-100 text-purple-800',
  },
  {
    type: 'filter',
    label: 'Filtrering',
    description: 'Filter data basert på kriterier',
    icon: '🔽',
    color: 'bg-yellow-100 text-yellow-800',
  },
  {
    type: 'export',
    label: 'Eksport',
    description: 'Eksporter resultater',
    icon: '📤',
    color: 'bg-orange-100 text-orange-800',
  },
  {
    type: 'notification',
    label: 'Notifikasjon',
    description: 'Send varsel eller rapport',
    icon: '🔔',
    color: 'bg-red-100 text-red-800',
  },
  {
    type: 'delay',
    label: 'Vent',
    description: 'Pause før neste steg',
    icon: '⏰',
    color: 'bg-gray-100 text-gray-800',
  },
  {
    type: 'conditional',
    label: 'Betingelse',
    description: 'Utfør handling basert på betingelse',
    icon: '🔀',
    color: 'bg-indigo-100 text-indigo-800',
  },
] as const;

export default function PlaybooksPage() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [selectedPlaybook, setSelectedPlaybook] = useState<Playbook | null>(null);
  const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [playbookToDelete, setPlaybookToDelete] = useState<Playbook | null>(null);
  const [formData, setFormData] = useState<PlaybookFormData>({
    name: '',
    description: '',
    steps: [],
  });

  const { toast } = useToast();

  const {
    data: playbooksResponse,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['playbooks'],
    queryFn: () => api.getPlaybooks(),
  });

  const createPlaybookMutation = useMutation({
    mutationFn: () => api.createPlaybook({
      name: formData.name.trim(),
      description: formData.description.trim() || undefined,
      steps: formData.steps.map((step, index) => ({
        type: step.type,
        configuration: step.configuration,
        order: index + 1,
      })),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      setIsCreateDialogOpen(false);
      resetForm();
      toast({
        title: 'Playbook opprettet',
        description: 'Den nye playbook-en har blitt lagt til systemet.',
      });
    },
    onError: (mutationError: Error) => {
      toast({
        title: 'Kunne ikke opprette playbook',
        description: mutationError.message || 'En feil oppstod. Prøv igjen.',
        variant: 'destructive',
      });
    },
  });

  const deletePlaybookMutation = useMutation({
    mutationFn: (playbookId: string) => api.deletePlaybook(playbookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      setIsDeleteDialogOpen(false);
      setPlaybookToDelete(null);
      toast({
        title: 'Playbook slettet',
        description: 'Playbook-en har blitt fjernet fra systemet.',
      });
    },
    onError: (mutationError: Error) => {
      toast({
        title: 'Kunne ikke slette playbook',
        description: mutationError.message || 'En feil oppstod. Prøv igjen.',
        variant: 'destructive',
      });
    },
  });

  const duplicatePlaybookMutation = useMutation({
    mutationFn: (playbook: Playbook) => api.createPlaybook({
      name: `${playbook.name} (kopi)`,
      description: playbook.description,
      steps: playbook.steps.map((step, index) => ({
        type: step.type,
        configuration: step.configuration,
        order: index + 1,
      })),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playbooks'] });
      toast({
        title: 'Playbook duplisert',
        description: 'Kopien er opprettet i databasen.',
      });
    },
    onError: (mutationError: Error) => {
      toast({
        title: 'Kunne ikke duplisere playbook',
        description: mutationError.message || 'En feil oppstod. Prøv igjen.',
        variant: 'destructive',
      });
    },
  });

  const playbooks = playbooksResponse?.data || [];

  // Filter playbooks
  const filteredPlaybooks = playbooks.filter(playbook => {
    const matchesSearch = playbook.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         playbook.description?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || playbook.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const handleCreatePlaybook = async () => {
    await createPlaybookMutation.mutateAsync();
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      steps: [],
    });
  };

  const addStep = () => {
    const newStep: Omit<PlaybookStep, 'id'> = {
      type: 'data_collection',
      configuration: {},
      order: formData.steps.length + 1,
    };
    setFormData(prev => ({
      ...prev,
      steps: [...prev.steps, newStep],
    }));
  };

  const updateStep = (index: number, field: keyof PlaybookStep, value: any) => {
    setFormData(prev => ({
      ...prev,
      steps: prev.steps.map((step, i) =>
        i === index ? { ...step, [field]: value } : step
      ),
    }));
  };

  const removeStep = (index: number) => {
    setFormData(prev => ({
      ...prev,
      steps: prev.steps.filter((_, i) => i !== index)
        .map((step, i) => ({ ...step, order: i + 1 })),
    }));
  };

  const moveStep = (index: number, direction: 'up' | 'down') => {
    if (
      (direction === 'up' && index === 0) ||
      (direction === 'down' && index === formData.steps.length - 1)
    ) {
      return;
    }

    const newIndex = direction === 'up' ? index - 1 : index + 1;
    const newSteps = [...formData.steps];
    [newSteps[index], newSteps[newIndex]] = [newSteps[newIndex], newSteps[index]];

    // Update order numbers
    newSteps.forEach((step, i) => {
      step.order = i + 1;
    });

    setFormData(prev => ({ ...prev, steps: newSteps }));
  };

  const getStepTypeInfo = (type: string) => {
    return STEP_TYPES.find(t => t.type === type) || STEP_TYPES[0];
  };

  const getStatusVariant = (status: Playbook['status']): 'default' | 'secondary' | 'destructive' | 'success' => {
    switch (status) {
      case 'active':
        return 'success';
      case 'inactive':
        return 'secondary';
      case 'draft':
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  const getStatusLabel = (status: Playbook['status']) => {
    const labels = {
      draft: 'Utkast',
      active: 'Aktiv',
      inactive: 'Inaktiv',
    };
    return labels[status] || status;
  };

  const openViewDialog = (playbook: Playbook) => {
    setSelectedPlaybook(playbook);
    setIsViewDialogOpen(true);
  };

  const openDeleteDialog = (playbook: Playbook) => {
    setPlaybookToDelete(playbook);
    setIsDeleteDialogOpen(true);
  };

  const handleDeletePlaybook = async () => {
    if (!playbookToDelete) return;

    await deletePlaybookMutation.mutateAsync(playbookToDelete.id);
  };

  const handleRunPlaybook = async (playbook: Playbook) => {
    toast({
      title: 'Kjøring ikke tilgjengelig ennå',
      description: `"${playbook.name}" er lagret, men runtime-kjøring av playbooks er ikke implementert ennå.`,
    });
  };

  const handleDuplicatePlaybook = async (playbook: Playbook) => {
    await duplicatePlaybookMutation.mutateAsync(playbook);
  };

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Playbooks</h1>
          <p className="text-muted-foreground">
            Automatiser og standardiser dine OSINT-arbeidsflyter
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => resetForm()}>
              <Plus className="mr-2 h-4 w-4" />
              Ny playbook
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Opprett ny playbook</DialogTitle>
              <DialogDescription>
                Definer en arbeidsflyt med en sekvens av automatiserte steg.
              </DialogDescription>
            </DialogHeader>
            <Tabs defaultValue="basic" className="space-y-4">
              <TabsList>
                <TabsTrigger value="basic">Grunnleggende</TabsTrigger>
                <TabsTrigger value="steps">Steg</TabsTrigger>
              </TabsList>

              <TabsContent value="basic" className="space-y-4">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="playbook-name">Playbook-navn</Label>
                    <Input
                      id="playbook-name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="f.eks. LinkedIn Lead Discovery"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="playbook-description">Beskrivelse</Label>
                    <Textarea
                      id="playbook-description"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="Beskrivelse av arbeidsflytens formål og funksjoner..."
                      rows={3}
                    />
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="steps" className="space-y-4">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label>Arbeidsflyt-steg</Label>
                    <Button onClick={addStep} size="sm">
                      <Plus className="mr-2 h-4 w-4" />
                      Legg til steg
                    </Button>
                  </div>

                  {formData.steps.length === 0 ? (
                    <div className="text-center py-8 border-2 border-dashed border-muted rounded-lg">
                      <BookOpen className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
                      <p className="text-muted-foreground">Ingen steg lagt til ennå</p>
                      <p className="text-sm text-muted-foreground">Klikk &quot;Legg til steg&quot; for å begynne</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {formData.steps.map((step, index) => {
                        const stepInfo = getStepTypeInfo(step.type);
                        return (
                          <Card key={index}>
                            <CardHeader className="pb-3">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-3">
                                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-medium">
                                    {index + 1}
                                  </div>
                                  <div className="flex items-center space-x-2">
                                    <span className="text-lg">{stepInfo.icon}</span>
                                    <Badge className={stepInfo.color}>{stepInfo.label}</Badge>
                                  </div>
                                </div>
                                <div className="flex items-center space-x-1">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => moveStep(index, 'up')}
                                    disabled={index === 0}
                                  >
                                    ↑
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => moveStep(index, 'down')}
                                    disabled={index === formData.steps.length - 1}
                                  >
                                    ↓
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => removeStep(index)}
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </div>
                              </div>
                            </CardHeader>
                            <CardContent className="space-y-3">
                              <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                  <Label>Type</Label>
                                  <Select
                                    value={step.type}
                                    onValueChange={(value) => updateStep(index, 'type', value)}
                                  >
                                    <SelectTrigger>
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {STEP_TYPES.map(type => (
                                        <SelectItem key={type.type} value={type.type}>
                                          <div className="flex items-center space-x-2">
                                            <span>{type.icon}</span>
                                            <div>
                                              <div className="font-medium">{type.label}</div>
                                              <div className="text-sm text-muted-foreground">{type.description}</div>
                                            </div>
                                          </div>
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </div>
                              </div>

                              <div className="space-y-2">
                                <Label>Konfigurasjon (JSON)</Label>
                                <Textarea
                                  value={JSON.stringify(step.configuration, null, 2)}
                                  onChange={(e) => {
                                    try {
                                      const config = JSON.parse(e.target.value);
                                      updateStep(index, 'configuration', config);
                                    } catch {
                                      // Ignore invalid JSON
                                    }
                                  }}
                                  placeholder='{"key": "value"}'
                                  rows={4}
                                  className="font-mono text-sm"
                                />
                              </div>
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Avbryt
              </Button>
              <Button
                onClick={handleCreatePlaybook}
                disabled={!formData.name.trim() || formData.steps.length === 0 || createPlaybookMutation.isPending}
              >
                {createPlaybookMutation.isPending ? 'Oppretter...' : 'Opprett playbook'}
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
            placeholder="Søk playbooks..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Alle statuser" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Alle statuser</SelectItem>
            <SelectItem value="active">Aktiv</SelectItem>
            <SelectItem value="inactive">Inaktiv</SelectItem>
            <SelectItem value="draft">Utkast</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading && (
        <div className="text-sm text-muted-foreground">Laster playbooks...</div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Kunne ikke laste playbooks fra backend. Prøv igjen.
        </div>
      )}

      {/* Playbooks Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredPlaybooks.map((playbook) => (
          <Card key={playbook.id} className="h-full flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="space-y-1 flex-1">
                <CardTitle className="text-lg">{playbook.name}</CardTitle>
                <div className="flex items-center space-x-2">
                  <Badge variant={getStatusVariant(playbook.status)}>
                    {getStatusLabel(playbook.status)}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {playbook.steps.length} steg
                  </span>
                </div>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => handleRunPlaybook(playbook)}>
                    <Play className="mr-2 h-4 w-4" />
                    Kjør playbook
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => openViewDialog(playbook)}>
                    <BookOpen className="mr-2 h-4 w-4" />
                    Vis detaljer
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleDuplicatePlaybook(playbook)}>
                    <Copy className="mr-2 h-4 w-4" />
                    Dupliser
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>
                    <Edit className="mr-2 h-4 w-4" />
                    Rediger
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => openDeleteDialog(playbook)}
                    className="text-red-600"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Slett
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </CardHeader>

            <CardContent className="space-y-4 flex-1">
              {playbook.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {playbook.description}
                </p>
              )}

              <div className="space-y-2">
                <div className="text-sm font-medium">Arbeidsflyt:</div>
                <div className="flex flex-wrap gap-1">
                  {playbook.steps.slice(0, 4).map((step, index) => {
                    const stepInfo = getStepTypeInfo(step.type);
                    return (
                      <div key={step.id} className="flex items-center">
                        <span className="text-sm" title={stepInfo.label}>
                          {stepInfo.icon}
                        </span>
                        {index < Math.min(playbook.steps.length, 4) - 1 && (
                          <ArrowRight className="h-3 w-3 mx-1 text-muted-foreground" />
                        )}
                      </div>
                    );
                  })}
                  {playbook.steps.length > 4 && (
                    <span className="text-xs text-muted-foreground">
                      +{playbook.steps.length - 4} flere
                    </span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Kjøringer: </span>
                  <span className="text-muted-foreground">{formatNumber(playbook.runs_count)}</span>
                </div>
                <div>
                  <span className="font-medium">Suksess: </span>
                  <span className="text-muted-foreground">{playbook.success_rate.toFixed(1)}%</span>
                </div>
              </div>

              {playbook.success_rate > 0 && (
                <Progress value={playbook.success_rate} className="h-2" />
              )}

              <div className="text-sm text-muted-foreground">
                Opprettet: {formatRelativeTime(playbook.created_at)}
              </div>
            </CardContent>

            <CardFooter className="pt-0">
              <Button
                className="w-full"
                onClick={() => handleRunPlaybook(playbook)}
                disabled={playbook.status !== 'active'}
              >
                <Play className="mr-2 h-4 w-4" />
                Kjør playbook
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      {filteredPlaybooks.length === 0 && (
        <div className="text-center py-12">
          <BookOpen className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-medium">Ingen playbooks funnet</h3>
          <p className="mt-2 text-muted-foreground">
            {searchTerm || statusFilter !== 'all'
              ? 'Prøv å justere filtreringsinnstillingene dine.'
              : 'Kom i gang ved å opprette din første playbook.'
            }
          </p>
        </div>
      )}

      {/* View Details Dialog */}
      <Dialog open={isViewDialogOpen} onOpenChange={setIsViewDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>{selectedPlaybook?.name}</DialogTitle>
            <DialogDescription>
              Detaljer om playbook-arbeidsflyt
            </DialogDescription>
          </DialogHeader>
          {selectedPlaybook && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium">Status</Label>
                  <div className="mt-1">
                    <Badge variant={getStatusVariant(selectedPlaybook.status)}>
                      {getStatusLabel(selectedPlaybook.status)}
                    </Badge>
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium">Antall steg</Label>
                  <p className="mt-1 text-lg font-semibold">{selectedPlaybook.steps.length}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Kjøringer</Label>
                  <p className="mt-1 text-lg font-semibold">{formatNumber(selectedPlaybook.runs_count)}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Suksessrate</Label>
                  <p className="mt-1 text-lg font-semibold">{selectedPlaybook.success_rate.toFixed(1)}%</p>
                </div>
              </div>

              {selectedPlaybook.description && (
                <div>
                  <Label className="text-sm font-medium">Beskrivelse</Label>
                  <p className="mt-1 text-sm text-muted-foreground">{selectedPlaybook.description}</p>
                </div>
              )}

              <div>
                <Label className="text-sm font-medium">Arbeidsflyt-steg</Label>
                <div className="mt-2 space-y-3">
                  {selectedPlaybook.steps.map((step, index) => {
                    const stepInfo = getStepTypeInfo(step.type);
                    return (
                      <div key={step.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center space-x-3">
                          <div className="flex items-center justify-center w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs font-medium">
                            {index + 1}
                          </div>
                          <div className="flex items-center space-x-2">
                            <span>{stepInfo.icon}</span>
                            <span className="font-medium">{stepInfo.label}</span>
                          </div>
                        </div>
                        <Badge className={stepInfo.color}>{stepInfo.label}</Badge>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <Label className="text-sm font-medium">Opprettet</Label>
                  <p className="mt-1">{formatRelativeTime(selectedPlaybook.created_at)}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Sist oppdatert</Label>
                  <p className="mt-1">{formatRelativeTime(selectedPlaybook.updated_at)}</p>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Er du sikker?</AlertDialogTitle>
            <AlertDialogDescription>
              Dette vil permanent slette playbook-en &quot;{playbookToDelete?.name}&quot; og alle tilhørende data.
              Denne handlingen kan ikke angres.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Avbryt</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeletePlaybook}
              disabled={deletePlaybookMutation.isPending}
              className="bg-red-600 hover:bg-red-700"
            >
              {deletePlaybookMutation.isPending ? 'Sletter...' : 'Slett'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}