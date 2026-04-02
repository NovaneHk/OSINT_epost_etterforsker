import { render, screen } from '@testing-library/react';
import InvestigationDetails from './InvestigationDetails';
import { Investigation } from '@/types/api';

const baseInvestigation = {
    id: '123',
    email: 'test@example.com',
    status: 'completed' as const,
    score: 85,
    createdAt: '2025-11-10T10:00:00Z',
    completedAt: '2025-11-10T10:30:00Z',
    findings: ['Suspicious Activity', 'Multiple Aliases']
} satisfies Partial<Investigation>;

const mockInvestigation: Investigation = {
    ...baseInvestigation,
    findings: baseInvestigation.findings ?? [],
    score: baseInvestigation.score ?? null
} satisfies Investigation;

describe('InvestigationDetails', () => {
    it('renders investigation details correctly', () => {
        render(<InvestigationDetails investigation={mockInvestigation} />);
        
        // Check if email is displayed
        expect(screen.getByText('test@example.com')).toBeInTheDocument();
        
        // Check status
        expect(screen.getByText('Fullført')).toBeInTheDocument();
        
        // Check score
        expect(screen.getByText('85')).toBeInTheDocument();
        
        // Check findings
        expect(screen.getByText('Suspicious Activity')).toBeInTheDocument();
        expect(screen.getByText('Multiple Aliases')).toBeInTheDocument();
    });

    it('handles error state correctly', () => {
        const errorInvestigation = {
            ...mockInvestigation,
            status: 'in_progress' as const,
            error: 'Failed to process email'
        };

        render(<InvestigationDetails investigation={errorInvestigation} />);
        
        expect(screen.getByText('Det oppstod en feil under undersøkelsen')).toBeInTheDocument();
        expect(screen.getByText('Failed to process email')).toBeInTheDocument();
    });

    it('displays timestamps in Norwegian format', () => {
        render(<InvestigationDetails investigation={mockInvestigation} />);
        
        // Note: The exact format will depend on the locale implementation
        expect(screen.getByText(/10\. november 2025/)).toBeInTheDocument();
    });

    it('handles null score correctly', () => {
        const nullScoreInvestigation: Investigation = {
            ...mockInvestigation,
            score: null
        };
        render(<InvestigationDetails investigation={nullScoreInvestigation} />);
        expect(screen.getByText('Ikke beregnet')).toBeInTheDocument();
    });

    it('handles missing findings correctly', () => {
        const noFindingsInvestigation: Investigation = {
            ...mockInvestigation,
            findings: []
        };
        render(<InvestigationDetails investigation={noFindingsInvestigation} />);
        expect(screen.queryByText('Funn')).not.toBeInTheDocument();
    });

    it('handles pending status correctly', () => {
        const pendingInvestigation: Investigation = {
            ...mockInvestigation,
            status: 'pending',
            completedAt: undefined
        };
        render(<InvestigationDetails investigation={pendingInvestigation} />);
        expect(screen.getByText('Venter')).toBeInTheDocument();
        expect(screen.queryByText(/Fullført:/)).not.toBeInTheDocument();
    });

    it('handles in_progress status correctly', () => {
        const inProgressInvestigation: Investigation = {
            ...mockInvestigation,
            status: 'in_progress',
            completedAt: undefined
        };
        render(<InvestigationDetails investigation={inProgressInvestigation} />);
        expect(screen.getByText('Pågår')).toBeInTheDocument();
    });

    it('displays multiple findings correctly', () => {
        const multipleFindings: Investigation = {
            ...mockInvestigation,
            findings: ['High Risk', 'Multiple Aliases', 'Suspicious Activity', 'Known Fraud']
        };
        render(<InvestigationDetails investigation={multipleFindings} />);
        expect(screen.getByText('High Risk')).toBeInTheDocument();
        expect(screen.getByText('Multiple Aliases')).toBeInTheDocument();
        expect(screen.getByText('Suspicious Activity')).toBeInTheDocument();
        expect(screen.getByText('Known Fraud')).toBeInTheDocument();
    });

    it('handles long email addresses correctly', () => {
        const longEmailInvestigation: Investigation = {
            ...mockInvestigation,
            email: 'very.long.email.address.that.might.cause.wrapping@really.long.domain.name.com'
        };
        render(<InvestigationDetails investigation={longEmailInvestigation} />);
        expect(screen.getByText(longEmailInvestigation.email)).toBeInTheDocument();
    });

    it('applies correct score colors based on value', () => {
        const testScores = [
            { score: 95, expectedClass: 'text-green-600' },
            { score: 75, expectedClass: 'text-yellow-600' },
            { score: 30, expectedClass: 'text-red-600' }
        ];

        testScores.forEach(({ score, expectedClass }) => {
            const scoreInvestigation: Investigation = {
                ...mockInvestigation,
                score
            };
            const { container, rerender } = render(<InvestigationDetails investigation={scoreInvestigation} />);
            const scoreElement = container.querySelector(`.${expectedClass}`);
            expect(scoreElement).toBeInTheDocument();
            rerender(<InvestigationDetails investigation={mockInvestigation} />);
        });
    });

    it('handles concurrent status and error states correctly', () => {
        const errorInvestigation: Investigation = {
            ...mockInvestigation,
            status: 'in_progress',
            error: 'API timeout occurred'
        };
        render(<InvestigationDetails investigation={errorInvestigation} />);
        
        // Should show both status and error
        expect(screen.getByText('Pågår')).toBeInTheDocument();
        expect(screen.getByText('Det oppstod en feil under undersøkelsen')).toBeInTheDocument();
        expect(screen.getByText('API timeout occurred')).toBeInTheDocument();
    });

    it('formats dates according to Norwegian locale', () => {
        const dateInvestigation: Investigation = {
            ...mockInvestigation,
            createdAt: '2025-11-10T14:30:00Z',
            completedAt: '2025-11-10T15:45:00Z'
        };
        render(<InvestigationDetails investigation={dateInvestigation} />);
        
        // Check for Norwegian date format
        expect(screen.getByText(/10\. november 2025/)).toBeInTheDocument();
        expect(screen.getByText(/14:30/)).toBeInTheDocument();
        expect(screen.getByText(/15:45/)).toBeInTheDocument();
    });
});