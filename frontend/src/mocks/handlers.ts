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
  ExportJob
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
    status: 'success',
    startedAt: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    finishedAt: new Date(Date.now() - 2.5 * 60 * 60 * 1000).toISOString(),
    stats: { scanned: 1200, hits: 89, newLeads: 76, duplicates: 13 },
    logUrl: '/api/runs/run_1/logs'
  },
  {
    id: 'run_2',
    status: 'running',
    startedAt: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    finishedAt: undefined,
    stats: { scanned: 456, hits: 34, newLeads: 28, duplicates: 6 },
    logUrl: '/api/runs/run_2/logs'
  },
  {
    id: 'run_3',
    status: 'error',
    startedAt: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
    finishedAt: new Date(Date.now() - 5.8 * 60 * 60 * 1000).toISOString(),
    stats: { scanned: 234, hits: 12, newLeads: 8, duplicates: 4 },
    error: 'Connection timeout to source',
    logUrl: '/api/runs/run_3/logs'
  },
  {
    id: 'run_4',
    status: 'queued',
    startedAt: undefined,
    finishedAt: undefined,
    stats: { scanned: 0, hits: 0, newLeads: 0, duplicates: 0 }
  }
];

const generateMockExports = (): ExportJob[] => [
  {
    id: 'export_1',
    format: 'CSV',
    status: 'done',
    rowCount: 1247,
    fileUrl: '/api/exports/export_1/download',
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    finishedAt: new Date(Date.now() - 1.8 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'export_2',
    format: 'JSON',
    status: 'running',
    createdAt: new Date(Date.now() - 10 * 60 * 1000).toISOString()
  },
  {
    id: 'export_3',
    format: 'PARQUET',
    status: 'done',
    rowCount: 856,
    fileUrl: '/api/exports/export_3/download',
    createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    finishedAt: new Date(Date.now() - 23.5 * 60 * 60 * 1000).toISOString()
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
      leads7d: 1247,
      hits7d: 15430,
      conversion_rate: 8.1,
      exports7d: 23,
      total_sources: 12,
      active_sources: 9
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
      pagination: {
        page,
        limit,
        total: allLeads.length,
        pages: Math.ceil(allLeads.length / limit)
      },
      filters: {
        search,
        tags,
        minScore: minScore > 0 ? minScore : undefined
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

    const newExport: ExportJob = {
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
  })
];