export interface KPIData {
    leadsLast7Days: number;
    conversionRate: number;
    activeSources: number;
    totalLeads: number;
}

export interface PaginationMeta {
    page: number;
    perPage: number;
    total: number;
    pages: number;
}

export interface ActivityResponse {
    activities: Activity[];
    meta: PaginationMeta;
    leads_timeline?: Array<{ date: string; count: number }>;
    campaign_stats?: Array<{ name: string; performance: number }>;
}

export interface Activity {
    id: string;
    type: 'lead_created' | 'export_completed' | 'campaign_started' | 'source_updated';
    description: string;
    timestamp: string;
    userId: string;
    entityId?: string;
    entityType?: string;
}

export interface HealthCheckResponse {
    status: 'healthy' | 'unhealthy';
    version: string;
    uptime: number;
    lastChecked: string;
    services: {
        database: 'up' | 'down';
        cache: 'up' | 'down';
        search: 'up' | 'down';
    };
}

export interface Lead {
    id: string;
    email: string;
    name?: string;
    company?: string;
    position?: string;
    phone?: string;
    linkedIn?: string;
    score?: number;
    status: 'new' | 'qualified' | 'contacted' | 'converted' | 'archived';
    createdAt: string;
    updatedAt: string;
    sourceId: string;
}

export interface LeadFilters {
    status?: string[];
    score?: { min?: number; max?: number };
    source?: string[];
    dateRange?: { from?: string; to?: string };
    search?: string;
    sort?: { field: string; direction: 'asc' | 'desc' };
}

export interface LeadsResponse {
    leads: Lead[];
    meta: PaginationMeta;
}