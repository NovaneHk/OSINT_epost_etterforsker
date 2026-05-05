import { useEffect, useState } from 'react';
import { Investigation } from '@/types/api';
import { api } from '@/lib/api';
import InvestigationDetails from './InvestigationDetails';
import InvestigationDetailsSkeleton from './InvestigationDetailsSkeleton';

interface InvestigationDetailsContainerProps {
    investigationId: string;
}

export default function InvestigationDetailsContainer({ investigationId }: InvestigationDetailsContainerProps) {
    const [investigation, setInvestigation] = useState<Investigation | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchInvestigation() {
            try {
                setIsLoading(true);
                setError(null);
                const response = await api.getInvestigation(investigationId);
                setInvestigation(response.data);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Det oppstod en feil under henting av undersøkelsen');
            } finally {
                setIsLoading(false);
            }
        }

        fetchInvestigation();
    }, [investigationId]);

    if (isLoading) {
        return <InvestigationDetailsSkeleton />;
    }

    if (error) {
        return (
            <div className="rounded-md bg-red-50 p-4">
                <div className="flex">
                    <div className="ml-3">
                        <h3 className="text-sm font-medium text-red-800">
                            Kunne ikke laste undersøkelsen
                        </h3>
                        <div className="mt-2 text-sm text-red-700">
                            <p>{error}</p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (!investigation) {
        return (
            <div className="rounded-md bg-yellow-50 p-4">
                <div className="flex">
                    <div className="ml-3">
                        <h3 className="text-sm font-medium text-yellow-800">
                            Ingen undersøkelse funnet
                        </h3>
                    </div>
                </div>
            </div>
        );
    }

    return <InvestigationDetails investigation={investigation} />;
}