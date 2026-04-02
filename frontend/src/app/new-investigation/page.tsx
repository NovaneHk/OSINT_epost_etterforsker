'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function extractDomain(email: string): string | null {
    const at = email.indexOf('@');
    if (at === -1) return null;
    const domain = email.slice(at + 1).trim();
    return domain.length > 0 ? domain : null;
}

function statusLabel(status: string): { label: string; color: string } {
    switch (status) {
        case 'completed': return { label: 'Fullført', color: 'text-green-600' };
        case 'failed':    return { label: 'Feilet',   color: 'text-red-600' };
        case 'running':   return { label: 'Kjører',   color: 'text-blue-600' };
        default:          return { label: 'Venter',   color: 'text-gray-500' };
    }
}

interface Investigation {
    id: string;
    email: string;
    status: string;
    score?: number;
    created_at?: string;
}

export default function NewInvestigationPage() {
    const [email, setEmail] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [touched, setTouched] = useState(false);
    const [recent, setRecent] = useState<Investigation[]>([]);
    const router = useRouter();

    const domain = extractDomain(email);
    const emailValid = EMAIL_REGEX.test(email);
    const showValidationError = touched && email.length > 0 && !emailValid;

    useEffect(() => {
        api.getInvestigations({ limit: 5 })
            .then((res) => setRecent(res.data?.investigations ?? res.data ?? []))
            .catch(() => {/* silent */});
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setTouched(true);
        if (!emailValid) return;
        setIsSubmitting(true);
        setError(null);

        try {
            const response = await api.createInvestigation(email);
            router.push(`/investigation/${response.data.id}`);
        } catch (err) {
            setError('Kunne ikke opprette undersøkelsen. Vennligst prøv igjen.');
            console.error('Error creating investigation:', err);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-100 py-8">
            <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="mb-8">
                    <button
                        onClick={() => router.push('/dashboard')}
                        className="text-indigo-600 hover:text-indigo-800"
                    >
                        ← Tilbake til dashboard
                    </button>
                </div>

                <div className="bg-white shadow sm:rounded-lg mb-6">
                    <div className="px-4 py-5 sm:p-6">
                        <h3 className="text-lg leading-6 font-medium text-gray-900">
                            Ny undersøkelse
                        </h3>
                        <div className="mt-2 max-w-xl text-sm text-gray-500">
                            <p>
                                Skriv inn e-postadressen du ønsker å undersøke. Systemet vil
                                automatisk starte en grundig OSINT-analyse.
                            </p>
                        </div>
                        <form className="mt-5" onSubmit={handleSubmit} noValidate>
                            <div className="space-y-4">
                                <div>
                                    <label
                                        htmlFor="email"
                                        className="block text-sm font-medium text-gray-700"
                                    >
                                        E-postadresse
                                    </label>
                                    <div className="mt-1">
                                        <input
                                            type="email"
                                            name="email"
                                            id="email"
                                            autoComplete="off"
                                            className={`shadow-sm block w-full sm:text-sm rounded-md
                                                ${showValidationError
                                                    ? 'border-red-400 focus:ring-red-500 focus:border-red-500'
                                                    : emailValid && email.length > 0
                                                        ? 'border-green-400 focus:ring-green-500 focus:border-green-500'
                                                        : 'border-gray-300 focus:ring-indigo-500 focus:border-indigo-500'
                                                }`}
                                            placeholder="example@domain.com"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            onBlur={() => setTouched(true)}
                                        />
                                    </div>
                                    {showValidationError && (
                                        <p className="mt-1 text-xs text-red-600">
                                            Ugyldig e-postformat — bruk formatet bruker@domene.no
                                        </p>
                                    )}
                                    {emailValid && domain && (
                                        <p className="mt-1 text-xs text-gray-500">
                                            🌐 Domene: <span className="font-medium text-gray-700">{domain}</span>
                                        </p>
                                    )}
                                </div>

                                {error && (
                                    <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
                                        {error}
                                    </div>
                                )}

                                <div>
                                    <button
                                        type="submit"
                                        disabled={isSubmitting || (touched && !emailValid)}
                                        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {isSubmitting ? (
                                            <span className="flex items-center">
                                                <svg
                                                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                                                    xmlns="http://www.w3.org/2000/svg"
                                                    fill="none"
                                                    viewBox="0 0 24 24"
                                                >
                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                                </svg>
                                                Oppretter undersøkelse...
                                            </span>
                                        ) : (
                                            '🔍 Start undersøkelse'
                                        )}
                                    </button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>

                {recent.length > 0 && (
                    <div className="bg-white shadow sm:rounded-lg">
                        <div className="px-4 py-5 sm:p-6">
                            <h4 className="text-sm font-medium text-gray-700 mb-3">
                                Nylige undersøkelser
                            </h4>
                            <ul className="divide-y divide-gray-200">
                                {recent.map((inv) => {
                                    const { label, color } = statusLabel(inv.status);
                                    return (
                                        <li key={inv.id} className="py-2 flex items-center justify-between">
                                            <div>
                                                <Link
                                                    href={`/investigation/${inv.id}`}
                                                    className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                                                >
                                                    {inv.email}
                                                </Link>
                                                {inv.score != null && (
                                                    <span className="ml-2 text-xs text-gray-500">
                                                        Score: {inv.score}
                                                    </span>
                                                )}
                                            </div>
                                            <span className={`text-xs font-medium ${color}`}>{label}</span>
                                        </li>
                                    );
                                })}
                            </ul>
                            <div className="mt-3 text-right">
                                <Link href="/investigations" className="text-xs text-indigo-600 hover:underline">
                                    Se alle undersøkelser →
                                </Link>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}