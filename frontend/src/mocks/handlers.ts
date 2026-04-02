// @ts-nocheck - Mock data handlers, type mismatches are acceptable for testing
import { http, HttpResponse } from 'msw';
import type {
  KPIResponse,
  LeadsResponse,
  SourcesResponse,
  RunsResponse,
  ExportsResponse,
  SettingsResponse,
  Lead,
  Source,
  Run,
  Export
} from '@/types/api';

// Mock data generators
const generateMockLeads = (count: number): Lead[] => {
  const companies = ['TechCorp AS', 'InnovateLab', 'DataDriven Solutions', 'CloudFirst', 'AI Ventures', 'DigitalPioneer'];
  const roles = ['CTO', 'Tech Lead', 'VP Engineering', 'Head of Technology', 'Engineering Manager', 'Technical Director'];
  const locations = ['Oslo, Norge', 'Bergen, Norge', 'Trondheim, Norge', 'Stavanger, Norge', 'Kristiansand, Norge'];
  const tags = ['technology', 'b2b', 'saas', 'startup', 'enterprise', 'ai', 'cloud'];

  return Array.from({ length: count }, (_, i) => ({
    id: `lead_${i + 1}`,
    email: `user${i + 1}@${companies[i % companies.length].toLowerCase().replace(/\s+/g, '')}.com`,
    name: `Person ${i + 1}`,
    company: companies[i % companies.length],
    title: roles[i % roles.length],
    location: locations[i % locations.length],
    tags: [tags[i % tags.length], tags[(i + 1) % tags.length]],
    score: Math.floor(Math.random() * 40) + 60, // 60-100
    sourceIds: [`src_${Math.floor(i / 10) + 1}`],
    createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date().toISOString(),
    meta: {
      verified: Math.random() > 0.3,
      confidence: Math.random()
    }
  }));
};

const generateMockSources = (): Source[] => [
  {
    id: 'src_1',
    name: 'Norwegian Chamber of Commerce',
    kind: 'registry',
    url: 'https://www.chamber.no/member-directory',
    enabled: true,
    health: 'ok',
    lastRunAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'src_2',
    name: 'Nordic Tech Directory',
    kind: 'web',
    url: 'https://nordictech.directory/companies',
    enabled: true,
    health: 'ok',
    lastRunAt: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'src_3',
    name: 'LinkedIn Company Search',
    kind: 'social',
    url: 'https://linkedin.com/company',
    enabled: false,
    health: 'warn',
    lastRunAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'src_4',
    name: 'Crunchbase API',
    kind: 'api',
    url: 'https://api.crunchbase.com',
    enabled: true,
    health: 'ok',
    lastRunAt: new Date(Date.now() - 30 * 60 * 1000).toISOString()
  },
  {
    id: 'src_5',
    name: 'TechCrunch Events',
    kind: 'web',
    url: 'https://techcrunch.com/events',
    enabled: true,
    health: 'down',
    lastRunAt: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString()
  }
];

const generateMockRuns = (): Run[] => [
  {
    id: 'run_1',
    name: 'LinkedIn Scan',
    source_ids: ['src_1'],
    status: 'completed',
    progress: 100,
    leads_found: 76,
    leads_processed: 1200,
    errors_count: 0,
    started_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 2.5 * 60 * 60 * 1000).toISOString(),
    configuration: {},
    created_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 2.5 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'run_2',
    name: 'Company Search',
    source_ids: ['src_2'],
    status: 'running',
    progress: 65,
    leads_found: 28,
    leads_processed: 456,
    errors_count: 0,
    started_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    configuration: {},
    created_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 5 * 60 * 1000).toISOString()
  },
  {
    id: 'run_3',
    name: 'Email Discovery',
    source_ids: ['src_3'],
    status: 'failed',
    progress: 45,
    leads_found: 8,
    leads_processed: 234,
    errors_count: 1,
    started_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 5.8 * 60 * 60 * 1000).toISOString(),
    error_message: 'Connection timeout to source',
    configuration: {},
    created_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 5.8 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'run_4',
    name: 'Scheduled Scan',
    source_ids: ['src_1', 'src_2'],
    status: 'pending',
    progress: 0,
    leads_found: 0,
    leads_processed: 0,
    errors_count: 0,
    configuration: {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  }
];

const generateMockExports = (): Export[] => [
  {
    id: 'export_1',
    name: 'Lead Export CSV',
    type: 'csv',
    status: 'completed',
    file_path: '/api/exports/export_1/download',
    file_size: 524288,
    leads_count: 1247,
    progress: 100,
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 1.8 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'export_2',
    name: 'Lead Export JSON',
    type: 'json',
    status: 'processing',
    progress: 45,
    created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString()
  },
  {
    id: 'export_3',
    name: 'Lead Export Excel',
    type: 'xlsx',
    status: 'completed',
    file_path: '/api/exports/export_3/download',
    file_size: 312576,
    leads_count: 856,
    progress: 100,
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 23.5 * 60 * 60 * 1000).toISOString()
  }
];

let savedLeadViews = [
  {
    id: '1',
    name: 'Høy score tech',
    filters: {
      search: 'tech',
      tags: ['technology'],
      scoreRange: [80, 100],
      sources: []
    },
    isDefault: true,
    createdAt: new Date().toISOString()
  }
];

