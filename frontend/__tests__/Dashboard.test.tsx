import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import Dashboard from '@/app/dashboard/page';
import * as dashboardData from '@/lib/data/dashboard';
import * as runsData from '@/lib/data/runs';
import * as sourcesData from '@/lib/data/sources';
import * as leadsData from '@/lib/data/leads';

vi.mock('@/lib/data/dashboard');
vi.mock('@/lib/data/runs');
vi.mock('@/lib/data/sources');
vi.mock('@/lib/data/leads');
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/dashboard',
  useSearchParams: () => new URLSearchParams(),
}));

const METRICS_STUB = {
  ok: true as const,
  data: {
    leads7d: 187,
    leads7dChange: 14.2,
    searches7d: 24,
    searches7dChange: -4.5,
    conversionRate: 8.3,
    conversionRateChange: 1.1,
    exports7d: 6,
    exports7dChange: 50.0,
  },
};

beforeEach(() => {
  vi.mocked(dashboardData.getDashboardMetrics).mockResolvedValue(METRICS_STUB);
  vi.mocked(dashboardData.getDashboardTrends).mockResolvedValue({ ok: true, data: [] });
  vi.mocked(dashboardData.getDashboardActivity).mockResolvedValue({ ok: true, data: [] });
  vi.mocked(runsData.getActiveRuns).mockResolvedValue({ ok: true, data: [] });
  vi.mocked(sourcesData.getSourceHealth).mockResolvedValue({ ok: true, data: [] });
  vi.mocked(leadsData.getLeads).mockResolvedValue({
    ok: true,
    data: { items: [], page: 1, pageSize: 8, total: 0, hasNextPage: false },
  });
});

describe('Dashboard page', () => {
  it('shows skeleton loading state initially', () => {
    // Hang the first call to keep the loading state visible
    vi.mocked(dashboardData.getDashboardMetrics).mockReturnValue(new Promise(() => {}));
    render(<Dashboard />);
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders KPI labels after data loads', async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('Leads 7d')).toBeInTheDocument();
      expect(screen.getByText('Searches 7d')).toBeInTheDocument();
      expect(screen.getByText('Conversion Rate')).toBeInTheDocument();
      expect(screen.getByText('Exports 7d')).toBeInTheDocument();
    });
  });

  it('shows error banner when data layer throws', async () => {
    vi.mocked(dashboardData.getDashboardMetrics).mockRejectedValue(new Error('Network error'));
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('Failed to load dashboard')).toBeInTheDocument();
    });
  });
});
