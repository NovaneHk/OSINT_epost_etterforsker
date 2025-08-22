'use client';

import React, { useState } from 'react';
import { Plus, Search, Users, Target, Play, Pause, Settings, Trash2, Filter, Download, Eye, BarChart3 } from 'lucide-react';
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
import { Switch } from '@/components/ui/switch';
import { useCampaigns, useCreateCampaign } from '@/hooks/use-api';
import { useToast } from '@/components/ui/use-toast';
import { formatRelativeTime, formatNumber } from '@/lib/utils';
import type { Campaign } from '@/types/api';

interface CampaignFormData {
  name: string;
  description: string;
  filter_criteria: {
    verification_status?: string[];
    confidence_score_min?: number;
    confidence_score_max?: number;
    industries?: string[];
    domains?: string[];
    company_size?: string[];
    location?: string[];
    tags?: string[];
  };
  target_count?: number;
}

const VERIFICATION_STATUSES = [
  { value: 'verified', label: 'Verifisert', color: 'bg-green-100 text-green-800' },
  { value: 'unverified', label: 'Ikke verifisert', color: 'bg-yellow-100 text-yellow-800' },
  { value: 'invalid', label: 'Ugyldig', color: 'bg-red-100 text-red-800' },
  { value: 'pending', label: 'Venter', color: 'bg-blue-100 text-blue-800' },
];

const INDUSTRIES = [
  'Teknologi', 'Finans', 'Helse', 'Utdanning', 'Retail', 'Bygg og anlegg',
  'Media', 'Transport', 'Energi', 'Forskning', 'Consulting', 'Annet'
];

const COMPANY_SIZES = [
  '1-10 ansatte', '11-50 ansatte', '51-200 ansatte', '201-500 ansatte',
  '501-1000 ansatte', '1000+ ansatte'
];

const LOCATIONS = [
  'Oslo', 'Bergen', 'Trondheim', 'Stavanger', 'Kristiansand', 'Tromsø',
  'Drammen', 'Fredrikstad', 'Skien', 'Sandnes', 'Annet'
];

