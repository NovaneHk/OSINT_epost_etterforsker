'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';

interface Finding {
    category: string;
    severity: 'low' | 'medium' | 'high';
    details: string;
}

interface InvestigationDetails {
    id: string;
    email: string;
    status: 'pending' | 'in_progress' | 'completed' | 'failed';
    createdAt: string;
    score: number;
    findings: Finding[];
    metadata: {
        source: string;
        lastUpdated: string;
        confidence: number;
    };
}

const POLL_INTERVAL_MS = 4000;

export default function InvestigationDetailsPage() {
    const params = useParams();
    const router = useRouter();
    const [investigation, setInvestigation] = useState<InvestigationDetails | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const pollerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const mapResponse = (data: any): InvestigationDetails => ({
        id: data.id,
        email: data.email,
        status: data.status,
        createdAt: data.created_at || data.createdAt,
        score: data.score || 0,
        findings: (data.findings || []).map((f: any): Finding => {
            if (typeof f === 'object' && f !== null && f.category) {
                return {
                    category: f.category,
                    severity: (['low', 'medium', 'high'].includes(f.severity) ? f.severity : 'medium') as Finding['severity'],
                    details: f.details || '',
                };
            }
            return { category: 'Funn', severity: 'medium', details: typeof f === 'string' ? f : JSON.stringify(f) };
        }),
        metadata: {
            source: 'OSINT analyse',
            lastUpdated: data.completed_at || data.updated_at || data.created_at || '',
            confidence: data.score || 0,
        },
    });

    const fetchOnce = useCallback(async () => {
        try {
            const response = await api.getInvestigation(String(params.id));
            const mapped = mapResponse(response.data);
            setInvestigation(mapped);
            setIsLoading(false);
            // Stop polling when terminal state reached
            if (['completed', 'failed'].includes(mapped.status) && pollerRef.current) {
                clearInterval(pollerRef.current);
                pollerRef.current = null;
            }
        } catch (err) {
            setError('Kunne ikke hente undersøkelsesdetaljer');
            setIsLoading(false);
            if (pollerRef.current) {
                clearInterval(pollerRef.current);
                pollerRef.current = null;
            }
        }
    }, [params.id]);

    useEffect(() => {
        if (!params.id) return;
        fetchOnce();
        // Start polling; stops itself when status is terminal
        pollerRef.current = setInterval(fetchOnce, POLL_INTERVAL_MS);
        return () => {
            if (pollerRef.current) clearInterval(pollerRef.current);
        };
    }, [params.id, fetchOnce]);

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
            </div>
        );
    }

    if (error || !investigation) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <h2 className="text-xl text-red-600">{error || 'Undersøkelse ikke funnet'}</h2>
                    <button
                        onClick={() => router.push('/dashboard')}
                        className="mt-4 text-indigo-600 hover:text-indigo-800"
                    >
                        Tilbake til dashboard
                    </button>
                </div>
            </div>
        );
    }

    const isAnalyzing = investigation.status === 'pending' || investigation.status === 'in_progress';

    const statusLabel: Record<string, string> = {
        pending: 'Venter',
        in_progress: 'Analyserer…',
        completed: 'Fullført',
        failed: 'Feilet',
    };

    const statusColor: Record<string, string> = {
        pending: 'bg-yellow-100 text-yellow-800',
        in_progress: 'bg-blue-100 text-blue-800',
        completed: 'bg-green-100 text-green-800',
        failed: 'bg-red-100 text-red-800',
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'high': return 'bg-red-100 text-red-800';
            case 'medium': return 'bg-yellow-100 text-yellow-800';
            case 'low': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const severityLabel: Record<string, string> = { high: 'Høy', medium: 'Middels', low: 'Lav' };

    return (
        <div className="min-h-screen bg-gray-100 py-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="mb-8">
                    <button
                        onClick={() => router.push('/dashboard')}
                        className="text-indigo-600 hover:text-indigo-800"
                    >
                        ← Tilbake til dashboard
                    </button>
                </div>

                <div className="bg-white shadow overflow-hidden sm:rounded-lg">
                    <div className="px-4 py-5 sm:px-6 flex items-center justify-between">
                        <div>
                            <h3 className="text-lg leading-6 font-medium text-gray-900">
                                Undersøkelsesdetaljer
                            </h3>
                            <p className="mt-1 max-w-2xl text-sm text-gray-500">
                                {investigation.email}
                            </p>
                        </div>
                        <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${statusColor[investigation.status] || 'bg-gray-100 text-gray-700'}`}>
                            {isAnalyzing && (
                                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                                </svg>
                            )}
                            {statusLabel[investigation.status] || investigation.status}
                        </span>
                    </div>

                    {isAnalyzing && (
                        <div className="px-4 py-3 bg-blue-50 border-t border-blue-100 text-sm text-blue-700">
                            Analysen pågår — siden oppdateres automatisk…
                        </div>
                    )}

                    <div className="border-t border-gray-200 px-4 py-5 sm:px-6">
                        <dl className="grid grid-cols-1 gap-x-4 gap-y-8 sm:grid-cols-2">
                            <div className="sm:col-span-1">
                                <dt className="text-sm font-medium text-gray-500">Score</dt>
                                <dd className="mt-1 text-sm text-gray-900">
                                    {investigation.score > 0
                                        ? <span className="font-semibold">{investigation.score} / 100</span>
                                        : <span className="text-gray-400">{isAnalyzing ? 'Beregner…' : 'Ikke tilgjengelig'}</span>}
                                </dd>
                            </div>
                            <div className="sm:col-span-1">
                                <dt className="text-sm font-medium text-gray-500">Opprettet</dt>
                                <dd className="mt-1 text-sm text-gray-900">
                                    {investigation.createdAt ? new Date(investigation.createdAt).toLocaleString('nb-NO') : '—'}
                                </dd>
                            </div>
                            <div className="sm:col-span-2">
                                <dt className="text-sm font-medium text-gray-500 mb-2">Funn</dt>
                                <dd className="text-sm text-gray-900">
                                    {investigation.findings.length === 0 ? (
                                        <p className="text-gray-400 italic">
                                            {isAnalyzing ? 'Analysen er i gang…' : 'Ingen funn registrert.'}
                                        </p>
                                    ) : (
                                        <div className="space-y-3">
                                            {investigation.findings.map((finding, index) => (
                                                <div key={index} className="border rounded-lg p-4">
                                                    <div className="flex justify-between items-start">
                                                        <h4 className="font-medium">{finding.category}</h4>
                                                        <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${getSeverityColor(finding.severity)}`}>
                                                            {severityLabel[finding.severity] || finding.severity}
                                                        </span>
                                                    </div>
                                                    <p className="mt-1 text-gray-600">{finding.details}</p>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </dd>
                            </div>
                            {investigation.metadata.lastUpdated && (
                                <div className="sm:col-span-2">
                                    <dt className="text-sm font-medium text-gray-500">Sist oppdatert</dt>
                                    <dd className="mt-1 text-sm text-gray-900">
                                        {new Date(investigation.metadata.lastUpdated).toLocaleString('nb-NO')}
                                    </dd>
                                </div>
                            )}
                        </dl>
                    </div>
                </div>
            </div>
        </div>
    );
}