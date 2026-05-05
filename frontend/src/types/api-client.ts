import { Investigation } from '@/components/InvestigationList';
import type { 
  KPIData, 
  ActivityResponse, 
  HealthCheckResponse, 
  LeadsResponse, 
  Lead, 
  LeadFilters, 
  BatchUpdateLeadsRequest,
  SourcesResponse,
  Source,
  RunsResponse,
  CreateRunRequest,
  CampaignsResponse,
  Campaign,
  CreateCampaignRequest,
  ExportsResponse,
  CreateExportRequest,
  PlaybooksResponse,
  Playbook,
  CreatePlaybookRequest,
  SettingsResponse,
  UpdateSettingsRequest
} from './api';

export interface APIClient {
    // KPIs and Dashboard
    getKPIs: () => Promise<KPIData>;
    getActivity: () => Promise<ActivityResponse>;
    getHealth: () => Promise<HealthCheckResponse>;

    // Leads
    getLeads: (filters?: LeadFilters) => Promise<LeadsResponse>;
    createLead: (data: Partial<Lead>) => Promise<Lead>;
    updateLead: (id: string, data: Partial<Lead>) => Promise<Lead>;
    deleteLead: (id: string) => Promise<void>;
    batchUpdateLeads: (data: BatchUpdateLeadsRequest) => Promise<void>;

    // Sources
    getSources: () => Promise<SourcesResponse>;
    createSource: (data: Partial<Source>) => Promise<Source>;
    updateSource: (id: string, data: Partial<Source>) => Promise<Source>;
    deleteSource: (id: string) => Promise<void>;
    testSource: (id: string) => Promise<void>;

    // Runs
    getRuns: () => Promise<RunsResponse>;
    createRun: (data: CreateRunRequest) => Promise<{ runId: string }>;
    stopRun: (id: string) => Promise<void>;
    getRunLogs: (id: string) => Promise<{ logs: string[] }>;

    // Campaigns
    getCampaigns: () => Promise<CampaignsResponse>;
    createCampaign: (data: CreateCampaignRequest) => Promise<Campaign>;
    updateCampaign: (id: string, data: Partial<Campaign>) => Promise<Campaign>;
    deleteCampaign: (id: string) => Promise<void>;

    // Exports
    getExports: () => Promise<ExportsResponse>;
    createExport: (data: CreateExportRequest) => Promise<void>;
    downloadExport: (id: string, filename?: string) => Promise<void>;

    // Playbooks
    getPlaybooks: () => Promise<PlaybooksResponse>;
    createPlaybook: (data: CreatePlaybookRequest) => Promise<Playbook>;
    updatePlaybook: (id: string, data: Partial<Playbook>) => Promise<Playbook>;
    deletePlaybook: (id: string) => Promise<void>;

    // Settings
    getSettings: () => Promise<SettingsResponse>;
    updateSettings: (data: UpdateSettingsRequest) => Promise<void>;

    // File upload
    uploadFile: <T>(endpoint: string, file: File, onProgress?: (progress: number) => void) => Promise<T>;

    // Investigations
    getInvestigations: (params?: {
        status?: 'pending' | 'in_progress' | 'completed';
        limit?: number;
        offset?: number;
    }) => Promise<InvestigationsResponse>;
    getActiveInvestigations: () => Promise<Investigation[]>;
    createInvestigation: (email: string) => Promise<InvestigationResponse>;
    getInvestigation: (id: string) => Promise<InvestigationResponse>;
}

export interface InvestigationsResponse {
    data: Investigation[];
    total: number;
}

export interface InvestigationResponse {
    data: Investigation;
}

// Re-export other types from api.ts
export * from './api';