export default function CampaignsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);
  const [formData, setFormData] = useState<CampaignFormData>({
    name: '',
    description: '',
    filter_criteria: {},
    target_count: undefined,
  });

  const { toast } = useToast();
  const { data: campaignsResponse, isLoading, error } = useCampaigns();
  const createCampaignMutation = useCreateCampaign();

  const campaigns = campaignsResponse?.data || [];

  // Filter campaigns
  const filteredCampaigns = campaigns.filter(campaign => {
    const matchesSearch = campaign.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         campaign.description?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || campaign.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const handleCreateCampaign = async () => {
    try {
      await createCampaignMutation.mutateAsync({
        name: formData.name,
        description: formData.description,
        filter_criteria: formData.filter_criteria,
        target_count: formData.target_count,
      });
      setIsCreateDialogOpen(false);
      resetForm();
      toast({
        title: 'Segment opprettet',
        description: 'Det nye segmentet har blitt lagt til systemet.',
      });
    } catch (error) {
      toast({
        title: 'Kunne ikke opprette segment',
        description: 'En feil oppstod. Prøv igjen.',
        variant: 'destructive',
      });
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      filter_criteria: {},
      target_count: undefined,
    });
  };

  const updateFilterCriteria = (key: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      filter_criteria: {
        ...prev.filter_criteria,
        [key]: value,
      },
    }));
  };

  const getStatusVariant = (status: Campaign['status']): 'default' | 'secondary' | 'destructive' | 'success' => {
    switch (status) {
      case 'active':
        return 'success';
      case 'completed':
        return 'default';
      case 'paused':
        return 'secondary';
      case 'draft':
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  const getStatusLabel = (status: Campaign['status']) => {
    const labels = {
      draft: 'Utkast',
      active: 'Aktiv',
      paused: 'Pauset',
      completed: 'Fullført',
    };
    return labels[status] || status;
  };

  const calculateProgress = (campaign: Campaign) => {
    if (!campaign.target_count) return 0;
    return Math.min((campaign.leads_count / campaign.target_count) * 100, 100);
  };

  const openViewDialog = (campaign: Campaign) => {
    setSelectedCampaign(campaign);
    setIsViewDialogOpen(true);
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Laster segmenter...</p>
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
            <Target className="h-8 w-8 text-red-600 mx-auto mb-4" />
            <p className="text-red-600">Kunne ikke laste segmenter. Prøv igjen senere.</p>
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
          <h1 className="text-3xl font-bold tracking-tight">Segmenter</h1>
          <p className="text-muted-foreground">
            Organiser og målrett lead-segmenter for effektiv outreach
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => resetForm()}>
              <Plus className="mr-2 h-4 w-4" />
              Nytt segment
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Opprett nytt segment</DialogTitle>
              <DialogDescription>
                Definer kriterier for å gruppere leads i et målrettet segment.
              </DialogDescription>
            </DialogHeader>
            <Tabs defaultValue="basic" className="space-y-4">
              <TabsList>
                <TabsTrigger value="basic">Grunnleggende</TabsTrigger>
                <TabsTrigger value="criteria">Kriterier</TabsTrigger>
                <TabsTrigger value="advanced">Avansert</TabsTrigger>
              </TabsList>

              <TabsContent value="basic" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2 space-y-2">
                    <Label htmlFor="name">Segmentnavn</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="f.eks. Tech Startups Oslo"
                    />
                  </div>
                  <div className="col-span-2 space-y-2">
                    <Label htmlFor="description">Beskrivelse</Label>
                    <Textarea
                      id="description"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="Beskrivelse av segmentet..."
                      rows={3}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="target_count">Målgruppe-størrelse</Label>
                    <Input
                      id="target_count"
                      type="number"
                      value={formData.target_count || ''}
                      onChange={(e) => setFormData({ ...formData, target_count: e.target.value ? parseInt(e.target.value) : undefined })}
                      placeholder="f.eks. 500"
                    />
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="criteria" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Verifikasjonsstatus</Label>
                    <div className="flex flex-wrap gap-2">
                      {VERIFICATION_STATUSES.map(status => {
                        const isSelected = formData.filter_criteria.verification_status?.includes(status.value);
                        return (
                          <button
                            key={status.value}
                            type="button"
                            className={`px-3 py-1 rounded-full text-sm transition-colors ${
                              isSelected
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                            }`}
                            onClick={() => {
                              const current = formData.filter_criteria.verification_status || [];
                              const updated = isSelected
                                ? current.filter(s => s !== status.value)
                                : [...current, status.value];
                              updateFilterCriteria('verification_status', updated);
                            }}
                          >
                            {status.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Konfidenspoeng</Label>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label className="text-sm">Min</Label>
                        <Input
                          type="number"
                          min="0"
                          max="100"
                          value={formData.filter_criteria.confidence_score_min || ''}
                          onChange={(e) => updateFilterCriteria('confidence_score_min', e.target.value ? parseInt(e.target.value) : undefined)}
                          placeholder="0"
                        />
                      </div>
                      <div>
                        <Label className="text-sm">Maks</Label>
                        <Input
                          type="number"
                          min="0"
                          max="100"
                          value={formData.filter_criteria.confidence_score_max || ''}
                          onChange={(e) => updateFilterCriteria('confidence_score_max', e.target.value ? parseInt(e.target.value) : undefined)}
                          placeholder="100"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Bransjer</Label>
                    <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
                      {INDUSTRIES.map(industry => {
                        const isSelected = formData.filter_criteria.industries?.includes(industry);
                        return (
                          <button
                            key={industry}
                            type="button"
                            className={`px-2 py-1 rounded text-sm transition-colors ${
                              isSelected
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                            }`}
                            onClick={() => {
                              const current = formData.filter_criteria.industries || [];
                              const updated = isSelected
                                ? current.filter(i => i !== industry)
                                : [...current, industry];
                              updateFilterCriteria('industries', updated);
                            }}
                          >
                            {industry}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Bedriftsstørrelser</Label>
                    <div className="flex flex-wrap gap-2">
                      {COMPANY_SIZES.map(size => {
                        const isSelected = formData.filter_criteria.company_size?.includes(size);
                        return (
                          <button
                            key={size}
                            type="button"
                            className={`px-2 py-1 rounded text-sm transition-colors ${
                              isSelected
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                            }`}
                            onClick={() => {
                              const current = formData.filter_criteria.company_size || [];
                              const updated = isSelected
                                ? current.filter(s => s !== size)
                                : [...current, size];
                              updateFilterCriteria('company_size', updated);
                            }}
                          >
                            {size}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="advanced" className="space-y-4">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Lokasjoner</Label>
                    <div className="flex flex-wrap gap-2">
                      {LOCATIONS.map(location => {
                        const isSelected = formData.filter_criteria.location?.includes(location);
                        return (
                          <button
                            key={location}
                            type="button"
                            className={`px-2 py-1 rounded text-sm transition-colors ${
                              isSelected
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                            }`}
                            onClick={() => {
                              const current = formData.filter_criteria.location || [];
                              const updated = isSelected
                                ? current.filter(l => l !== location)
                                : [...current, location];
                              updateFilterCriteria('location', updated);
                            }}
                          >
                            {location}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="domains">Domener (kommaseparert)</Label>
                    <Textarea
                      id="domains"
                      value={formData.filter_criteria.domains?.join(', ') || ''}
                      onChange={(e) => {
                        const domains = e.target.value.split(',').map(d => d.trim()).filter(d => d);
                        updateFilterCriteria('domains', domains);
                      }}
                      placeholder="example.com, another.no"
                      rows={2}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="tags">Tags (kommaseparert)</Label>
                    <Textarea
                      id="tags"
                      value={formData.filter_criteria.tags?.join(', ') || ''}
                      onChange={(e) => {
                        const tags = e.target.value.split(',').map(t => t.trim()).filter(t => t);
                        updateFilterCriteria('tags', tags);
                      }}
                      placeholder="vip, hot-lead, follow-up"
                      rows={2}
                    />
                  </div>
                </div>
              </TabsContent>
            </Tabs>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Avbryt
              </Button>
              <Button
                onClick={handleCreateCampaign}
                disabled={createCampaignMutation.isPending || !formData.name.trim()}
              >
                {createCampaignMutation.isPending ? 'Oppretter...' : 'Opprett segment'}
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
            placeholder="Søk segmenter..."
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
            <SelectItem value="draft">Utkast</SelectItem>
            <SelectItem value="active">Aktiv</SelectItem>
            <SelectItem value="paused">Pauset</SelectItem>
            <SelectItem value="completed">Fullført</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Campaigns Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredCampaigns.map((campaign) => (
          <Card key={campaign.id} className="h-full flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="space-y-1 flex-1">
                <CardTitle className="text-lg">{campaign.name}</CardTitle>
                <div className="flex items-center space-x-2">
                  <Badge variant={getStatusVariant(campaign.status)}>
                    {getStatusLabel(campaign.status)}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {formatNumber(campaign.leads_count)} leads
                  </span>
                </div>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <Settings className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => openViewDialog(campaign)}>
                    <Eye className="mr-2 h-4 w-4" />
                    Vis detaljer
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Analyser
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <Download className="mr-2 h-4 w-4" />
                    Eksporter
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>
                    <Settings className="mr-2 h-4 w-4" />
                    Rediger
                  </DropdownMenuItem>
                  <DropdownMenuItem className="text-red-600">
                    <Trash2 className="mr-2 h-4 w-4" />
                    Slett
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </CardHeader>

            <CardContent className="space-y-4 flex-1">
              {campaign.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {campaign.description}
                </p>
              )}

              {campaign.target_count && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Fremgang</span>
                    <span>{formatNumber(campaign.leads_count)} / {formatNumber(campaign.target_count)}</span>
                  </div>
                  <Progress value={calculateProgress(campaign)} className="h-2" />
                  <div className="text-xs text-muted-foreground">
                    {calculateProgress(campaign).toFixed(1)}% av målet nådd
                  </div>
                </div>
              )}

              <div className="text-sm text-muted-foreground">
                Opprettet: {formatRelativeTime(campaign.created_at)}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredCampaigns.length === 0 && (
        <div className="text-center py-12">
          <Target className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-medium">Ingen segmenter funnet</h3>
          <p className="mt-2 text-muted-foreground">
            {searchTerm || statusFilter !== 'all'
              ? 'Prøv å justere filtreringsinnstillingene dine.'
              : 'Kom i gang ved å opprette ditt første segment.'
            }
          </p>
        </div>
      )}

      {/* View Details Dialog */}
      <Dialog open={isViewDialogOpen} onOpenChange={setIsViewDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{selectedCampaign?.name}</DialogTitle>
            <DialogDescription>
              Detaljer og kriterier for segmentet
            </DialogDescription>
          </DialogHeader>
          {selectedCampaign && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium">Status</Label>
                  <div className="mt-1">
                    <Badge variant={getStatusVariant(selectedCampaign.status)}>
                      {getStatusLabel(selectedCampaign.status)}
                    </Badge>
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium">Antall leads</Label>
                  <p className="mt-1 text-lg font-semibold">{formatNumber(selectedCampaign.leads_count)}</p>
                </div>
              </div>

              {selectedCampaign.description && (
                <div>
                  <Label className="text-sm font-medium">Beskrivelse</Label>
                  <p className="mt-1 text-sm text-muted-foreground">{selectedCampaign.description}</p>
                </div>
              )}

              <div>
                <Label className="text-sm font-medium">Filterkriterier</Label>
                <div className="mt-2 p-3 bg-muted rounded-md">
                  <pre className="text-xs text-muted-foreground whitespace-pre-wrap">
                    {JSON.stringify(selectedCampaign.filter_criteria, null, 2)}
                  </pre>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <Label className="text-sm font-medium">Opprettet</Label>
                  <p className="mt-1">{formatRelativeTime(selectedCampaign.created_at)}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Sist oppdatert</Label>
                  <p className="mt-1">{formatRelativeTime(selectedCampaign.updated_at)}</p>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}