'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import InvestigationList, { Investigation } from '@/components/InvestigationList';
import { AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';

export default function ActiveInvestigationsPage() {
    const router = useRouter();
    const [filter, setFilter] = useState<'all' | 'in_progress' | 'pending'>('all');

    const { data: investigations, isLoading, error } = useQuery({
        queryKey: ['investigations', 'active'],
        queryFn: () => api.getActiveInvestigations(),
        refetchInterval: 30000 // Refresh every 30 seconds
    });

    const filteredInvestigations = investigations?.filter(
        (investigation: Investigation) =>
            filter === 'all' || investigation.status === filter
    );

    if (isLoading) {
        return (
            <div className="p-6">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
                    <div className="space-y-4">
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="h-32 bg-gray-200 rounded"></div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <div className="flex items-center gap-2 text-red-600 mb-4">
                    <AlertCircle className="h-5 w-5" />
                    <span>Feil ved lasting av aktive undersøkelser</span>
                </div>
                <p className="text-gray-600">Prøv å laste siden på nytt</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Aktive undersøkelser</h1>
                <p className="text-muted-foreground">
                    Oversikt over pågående og ventende undersøkelser
                </p>
            </div>

            <Separator />

            <Card className="p-4">
                <div className="flex justify-between items-center mb-4">
                    <div className="flex gap-2">
                        <button
                            onClick={() => setFilter('all')}
                            className={`px-3 py-1 rounded-md text-sm font-medium ${
                                filter === 'all'
                                    ? 'bg-indigo-100 text-indigo-700'
                                    : 'text-gray-500 hover:text-gray-700'
                            }`}
                        >
                            Alle
                        </button>
                        <button
                            onClick={() => setFilter('in_progress')}
                            className={`px-3 py-1 rounded-md text-sm font-medium ${
                                filter === 'in_progress'
                                    ? 'bg-blue-100 text-blue-700'
                                    : 'text-gray-500 hover:text-gray-700'
                            }`}
                        >
                            Pågår
                        </button>
                        <button
                            onClick={() => setFilter('pending')}
                            className={`px-3 py-1 rounded-md text-sm font-medium ${
                                filter === 'pending'
                                    ? 'bg-yellow-100 text-yellow-700'
                                    : 'text-gray-500 hover:text-gray-700'
                            }`}
                        >
                            Venter
                        </button>
                    </div>

                    <button
                        onClick={() => router.push('/new-investigation')}
                        className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                    >
                        Ny undersøkelse
                    </button>
                </div>

                <InvestigationList
                    investigations={filteredInvestigations || []}
                    onInvestigationClick={(investigation) =>
                        router.push(`/investigation/${investigation.id}`)
                    }
                />
            </Card>
        </div>
    );
}