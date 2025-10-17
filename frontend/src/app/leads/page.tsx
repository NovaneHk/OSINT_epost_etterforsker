'use client';

import { useState, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SmartFilterBar } from '@/components/shared/smart-filter-bar';
import { LeadTable } from '@/components/leads/lead-table';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/components/ui/use-toast';
import { LoadingOverlay, StatsSkeleton, ButtonLoading, DataLoadingWrapper } from '@/components/ui/loading';
import { useLoadingState } from '@/components/providers/loading-provider';
import { PageErrorBoundary } from '@/components/providers/error-boundary';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  Plus,
  Download,
  Upload,
  Filter,
  RefreshCw,
  Play,
  Settings,
  MoreHorizontal,
  FileText,
  Mail,
  Users,
  TrendingUp
} from 'lucide-react';
import { formatNumber } from '@/lib/utils';
import { api } from '@/lib/api';
import type { Lead, FilterState, SortState, LeadsResponse, BatchUpdateLeadsRequest, LeadFilters } from '@/types/api';

export default function LeadsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { isLoading: pageLoading, startLoading: startPageLoading, stopLoading: stopPageLoading } = useLoadingState('leads-page');

  // State
  const [filters, setFilters] = useState<FilterState>({
    search: '',
    tags: [],
    scoreRange: [0, 100],
    sources: [],
  });

  const [sort, setSort] = useState<SortState>({
    field: 'created_at',
    direction: 'desc'
  });

  const [page, setPage] = useState(1);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteLeadIds, setDeleteLeadIds] = useState<string[]>([]);

  // Convert filters to LeadFilters format
  const leadFilters: LeadFilters = {
    search: filters.search || undefined,
    tags: filters.tags.length > 0 ? filters.tags : undefined,
    page,
    limit: 50,
    sort_by: sort.field,
    sort_order: sort.direction,
  };

  // Fetch leads
  const {
    data: leadsResponse,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['leads', leadFilters],
    queryFn: () => api.getLeads(leadFilters),
  });

  // Mutations for batch operations
  const batchUpdateMutation = useMutation({
    mutationFn: (request: BatchUpdateLeadsRequest) => api.batchUpdateLeads(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast({
        title: 'Suksess',
        description: 'Leads oppdatert',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Feil',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  const exportMutation = useMutation({
    mutationFn: (leadIds?: string[]) =>
      api.createExport({
        name: 'Leads Export',
        type: 'csv',
        filters: leadIds ? { lead_ids: leadIds } : undefined
      }),
    onSuccess: () => {
      toast({
        title: 'Eksport startet',
        description: 'Du vil motta en e-post når eksporten er ferdig',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Eksport feilet',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  const runMutation = useMutation({
    mutationFn: () =>
      api.createRun({
        source_ids: [],
        filters: leadFilters as Record<string, unknown>
      }),
    onSuccess: () => {
      toast({
        title: 'Kjøring startet',
        description: 'En ny OSINT-kjøring har blitt startet',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Kunne ikke starte kjøring',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Event handlers
  const handleFiltersChange = (newFilters: FilterState) => {
    setFilters(newFilters);
    setPage(1); // Reset to first page when filters change
  };

  const handleSortChange = (newSort: SortState) => {
    setSort(newSort);
    setPage(1); // Reset to first page when sort changes
  };

  const handleRowSelect = (lead: Lead) => {
    setSelectedLead(lead);
  };

  const handleBulkAction = (action: string, leadIds: string[]) => {
    switch (action) {
      case 'delete':
        setDeleteLeadIds(leadIds);
        setShowDeleteDialog(true);
        break;
      case 'addTags':
        // Would open tag dialog
        break;
      case 'export':
        exportMutation.mutate(leadIds);
        break;
      default:
        break;
    }
  };

  const handleExport = (leadIds?: string[]) => {
    exportMutation.mutate(leadIds);
  };

  const handleDeleteConfirm = () => {
    batchUpdateMutation.mutate({
      lead_ids: deleteLeadIds,
      updates: { verification_status: 'invalid' as const }
    });
    setShowDeleteDialog(false);
    setDeleteLeadIds([]);
  };

  const handleStartRun = () => {
    runMutation.mutate();
  };

  // Computed values
  const leadsData = leadsResponse?.data || [];
  const totalCount = leadsResponse?.meta?.total || 0;
  const totalPages = leadsResponse?.meta?.pages || 1;

  const stats = useMemo(() => {
    const highScoreLeads = leadsData.filter((lead: Lead) => (lead.score || lead.confidence_score || 0) >= 80).length;
    const taggedLeads = leadsData.filter((lead: Lead) => (lead.tags && lead.tags.length > 0)).length;
    const companiesCount = new Set(leadsData.map((lead: Lead) => lead.company).filter(Boolean)).size;

    return {
      total: totalCount,
      highScore: highScoreLeads,
      tagged: taggedLeads,
      companies: companiesCount
    };
  }, [leadsData, totalCount]);

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (filters.search) count++;
    if (filters.tags.length > 0) count++;
    if (filters.scoreRange[0] > 0 || filters.scoreRange[1] < 100) count++;
    if (filters.sources.length > 0) count++;
    if (filters.status) count++;
    return count;
  }, [filters]);

  return (
    <PageErrorBoundary>
      <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Leads</h1>
          <p className="text-muted-foreground">
            Administrer og analyser dine OSINT leads
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <ButtonLoading isLoading={isLoading} loadingText="Oppdaterer...">
              <RefreshCw className="mr-2 h-4 w-4" />
              Oppdater
            </ButtonLoading>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleStartRun}
            disabled={runMutation.isPending}
          >
            <ButtonLoading isLoading={runMutation.isPending} loadingText="Starter...">
              <Play className="mr-2 h-4 w-4" />
              Start kjøring
            </ButtonLoading>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Handlinger</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => handleExport()}>
                <Download className="mr-2 h-4 w-4" />
                Eksporter alle
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Upload className="mr-2 h-4 w-4" />
                Importer leads
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Settings className="mr-2 h-4 w-4" />
                Innstillinger
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button size="sm">
            <Plus className="mr-2 h-4 w-4" />
            Legg til lead
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <DataLoadingWrapper
        data={leadsResponse}
        isLoading={isLoading}
        error={error}
        loadingFallback={<StatsSkeleton />}
        errorFallback={(error) => (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <p className="text-red-700">Failed to load stats: {error.message}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
                className="mt-2"
              >
                Retry
              </Button>
            </CardContent>
          </Card>
        )}
      >
        {() => (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Totalt leads</CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(stats.total)}</div>
                <p className="text-xs text-muted-foreground">
                  {activeFiltersCount > 0 && `${activeFiltersCount} aktive filtre`}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Høy score</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(stats.highScore)}</div>
                <p className="text-xs text-muted-foreground">
                  Score ≥ 80
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Taggede</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(stats.tagged)}</div>
                <p className="text-xs text-muted-foreground">
                  Har tags
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Bedrifter</CardTitle>
                <Mail className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(stats.companies)}</div>
                <p className="text-xs text-muted-foreground">
                  Unike selskaper
                </p>
              </CardContent>
            </Card>
          </div>
        )}
      </DataLoadingWrapper>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <SmartFilterBar
            placeholder="Søk i leads, bedrifter, e-poster..."
            initialFilters={filters}
            onFiltersChange={handleFiltersChange}
            suggestions={[
              'CEO', 'CTO', 'Manager', 'Developer', 'Sales',
              'Oslo', 'Bergen', 'Trondheim', 'Stavanger',
              'tech', 'finance', 'healthcare', 'consulting'
            ]}
          />
        </CardContent>
      </Card>

      {/* Table */}
      <PageErrorBoundary>
        <Card>
          <CardContent className="p-0">
            <LoadingOverlay isLoading={isLoading} loadingText="Loading leads...">
              <LeadTable
                data={leadsData}
                loading={isLoading}
                totalCount={totalCount}
                filters={filters}
                onFiltersChange={handleFiltersChange}
                onSortChange={handleSortChange}
                onRowSelect={handleRowSelect}
                onBulkAction={handleBulkAction}
                onExport={handleExport}
              />
            </LoadingOverlay>
          </CardContent>
        </Card>
      </PageErrorBoundary>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1 || isLoading}
          >
            Forrige
          </Button>

          <div className="flex items-center space-x-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const pageNum = i + 1;
              return (
                <Button
                  key={pageNum}
                  variant={page === pageNum ? "default" : "outline"}
                  size="sm"
                  onClick={() => setPage(pageNum)}
                  disabled={isLoading}
                >
                  {pageNum}
                </Button>
              );
            })}

            {totalPages > 5 && (
              <>
                <span className="text-muted-foreground">...</span>
                <Button
                  variant={page === totalPages ? "default" : "outline"}
                  size="sm"
                  onClick={() => setPage(totalPages)}
                  disabled={isLoading}
                >
                  {totalPages}
                </Button>
              </>
            )}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages || isLoading}
          >
            Neste
          </Button>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Slett leads</AlertDialogTitle>
            <AlertDialogDescription>
              Er du sikker på at du vil slette {deleteLeadIds.length} lead(s)?
              Denne handlingen kan ikke angres.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Avbryt</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Slett
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Lead Detail Sheet */}
      <Sheet open={!!selectedLead} onOpenChange={() => setSelectedLead(null)}>
        <SheetContent className="w-[400px] sm:w-[540px]">
          {selectedLead && (
            <>
              <SheetHeader>
                <SheetTitle>{selectedLead.name || 'Ukjent navn'}</SheetTitle>
                <SheetDescription>
                  Lead detaljer og metadata
                </SheetDescription>
              </SheetHeader>

              <div className="mt-6 space-y-4">
                <div>
                  <label className="text-sm font-medium">E-post</label>
                  <p className="text-sm text-muted-foreground">{selectedLead.email}</p>
                </div>

                {selectedLead.company && (
                  <div>
                    <label className="text-sm font-medium">Bedrift</label>
                    <p className="text-sm text-muted-foreground">{selectedLead.company}</p>
                  </div>
                )}

                {selectedLead.title && (
                  <div>
                    <label className="text-sm font-medium">Tittel</label>
                    <p className="text-sm text-muted-foreground">{selectedLead.title}</p>
                  </div>
                )}

                {selectedLead.location && (
                  <div>
                    <label className="text-sm font-medium">Lokasjon</label>
                    <p className="text-sm text-muted-foreground">{selectedLead.location}</p>
                  </div>
                )}

                {selectedLead.score && (
                  <div>
                    <label className="text-sm font-medium">Score</label>
                    <p className="text-sm text-muted-foreground">{selectedLead.score}/100</p>
                  </div>
                )}

                {selectedLead.tags && selectedLead.tags.length > 0 && (
                  <div>
                    <label className="text-sm font-medium">Tags</label>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {selectedLead.tags.map(tag => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                <Separator />

                <div className="space-y-2">
                  <Button className="w-full" onClick={() => window.open(`mailto:${selectedLead.email}`)}>
                    <Mail className="mr-2 h-4 w-4" />
                    Send e-post
                  </Button>

                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => navigator.clipboard.writeText(selectedLead.email || '')}
                  >
                    Kopier e-post
                  </Button>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
      </div>
    </PageErrorBoundary>
  );
}
