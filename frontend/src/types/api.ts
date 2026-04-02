// Base types
export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface APIResponse<T> {
  data: T;
  meta?: PaginationMeta;
  message?: string;
}

// Investigation types
export interface Investigation {
  id: string;
  email: string;
  status: 'pending' | 'in_progress' | 'completed';
  createdAt: string;
  completedAt?: string;
  score: number | null;
  findings: string[];
  error?: string;
}

export interface InvestigationsResponse extends APIResponse<Investigation[]> {}

export interface InvestigationResponse extends APIResponse<Investigation> {}

// Lead types
export interface Lead {
  id: string;
  email: string;
  name?: string;
  company?: string;
  domain?: string;
  job_title?: string;
  title?: string; // Alias for job_title
  phone?: string;
  linkedin_url?: string;
  twitter_url?: string;
  website?: string;
  location?: string;
  industry?: string;
  company_size?: string;
  revenue?: string;
  technologies?: string[];
  confidence_score: number;
  score?: number; // Alias for confidence_score
  verification_status: 'verified' | 'unverified' | 'invalid' | 'pending';
  engagement_score?: number;
  last_contacted?: string;
  source_id?: string;
  source_url?: string;
  notes?: string;
  tags?: string[];
  custom_fields?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface LeadsResponse extends APIResponse<Lead[]> {}

export interface LeadSavedView {
  id: string;
  name: string;
  filters: FilterState;
  scope?: 'private' | 'role' | 'global';
  ownerUserId?: string;
  ownerRole?: string;
  isDefault?: boolean;
  createdAt: string;
}

// Source types
export interface Source {
  id: string;
  name: string;
  type: 'website' | 'linkedin' | 'twitter' | 'directory' | 'api' | 'upload';
  url?: string;
  description?: string;
  configuration: Record<string, unknown>;
  status: 'active' | 'inactive' | 'error' | 'testing';
  health?: 'ok' | 'warning' | 'error';
  last_run?: string;
  next_run?: string;
  schedule?: string;
  leads_count: number;
  success_rate: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface SourcesResponse extends APIResponse<Source[]> {}

// Run types
export interface Run {
  id: string;
  name?: string;
  source_ids: string[];
  filters?: Record<string, unknown>;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled' | 'stopped';
  progress: number;
  leads_found: number;
  leads_processed: number;
  errors_count: number;
  started_at?: string;
  completed_at?: string;
  duration?: number;
  error_message?: string;
  configuration: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface RunsResponse extends APIResponse<Run[]> {}

export interface CreateRunRequest {
  name?: string;
  source_ids: string[];
  filters?: Record<string, unknown>;
  configuration?: Record<string, unknown>;
}

// Campaign types
export interface Campaign {
  id: string;
  name: string;
  description?: string;
  filter_criteria: Record<string, unknown>;
  status: 'draft' | 'active' | 'paused' | 'completed' | 'archived';
  leads_count: number;
  target_count?: number;
  target_sources?: string[];
  created_by?: string;
  started_at?: string;
  ended_at?: string;
  progress?: number;
  created_at: string;
  updated_at: string;
}

export interface CampaignsResponse extends APIResponse<Campaign[]> {}

export interface CreateCampaignRequest {
  name: string;
  description?: string;
  filter_criteria: Record<string, unknown>;
  target_count?: number;
  target_sources?: string[];
}

// Export types
export interface Export {
  id: string;
  name: string;
  type: 'csv' | 'xlsx' | 'json';
  filters?: Record<string, unknown>;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'expired';
  file_path?: string;
  file_size?: number;
  leads_count?: number;
  progress: number;
  created_at: string;
  completed_at?: string;
  expires_at?: string;
}

export interface ExportsResponse extends APIResponse<Export[]> {}

export interface CreateExportRequest {
  name: string;
  type: 'csv' | 'xlsx' | 'json';
  filters?: Record<string, unknown>;
  include_fields?: string[];
}

// Playbook types
export interface PlaybookStep {
  id: string;
  type: string;
  configuration: Record<string, unknown>;
  order: number;
}

export interface Playbook {
  id: string;
  name: string;
  description?: string;
  steps: PlaybookStep[];
  status: 'draft' | 'active' | 'inactive';
  runs_count: number;
  success_rate: number;
  created_at: string;
  updated_at: string;
}

export interface PlaybooksResponse extends APIResponse<Playbook[]> {}

export interface CreatePlaybookRequest {
  name: string;
  description?: string;
  steps: Omit<PlaybookStep, 'id'>[];
}

// Settings types
export interface Settings {
  email_verification: {
    enabled: boolean;
    provider: string;
    api_key?: string;
    daily_limit?: number;
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
    webhook_url?: string;
    slack_webhook?: string;
  };
  rate_limiting: {
    requests_per_minute: number;
    burst_limit: number;
  };
}

export interface SettingsResponse extends APIResponse<Settings> {}

export interface UpdateSettingsRequest extends Partial<Settings> {}

// Dashboard/Analytics types
export interface KPIData {
  leads7d: number;
  hits7d: number;
  conversion_rate: number;
  exports7d: number;
  total_sources: number;
  active_sources: number;
}

export interface KPIResponse extends APIResponse<KPIData> {}

export interface ActivityData {
  daily_stats: Array<{
    date: string;
    leads_found: number;
    leads_verified: number;
    sources_active: number;
  }>;
  hourly_stats: Array<{
    hour: number;
    leads_found: number;
    api_calls: number;
  }>;
  leads_timeline?: Array<{ date: string; count: number }>;
  runs_timeline?: Array<{ date: string; count: number }>;
  exports_timeline?: Array<{ date: string; count: number }>;
  campaign_stats?: Array<{ name: string; performance: number }>;
  sources_distribution?: Array<{ name: string; value: number }>;
  recent_activity?: Array<{
    type: string;
    description: string;
    timestamp: string;
    details?: string;
  }>;
  top_domains?: Array<{
    domain: string;
    count: number;
    percentage: number;
  }>;
  source_performance: Array<{
    source_id: string;
    source_name: string;
    leads_found: number;
    success_rate: number;
    avg_quality_score: number;
  }>;
}

export interface ActivityResponse extends APIResponse<ActivityData> {}

// Health check types
export interface HealthCheckData {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  services: {
    database: {
      status: 'up' | 'down';
      response_time?: number;
    };
    redis: {
      status: 'up' | 'down';
      response_time?: number;
    };
    email_service: {
      status: 'up' | 'down';
      response_time?: number;
    };
    external_apis: Array<{
      name: string;
      status: 'up' | 'down';
      response_time?: number;
    }>;
  };
  system: {
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
  };
}

export interface HealthCheckResponse extends APIResponse<HealthCheckData> {}

// Batch operations
export interface BatchUpdateLeadsRequest {
  lead_ids: string[];
  updates: Partial<Lead>;
}

// API Error types
export interface APIError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
  status_code: number;
}

// Upload types
export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

// Filter types for lead queries
export interface LeadFilters {
  search?: string;
  verification_status?: Lead['verification_status'][];
  confidence_score_min?: number;
  confidence_score_max?: number;
  industries?: string[];
  domains?: string[];
  source_ids?: string[];
  tags?: string[];
  date_from?: string;
  date_to?: string;
  campaign_id?: string;
  page?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// Frontend-specific filter types
export interface FilterState {
  search: string;
  tags: string[];
  scoreRange: [number, number];
  sources: string[];
  status?: string;
  dateRange?: { from: Date; to: Date };
}

export interface SortState {
  field: string;
  direction: 'asc' | 'desc';
}

// WebSocket message types
export interface WebSocketMessage {
  type: 'run_update' | 'run_complete' | 'run_error' | 'lead_created' | 'lead_updated' | 'export_complete' | 'source_status_change';
  data: Record<string, unknown>;
  timestamp: string;
}