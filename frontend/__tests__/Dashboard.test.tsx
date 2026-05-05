import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Dashboard from '@/app/dashboard/page';
import { api } from '@/lib/api';

// Mock the API
jest.mock('@/lib/api', () => ({
    api: {
        getKPIs: jest.fn(),
        getLeads: jest.fn()
    }
}));

function createWrapper() {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } }
    });
    return ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );
}

describe('Dashboard', () => {
    const mockKPIs = {
        leads7d: 100,
        hits7d: 75,
        conversion_rate: 75.0,
        exports7d: 12,
        total_sources: 8,
        active_sources: 5
    };

    beforeEach(() => {
        jest.clearAllMocks();
        (api.getKPIs as jest.Mock).mockResolvedValue(mockKPIs);
        (api.getLeads as jest.Mock).mockResolvedValue([]);
    });

    it('renders loading state initially', () => {
        (api.getKPIs as jest.Mock).mockReturnValue(new Promise(() => {}));
        render(<Dashboard />, { wrapper: createWrapper() });
        expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
    });

    it('displays KPIs after loading', async () => {
        render(<Dashboard />, { wrapper: createWrapper() });

        await waitFor(() => {
            expect(screen.getByText('Dashboard')).toBeInTheDocument();
            expect(screen.getByText('100')).toBeInTheDocument();
            expect(screen.getByText('75')).toBeInTheDocument();
            expect(screen.getByText('75.0%')).toBeInTheDocument();
        });
    });

    it('handles API errors gracefully', async () => {
        (api.getKPIs as jest.Mock).mockRejectedValue(new Error('API Error'));

        render(<Dashboard />, { wrapper: createWrapper() });

        await waitFor(() => {
            expect(screen.getByText('Feil ved lasting av dashboard data')).toBeInTheDocument();
        });
    });
});