import { useQuery, useMutation, useQueryClient, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query';
import { api, getErrorMessage, isAPIError } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';
import type {
  KPIResponse,
  ActivityResponse,
  LeadsResponse,
  SourcesResponse,
  RunsResponse,
  ExportsResponse,
  CampaignsResponse,
  PlaybooksResponse,
  HealthCheckResponse,
  SettingsResponse,
  Lead,
  Source,
  Run,
  Campaign,
  Playbook,
  CreateRunRequest,
  CreateExportRequest,
  BatchUpdateLeadsRequest,
  CreateCampaignRequest,
  CreatePlaybookRequest,
  UpdateSettingsRequest,
  LeadFilters,
} from '@/types/api';

// Query Keys
export const queryKeys = {
  // Dashboard
  kpis: ['kpis'] as const,
  activity: ['activity'] as const,
  health: ['health'] as const,

  // Leads
  leads: ['leads'] as const,
  leadsWithFilters: (filters?: Record<string, unknown>) => ['leads', filters] as const,

  // Sources
  sources: ['sources'] as const,

  // Runs
  runs: ['runs'] as const,
  runLogs: (id: string) => ['runs', id, 'logs'] as const,

  // Campaigns
  campaigns: ['campaigns'] as const,

  // Exports
  exports: ['exports'] as const,

  // Playbooks
  playbooks: ['playbooks'] as const,

  // Settings
  settings: ['settings'] as const,
} as const;

// Dashboard Hooks
export function useKPIs(options?: UseQueryOptions<KPIResponse>) {
  return useQuery({
    queryKey: queryKeys.kpis,
    queryFn: api.getKPIs,
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

export function useActivity(options?: UseQueryOptions<ActivityResponse>) {
  return useQuery({
    queryKey: queryKeys.activity,
    queryFn: api.getActivity,
    staleTime: 2 * 60 * 1000, // 2 minutes
    ...options,
  });
}

export function useHealth(options?: UseQueryOptions<HealthCheckResponse>) {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: api.getHealth,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
    ...options,
  });
}

// Leads Hooks
export function useLeads(filters?: Record<string, unknown>, options?: UseQueryOptions<LeadsResponse>) {
  return useQuery({
    queryKey: queryKeys.leadsWithFilters(filters),
    queryFn: () => api.getLeads(filters),
    staleTime: 1 * 60 * 1000, // 1 minute
    ...options,
  });
}

export function useCreateLead(options?: UseMutationOptions<Lead, Error, Partial<Lead>>) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.createLead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.leads });
      toast({
        title: 'Lead opprettet',
        description: 'Den nye lead-en har blitt lagt til systemet.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kunne ikke opprette lead',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

export function useUpdateLead(options?: UseMutationOptions<Lead, Error, { id: string; data: Partial<Lead> }>) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => api.updateLead(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.leads });
      toast({
        title: 'Lead oppdatert',
        description: 'Endringene har blitt lagret.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kunne ikke oppdatere lead',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

export function useDeleteLead(options?: UseMutationOptions<void, Error, string>) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.deleteLead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.leads });
      toast({
        title: 'Lead slettet',
        description: 'Lead-en har blitt fjernet fra systemet.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kunne ikke slette lead',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

export function useBatchUpdateLeads(options?: UseMutationOptions<void, Error, BatchUpdateLeadsRequest>) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.batchUpdateLeads,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.leads });
      toast({
        title: 'Leads oppdatert',
        description: 'Alle valgte leads har blitt oppdatert.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kunne ikke oppdatere leads',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

// Sources Hooks
export function useSources(options?: UseQueryOptions<SourcesResponse>) {
  return useQuery({
    queryKey: queryKeys.sources,
    queryFn: api.getSources,
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

export function useCreateSource(options?: UseMutationOptions<Source, Error, Partial<Source>>) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.createSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      toast({
        title: 'Kilde opprettet',
        description: 'Den nye kilden har blitt lagt til systemet.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kunne ikke opprette kilde',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

export function useUpdateSource(options?: UseMutationOptions<Source, Error, { id: string; data: Partial<Source> }>) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => api.updateSource(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      toast({
        title: 'Kilde oppdatert',
        description: 'Endringene har blitt lagret.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kunne ikke oppdatere kilde',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

export function useDeleteSource(options?: UseMutationOptions<void, Error, string>) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.deleteSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
      toast({
        title: 'Kilde slettet',
        description: 'Kilden har blitt fjernet fra systemet.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kunne ikke slette kilde',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

export function useTestSource(options?: UseMutationOptions<void, Error, string>) {
  const { toast } = useToast();

  return useMutation({
    mutationFn: api.testSource,
    onSuccess: () => {
      toast({
        title: 'Kildetest vellykket',
        description: 'Kilden fungerer som forventet.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kildetest feilet',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

// Runs Hooks
export function useRuns(options?: UseQueryOptions<RunsResponse>) {
  return useQuery({
    queryKey: queryKeys.runs,
    queryFn: api.getRuns,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 5 * 1000, // Refetch every 5 seconds for live updates
    ...options,
  });
}

export function useCreateRun(options?: UseMutationOptions<{ runId: string }, Error, CreateRunRequest>) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.createRun,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.runs });
      toast({
        title: 'Kjøring startet',
        description: 'En ny OSINT-kjøring har blitt startet.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kunne ikke starte kjøring',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

export function useStopRun(options?: UseMutationOptions<void, Error, string>) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.stopRun,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.runs });
      toast({
        title: 'Kjøring stoppet',
        description: 'Kjøringen har blitt stoppet.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kunne ikke stoppe kjøring',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

export function useRunLogs(runId: string, options?: UseQueryOptions<{ logs: string[] }>) {
  return useQuery({
    queryKey: queryKeys.runLogs(runId),
    queryFn: () => api.getRunLogs(runId),
    enabled: !!runId,
    refetchInterval: 2 * 1000, // Refetch every 2 seconds
    ...options,
  });
}

// Campaigns Hooks
export function useCampaigns(options?: UseQueryOptions<CampaignsResponse>) {
  return useQuery({
    queryKey: queryKeys.campaigns,
    queryFn: api.getCampaigns,
    staleTime: 2 * 60 * 1000, // 2 minutes
    ...options,
  });
}

export function useCreateCampaign(options?: UseMutationOptions<Campaign, Error, CreateCampaignRequest>) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.createCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.campaigns });
      toast({
        title: 'Segment opprettet',
        description: 'Det nye segmentet har blitt lagt til systemet.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kunne ikke opprette segment',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

// Exports Hooks
export function useExports(options?: UseQueryOptions<ExportsResponse>) {
  return useQuery({
    queryKey: queryKeys.exports,
    queryFn: api.getExports,
    staleTime: 1 * 60 * 1000, // 1 minute
    ...options,
  });
}

export function useCreateExport(options?: UseMutationOptions<void, Error, CreateExportRequest>) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.createExport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.exports });
      toast({
        title: 'Export startet',
        description: 'Eksporten behandles og vil være klar om litt.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kunne ikke starte export',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

// Settings Hooks
export function useSettings(options?: UseQueryOptions<SettingsResponse>) {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: api.getSettings,
    staleTime: 10 * 60 * 1000, // 10 minutes
    ...options,
  });
}

export function useUpdateSettings(options?: UseMutationOptions<void, Error, UpdateSettingsRequest>) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings });
      toast({
        title: 'Innstillinger lagret',
        description: 'Endringene har blitt lagret.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Kunne ikke lagre innstillinger',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    },
    ...options,
  });
}

// WebSocket Hook for real-time updates
export function useWebSocket(url: string = 'ws://localhost:8000/ws') {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: ['websocket', url],
    queryFn: () => {
      return new Promise((resolve) => {
        const ws = new WebSocket(url);

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);

            // Handle different message types and invalidate appropriate queries
            switch (message.type) {
              case 'run_update':
              case 'run_complete':
              case 'run_error':
                queryClient.invalidateQueries({ queryKey: queryKeys.runs });
                break;
              case 'lead_created':
              case 'lead_updated':
                queryClient.invalidateQueries({ queryKey: queryKeys.leads });
                queryClient.invalidateQueries({ queryKey: queryKeys.kpis });
                break;
              case 'export_complete':
                queryClient.invalidateQueries({ queryKey: queryKeys.exports });
                break;
              case 'source_status_change':
                queryClient.invalidateQueries({ queryKey: queryKeys.sources });
                queryClient.invalidateQueries({ queryKey: queryKeys.health });
                break;
            }
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        ws.onopen = () => resolve(ws);
        ws.onerror = () => resolve(null);
      });
    },
    staleTime: Infinity,
    gcTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: true,
  });
}