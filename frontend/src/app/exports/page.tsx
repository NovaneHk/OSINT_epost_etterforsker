'use client';

import React, { useState } from 'react';
import { Plus, Search, Download, FileText, Clock, CheckCircle, AlertCircle, Trash2, Eye, Settings, Filter } from 'lucide-react';
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
import { Checkbox } from '@/components/ui/checkbox';
import { useExports, useCreateExport } from '@/hooks/use-api';
import { useToast } from '@/components/ui/use-toast';
import { formatRelativeTime, formatNumber, formatFileSize } from '@/lib/utils';
import type { Export, CreateExportRequest } from '@/types/api';

interface ExportFormData {
  name: string;
  type: 'csv' | 'xlsx' | 'json';
  filters: {
    verification_status?: string[];
    confidence_score_min?: number;
    confidence_score_max?: number;
    industries?: string[];
    domains?: string[];
    date_from?: string;
    date_to?: string;
    source_ids?: string[];
    tags?: string[];
  };
  include_fields: string[];
}

const EXPORT_TYPES = [
  { value: 'csv', label: 'CSV', description: 'Kommaseparerte verdier for Excel/Google Sheets' },
  { value: 'xlsx', label: 'Excel', description: 'Microsoft Excel-format (.xlsx)' },
  { value: 'json', label: 'JSON', description: 'Strukturert data for API-integrasjon' },
] as const;

const AVAILABLE_FIELDS = [
  { id: 'email', label: 'E-post', essential: true },
  { id: 'name', label: 'Navn' },
  { id: 'company', label: 'Bedrift' },
  { id: 'domain', label: 'Domene' },
  { id: 'job_title', label: 'Stillingstittel' },
  { id: 'phone', label: 'Telefon' },
  { id: 'linkedin_url', label: 'LinkedIn URL' },
  { id: 'twitter_url', label: 'Twitter URL' },
  { id: 'website', label: 'Nettside' },
  { id: 'location', label: 'Lokasjon' },
  { id: 'industry', label: 'Bransje' },
  { id: 'company_size', label: 'Bedriftsstørrelse' },
  { id: 'revenue', label: 'Omsetning' },
  { id: 'technologies', label: 'Teknologier' },
  { id: 'confidence_score', label: 'Konfidenspoeng' },
  { id: 'verification_status', label: 'Verifikasjonsstatus' },
  { id: 'engagement_score', label: 'Engasjementsscore' },
  { id: 'last_contacted', label: 'Sist kontaktet' },
  { id: 'source_id', label: 'Kilde-ID' },
  { id: 'source_url', label: 'Kilde URL' },
  { id: 'notes', label: 'Notater' },
  { id: 'tags', label: 'Tags' },
  { id: 'custom_fields', label: 'Egendefinerte felt' },
  { id: 'created_at', label: 'Opprettet dato' },
  { id: 'updated_at', label: 'Oppdatert dato' },
];

const VERIFICATION_STATUSES = [
  { value: 'verified', label: 'Verifisert' },
  { value: 'unverified', label: 'Ikke verifisert' },
  { value: 'invalid', label: 'Ugyldig' },
  { value: 'pending', label: 'Venter' },
];