// API Handlers
export const handlers = [
  // Health check
  http.get('/api/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      cli_available: true,
      details: 'All systems operational'
    });
  }),

  // KPIs
  http.get('/api/kpis', () => {
    const kpis: KPIResponse = {
      data: {
        leads7d: 1247,
        hits7d: 15430,
        conversion_rate: 8.1,
        exports7d: 23,
        total_sources: 12,
        active_sources: 9
      },
      message: 'OK'
    };
    return HttpResponse.json(kpis);
  }),

  // Leads
  http.get('/api/leads', ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '50');
    const search = url.searchParams.get('search') || '';
    const tags = url.searchParams.get('tags')?.split(',').filter(Boolean) || [];
    const minScore = parseFloat(url.searchParams.get('minScore') || '0');

    // Generate mock data
    let allLeads = generateMockLeads(2000);

    // Apply filters
    if (search) {
      allLeads = allLeads.filter(lead =>
        lead.email?.toLowerCase().includes(search.toLowerCase()) ||
        lead.name?.toLowerCase().includes(search.toLowerCase()) ||
        lead.company?.toLowerCase().includes(search.toLowerCase()) ||
        lead.title?.toLowerCase().includes(search.toLowerCase())
      );
    }

    if (tags.length > 0) {
      allLeads = allLeads.filter(lead =>
        tags.some(tag => lead.tags.includes(tag))
      );
    }

    if (minScore > 0) {
      allLeads = allLeads.filter(lead => (lead.score || 0) >= minScore);
    }

    // Pagination
    const startIndex = (page - 1) * limit;
    const endIndex = startIndex + limit;
    const paginatedLeads = allLeads.slice(startIndex, endIndex);

    const response: LeadsResponse = {
      data: paginatedLeads,
      meta: {
        page,
        limit,
        total: allLeads.length,
        pages: Math.ceil(allLeads.length / limit)
      }
    };

    return HttpResponse.json(response);
  }),

  // Sources
  http.get('/api/sources', () => {
    const response: SourcesResponse = {
      data: generateMockSources()
    };
    return HttpResponse.json(response);
  }),

  // Runs
  http.get('/api/runs', () => {
    const response: RunsResponse = {
      data: generateMockRuns()
    };
    return HttpResponse.json(response);
  }),

  // Create run
  http.post('/api/runs', async ({ request }) => {
    const body = await request.json() as any;

    const newRun: Run = {
      id: `run_${Date.now()}`,
      status: 'queued',
      startedAt: undefined,
      finishedAt: undefined,
      stats: { scanned: 0, hits: 0, newLeads: 0, duplicates: 0 },
      logUrl: undefined
    };

    // Simulate starting the run after a delay
    setTimeout(() => {
      newRun.status = 'running';
      newRun.startedAt = new Date().toISOString();
    }, 1000);

    return HttpResponse.json({ data: newRun });
  }),

  // Exports
  http.get('/api/exports', () => {
    const response: ExportsResponse = {
      data: generateMockExports()
    };
    return HttpResponse.json(response);
  }),

  // Create export
  http.post('/api/exports', async ({ request }) => {
    const body = await request.json() as any;

    const newExport: Export = {
      id: `export_${Date.now()}`,
      format: body.format || 'CSV',
      status: 'queued',
      createdAt: new Date().toISOString()
    };

    return HttpResponse.json({ data: newExport });
  }),

  // Settings
  http.get('/api/settings', () => {
    const response: SettingsResponse = {
      system: {
        default_persona: 'technical_leaders',
        default_sector: 'technology',
        default_geo: 'nordics',
        rate_limit: 2.0,
        max_concurrent: 10,
        data_retention_days: 90,
        gdpr_compliance_mode: true
      },
      personas: {
        technical_leaders: {
          roles: ['CTO', 'Tech Lead', 'VP Engineering'],
          email_patterns: ['cto@', 'tech@', 'engineering@'],
          negative_signals: ['intern', 'junior', 'assistant'],
          scoring_weight: 40,
          priority_level: 'high'
        }
      },
      sources: {
        directories: {
          priority: 1,
          daily_limit: 1000,
          sources: [{
            name: 'Norwegian Chamber of Commerce',
            url: 'https://www.chamber.no/member-directory',
            type: 'static',
            enabled: true,
            credibility_score: 95
          }]
        }
      },
      rules: {}
    };
    return HttpResponse.json(response);
  }),

  // Update settings
  http.patch('/api/settings', async ({ request }) => {
    const updates = await request.json();
    return HttpResponse.json({
      success: true,
      message: 'Settings updated successfully',
      data: updates
    });
  }),

  // Batch update leads
  http.put('/api/leads/batch', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      success: true,
      message: `Updated ${body.leadIds?.length || 0} leads`,
      affectedIds: body.leadIds
    });
  }),

  http.get('/api/leads/views', () => {
    return HttpResponse.json(savedLeadViews);
  }),

  http.post('/api/leads/views', async ({ request }) => {
    const body = await request.json() as any;
    const newView = {
      id: `${Date.now()}`,
      name: body.name,
      filters: body.filters,
      isDefault: Boolean(body.is_default),
      createdAt: new Date().toISOString()
    };
    savedLeadViews = [newView, ...savedLeadViews];
    return HttpResponse.json(newView);
  }),

  http.delete('/api/leads/views/:id', ({ params }) => {
    savedLeadViews = savedLeadViews.filter((view) => view.id !== params.id);
    return HttpResponse.json({ success: true });
  }),

  http.post('/api/leads/batch', async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({
      success: true,
      updated_count: body.lead_ids?.length || 0
    });
  })
];