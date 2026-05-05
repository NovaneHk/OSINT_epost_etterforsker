import { useMemo } from 'react';
import { CheckCircle, Clock, AlertTriangle } from 'lucide-react';
import { formatScore, getScoreColor } from '@/utils/score';
import FindingBadge from './FindingBadge';
import { Investigation } from '@/types/api';

const statusConfig = {
    completed: {
        label: 'Fullført',
        icon: CheckCircle,
        className: 'text-green-600',
    },
    in_progress: {
        label: 'Pågår',
        icon: Clock,
        className: 'text-blue-600',
    },
    pending: {
        label: 'Venter',
        icon: Clock,
        className: 'text-yellow-600',
    },
};

interface InvestigationDetailsProps {
    investigation: Investigation;
}

export default function InvestigationDetails({ investigation }: InvestigationDetailsProps) {
    const status = investigation.error ? 'error' : investigation.status;
    const StatusIcon = status === 'error' ? AlertTriangle : statusConfig[investigation.status].icon;
    const statusLabel = status === 'error' ? 'Feilet' : statusConfig[investigation.status].label;
    const statusClass = status === 'error' ? 'text-red-600' : statusConfig[investigation.status].className;

    const scoreColors = useMemo(() => 
        investigation.score !== null ? getScoreColor(investigation.score) : { bg: 'bg-gray-100', text: 'text-gray-600', border: 'border-gray-200' }
    , [investigation.score]);

    return (
        <div className="bg-white shadow sm:rounded-lg">
            <div className="px-4 py-5 sm:p-6">
                <div className="space-y-6">
                    {/* Header */}
                    <div>
                        <h3 className="text-lg font-medium leading-6 text-gray-900">
                            Undersøkelsesdetaljer
                        </h3>
                        <p className="mt-1 text-sm text-gray-500">
                            {investigation.email}
                        </p>
                    </div>

                    {/* Status and Score */}
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div>
                            <label className="text-sm font-medium text-gray-500">Status</label>
                            <div className="mt-1 flex items-center space-x-2">
                                <StatusIcon className={`h-5 w-5 ${statusClass}`} />
                                <span className={`text-sm ${statusClass} font-medium`}>
                                    {statusLabel}
                                </span>
                            </div>
                        </div>

                        <div>
                            <label className="text-sm font-medium text-gray-500">Score</label>
                            <div className="mt-1">
                                <span
                                    className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${scoreColors.bg} ${scoreColors.text} border ${scoreColors.border}`}
                                >
                                    {investigation.score !== null ? formatScore(investigation.score) : 'Ikke beregnet'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Timestamps */}
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div>
                            <label className="text-sm font-medium text-gray-500">Opprettet</label>
                            <p className="mt-1 text-sm text-gray-900">
                                {new Date(investigation.createdAt).toLocaleDateString('nb-NO', {
                                    year: 'numeric',
                                    month: 'long',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit',
                                })}
                            </p>
                        </div>

                        {investigation.completedAt && (
                            <div>
                                <label className="text-sm font-medium text-gray-500">Fullført</label>
                                <p className="mt-1 text-sm text-gray-900">
                                    {new Date(investigation.completedAt).toLocaleDateString('nb-NO', {
                                        year: 'numeric',
                                        month: 'long',
                                        day: 'numeric',
                                        hour: '2-digit',
                                        minute: '2-digit',
                                    })}
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Findings */}
                    {investigation.findings && investigation.findings.length > 0 && (
                        <div>
                            <label className="text-sm font-medium text-gray-500">Funn</label>
                            <div className="mt-2 flex flex-wrap gap-2">
                                {investigation.findings.map((finding, index) => (
                                    <FindingBadge key={index} text={finding} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Error */}
                    {investigation.error && (
                        <div className="rounded-md bg-red-50 p-4">
                            <div className="flex">
                                <div className="flex-shrink-0">
                                    <AlertTriangle className="h-5 w-5 text-red-400" aria-hidden="true" />
                                </div>
                                <div className="ml-3">
                                    <h3 className="text-sm font-medium text-red-800">
                                        Det oppstod en feil under undersøkelsen
                                    </h3>
                                    <div className="mt-2 text-sm text-red-700">
                                        <p>{investigation.error}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}