export default function ExportsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [selectedExport, setSelectedExport] = useState<Export | null>(null);
  const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);
  const [formData, setFormData] = useState<ExportFormData>({
    name: '',
    type: 'csv',
    filters: {},
    include_fields: ['email', 'name', 'company', 'job_title', 'confidence_score', 'verification_status'],
  });

  const { toast } = useToast();
  const { data: exportsResponse, isLoading, error } = useExports();
  const createExportMutation = useCreateExport();

  const exports = exportsResponse?.data || [];

  // Filter exports
  const filteredExports = exports.filter(exportItem => {
    const matchesSearch = exportItem.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || exportItem.status === statusFilter;
    const matchesType = typeFilter === 'all' || exportItem.type === typeFilter;

    return matchesSearch && matchesStatus && matchesType;
  });

  const handleCreateExport = async () => {
    try {
      await createExportMutation.mutateAsync({
        name: formData.name,
        type: formData.type,
        filters: Object.keys(formData.filters).length > 0 ? formData.filters : undefined,
        include_fields: formData.include_fields,
      });
      setIsCreateDialogOpen(false);
      resetForm();
      toast({
        title: 'Export startet',
        description: 'Eksporten behandles og vil være klar om litt.',
      });
    } catch (error) {
      toast({
        title: 'Kunne ikke starte export',
        description: 'En feil oppstod. Prøv igjen.',
        variant: 'destructive',
      });
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      type: 'csv',
      filters: {},
      include_fields: ['email', 'name', 'company', 'job_title', 'confidence_score', 'verification_status'],
    });
  };

  const updateFilter = (key: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      filters: {
        ...prev.filters,
        [key]: value,
      },
    }));
  };

  const toggleField = (fieldId: string) => {
    setFormData(prev => ({
      ...prev,
      include_fields: prev.include_fields.includes(fieldId)
        ? prev.include_fields.filter(f => f !== fieldId)
        : [...prev.include_fields, fieldId],
    }));
  };

  const getStatusIcon = (status: Export['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'processing':
        return <Clock className="h-4 w-4 text-blue-600 animate-spin" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-600" />;
      default:
        return <FileText className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusVariant = (status: Export['status']): 'default' | 'secondary' | 'destructive' | 'success' => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'destructive';
      case 'processing':
        return 'default';
      case 'pending':
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  const getStatusLabel = (status: Export['status']) => {
    const labels = {
      pending: 'Venter',
      processing: 'Behandler',
      completed: 'Fullført',
      failed: 'Feilet',
    };
    return labels[status] || status;
  };

  const getTypeIcon = (type: Export['type']) => {
    switch (type) {
      case 'csv':
        return '📊';
      case 'xlsx':
        return '📈';
      case 'json':
        return '🔗';
      default:
        return '📄';
    }
  };

  const handleDownload = async (exportItem: Export) => {
    if (exportItem.status !== 'completed' || !exportItem.file_path) {
      toast({
        title: 'Kan ikke laste ned',
        description: 'Eksporten er ikke fullført eller filen er ikke tilgjengelig.',
        variant: 'destructive',
      });
      return;
    }

    try {
      // This would typically call an API endpoint to download the file
      const filename = `${exportItem.name}.${exportItem.type}`;
      toast({
        title: 'Nedlasting startet',
        description: `Laster ned ${filename}...`,
      });

      // Mock download - in real app this would trigger actual file download
      console.log(`Downloading ${filename} from ${exportItem.file_path}`);
    } catch (error) {
      toast({
        title: 'Nedlasting feilet',
        description: 'Kunne ikke laste ned filen. Prøv igjen senere.',
        variant: 'destructive',
      });
    }
  };

  const openViewDialog = (exportItem: Export) => {
    setSelectedExport(exportItem);
    setIsViewDialogOpen(true);
  };

  const isExpired = (exportItem: Export) => {
    if (!exportItem.expires_at) return false;
    return new Date(exportItem.expires_at) < new Date();
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Laster eksporter...</p>
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
            <p className="text-red-600">Kunne ikke laste eksporter. Prøv igjen senere.</p>
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
          <h1 className="text-3xl font-bold tracking-tight">Eksporter</h1>
          <p className="text-muted-foreground">
            Eksporter lead-data i ulike formater for videre bruk
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => resetForm()}>
              <Plus className="mr-2 h-4 w-4" />
              Ny eksport
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Opprett ny eksport</DialogTitle>
              <DialogDescription>
                Velg data og format for eksporten av lead-informasjon.
              </DialogDescription>
            </DialogHeader>
            <Tabs defaultValue="basic" className="space-y-4">
              <TabsList>
                <TabsTrigger value="basic">Grunnleggende</TabsTrigger>
                <TabsTrigger value="filters">Filtre</TabsTrigger>
                <TabsTrigger value="fields">Felt</TabsTrigger>
              </TabsList>

              <TabsContent value="basic" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2 space-y-2">
                    <Label htmlFor="export-name">Eksportnavn</Label>
                    <Input
                      id="export-name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="f.eks. Verified Leads Q4 2024"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="export-type">Format</Label>
                    <Select value={formData.type} onValueChange={(value: 'csv' | 'xlsx' | 'json') => setFormData({ ...formData, type: value })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {EXPORT_TYPES.map(type => (
                          <SelectItem key={type.value} value={type.value}>
                            <div className="flex items-center space-x-2">
                              <span className="text-lg">{getTypeIcon(type.value)}</span>
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
              </TabsContent>

              <TabsContent value="filters" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Verifikasjonsstatus</Label>
                    <div className="flex flex-wrap gap-2">
                      {VERIFICATION_STATUSES.map(status => {
                        const isSelected = formData.filters.verification_status?.includes(status.value);
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
                              const current = formData.filters.verification_status || [];
                              const updated = isSelected
                                ? current.filter(s => s !== status.value)
                                : [...current, status.value];
                              updateFilter('verification_status', updated);
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
                          value={formData.filters.confidence_score_min || ''}
                          onChange={(e) => updateFilter('confidence_score_min', e.target.value ? parseInt(e.target.value) : undefined)}
                          placeholder="0"
                        />
                      </div>
                      <div>
                        <Label className="text-sm">Maks</Label>
                        <Input
                          type="number"
                          min="0"
                          max="100"
                          value={formData.filters.confidence_score_max || ''}
                          onChange={(e) => updateFilter('confidence_score_max', e.target.value ? parseInt(e.target.value) : undefined)}
                          placeholder="100"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Datoperiode</Label>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label className="text-sm">Fra</Label>
                        <Input
                          type="date"
                          value={formData.filters.date_from || ''}
                          onChange={(e) => updateFilter('date_from', e.target.value)}
                        />
                      </div>
                      <div>
                        <Label className="text-sm">Til</Label>
                        <Input
                          type="date"
                          value={formData.filters.date_to || ''}
                          onChange={(e) => updateFilter('date_to', e.target.value)}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="domains">Domener (kommaseparert)</Label>
                    <Textarea
                      id="domains"
                      value={formData.filters.domains?.join(', ') || ''}
                      onChange={(e) => {
                        const domains = e.target.value.split(',').map(d => d.trim()).filter(d => d);
                        updateFilter('domains', domains);
                      }}
                      placeholder="example.com, another.no"
                      rows={2}
                    />
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="fields" className="space-y-4">
                <div className="space-y-2">
                  <Label>Velg felt å inkludere i eksporten</Label>
                  <div className="grid grid-cols-2 gap-4 max-h-64 overflow-y-auto">
                    {AVAILABLE_FIELDS.map(field => (
                      <div key={field.id} className="flex items-center space-x-2">
                        <Checkbox
                          id={field.id}
                          checked={formData.include_fields.includes(field.id)}
                          onCheckedChange={() => toggleField(field.id)}
                          disabled={field.essential}
                        />
                        <Label
                          htmlFor={field.id}
                          className={`text-sm ${field.essential ? 'font-medium' : ''}`}
                        >
                          {field.label}
                          {field.essential && ' *'}
                        </Label>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    * Essensielle felt kan ikke fjernes
                  </p>
                </div>
              </TabsContent>
            </Tabs>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Avbryt
              </Button>
              <Button
                onClick={handleCreateExport}
                disabled={createExportMutation.isPending || !formData.name.trim()}
              >
                {createExportMutation.isPending ? 'Starter...' : 'Start eksport'}
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
            placeholder="Søk eksporter..."
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
            <SelectItem value="pending">Venter</SelectItem>
            <SelectItem value="processing">Behandler</SelectItem>
            <SelectItem value="completed">Fullført</SelectItem>
            <SelectItem value="failed">Feilet</SelectItem>
          </SelectContent>
        </Select>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Alle formater" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Alle formater</SelectItem>
            <SelectItem value="csv">CSV</SelectItem>
            <SelectItem value="xlsx">Excel</SelectItem>
            <SelectItem value="json">JSON</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Exports Table */}
      <Card>
        <CardHeader>
          <CardTitle>Eksporthistorikk</CardTitle>
          <CardDescription>
            Oversikt over alle dine dataeksporter
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Navn</TableHead>
                <TableHead>Format</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Fremgang</TableHead>
                <TableHead>Leads</TableHead>
                <TableHead>Størrelse</TableHead>
                <TableHead>Opprettet</TableHead>
                <TableHead>Utløper</TableHead>
                <TableHead className="text-right">Handlinger</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredExports.map((exportItem) => (
                <TableRow key={exportItem.id}>
                  <TableCell>
                    <div className="font-medium">{exportItem.name}</div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <span className="text-lg">{getTypeIcon(exportItem.type)}</span>
                      <span className="uppercase text-sm font-mono">{exportItem.type}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={getStatusVariant(exportItem.status)} className="flex items-center gap-1 w-fit">
                      {getStatusIcon(exportItem.status)}
                      {getStatusLabel(exportItem.status)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {exportItem.status === 'processing' ? (
                      <div className="space-y-1">
                        <Progress value={exportItem.progress} className="h-2" />
                        <div className="text-xs text-muted-foreground">
                          {exportItem.progress}%
                        </div>
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {exportItem.leads_count ? formatNumber(exportItem.leads_count) : '—'}
                  </TableCell>
                  <TableCell>
                    {exportItem.file_size ? formatFileSize(exportItem.file_size) : '—'}
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">{formatRelativeTime(exportItem.created_at)}</div>
                  </TableCell>
                  <TableCell>
                    {exportItem.expires_at ? (
                      <div className={`text-sm ${isExpired(exportItem) ? 'text-red-600' : 'text-muted-foreground'}`}>
                        {formatRelativeTime(exportItem.expires_at)}
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          <Settings className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openViewDialog(exportItem)}>
                          <Eye className="mr-2 h-4 w-4" />
                          Vis detaljer
                        </DropdownMenuItem>
                        {exportItem.status === 'completed' && !isExpired(exportItem) && (
                          <DropdownMenuItem onClick={() => handleDownload(exportItem)}>
                            <Download className="mr-2 h-4 w-4" />
                            Last ned
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuSeparator />
                        <DropdownMenuItem className="text-red-600">
                          <Trash2 className="mr-2 h-4 w-4" />
                          Slett
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {filteredExports.length === 0 && (
        <div className="text-center py-12">
          <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-medium">Ingen eksporter funnet</h3>
          <p className="mt-2 text-muted-foreground">
            {searchTerm || statusFilter !== 'all' || typeFilter !== 'all'
              ? 'Prøv å justere filtreringsinnstillingene dine.'
              : 'Kom i gang ved å opprette din første eksport.'
            }
          </p>
        </div>
      )}

      {/* View Details Dialog */}
      <Dialog open={isViewDialogOpen} onOpenChange={setIsViewDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{selectedExport?.name}</DialogTitle>
            <DialogDescription>
              Detaljer om eksporten
            </DialogDescription>
          </DialogHeader>
          {selectedExport && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium">Status</Label>
                  <div className="mt-1">
                    <Badge variant={getStatusVariant(selectedExport.status)} className="flex items-center gap-1 w-fit">
                      {getStatusIcon(selectedExport.status)}
                      {getStatusLabel(selectedExport.status)}
                    </Badge>
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium">Format</Label>
                  <div className="mt-1 flex items-center space-x-2">
                    <span className="text-lg">{getTypeIcon(selectedExport.type)}</span>
                    <span className="uppercase text-sm font-mono">{selectedExport.type}</span>
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium">Antall leads</Label>
                  <p className="mt-1 text-lg font-semibold">
                    {selectedExport.leads_count ? formatNumber(selectedExport.leads_count) : '—'}
                  </p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Filstørrelse</Label>
                  <p className="mt-1 text-lg font-semibold">
                    {selectedExport.file_size ? formatFileSize(selectedExport.file_size) : '—'}
                  </p>
                </div>
              </div>

              {selectedExport.filters && Object.keys(selectedExport.filters).length > 0 && (
                <div>
                  <Label className="text-sm font-medium">Filtre anvendt</Label>
                  <div className="mt-2 p-3 bg-muted rounded-md">
                    <pre className="text-xs text-muted-foreground whitespace-pre-wrap">
                      {JSON.stringify(selectedExport.filters, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <Label className="text-sm font-medium">Opprettet</Label>
                  <p className="mt-1">{formatRelativeTime(selectedExport.created_at)}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Fullført</Label>
                  <p className="mt-1">
                    {selectedExport.completed_at ? formatRelativeTime(selectedExport.completed_at) : '—'}
                  </p>
                </div>
              </div>

              {selectedExport.expires_at && (
                <div>
                  <Label className="text-sm font-medium">Utløper</Label>
                  <p className={`mt-1 ${isExpired(selectedExport) ? 'text-red-600' : 'text-muted-foreground'}`}>
                    {formatRelativeTime(selectedExport.expires_at)}
                    {isExpired(selectedExport) && ' (Utløpt)'}
                  </p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
