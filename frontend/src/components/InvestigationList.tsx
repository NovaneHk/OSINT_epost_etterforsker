import { format } from 'date-fns';
import { CheckCircle, Clock, AlertTriangle } from 'lucide-react';

const formatDate = (date: string) => {
  return format(new Date(date), 'dd.MM.yyyy HH:mm');
};

export interface Investigation {
    id: string;
    email: string;
    status: 'completed' | 'in_progress' | 'pending';
    createdAt: string;
    completedAt?: string;
    score: number | null;
    findings: string[];
    error?: string;
}

interface InvestigationListItemProps {
    investigation: Investigation;
    onClick?: () => void;
}

export function InvestigationListItem({ investigation, onClick }: InvestigationListItemProps) {
    const statusConfig = {
        completed: {
            label: 'Fullført',
            icon: CheckCircle,
            className: 'text-green-600 bg-green-50',
        },
        in_progress: {
            label: 'Pågår',
            icon: Clock,
            className: 'text-blue-600 bg-blue-50',
        },
        pending: {
            label: 'Venter',
            icon: Clock,
            className: 'text-yellow-600 bg-yellow-50',
        },
        error: {
            label: 'Feilet',
            icon: AlertTriangle,
            className: 'text-red-600 bg-red-50',
        },
    };

    const status = investigation.error ? 'error' : investigation.status;
    const StatusIcon = statusConfig[status].icon;

    return (
        <div
            onClick={onClick}
            className={`p-4 border-b last:border-b-0 hover:bg-gray-50 transition-colors ${
                onClick ? 'cursor-pointer' : ''
            }`}
        >
            <div className="flex justify-between items-start">
                <div className="space-y-1">
                    <p className="text-sm font-medium text-gray-900">
                        {investigation.email}
                    </p>
                    <div className="flex items-center space-x-2 text-xs text-gray-500">
                        <span>
                            Opprettet {formatDate(investigation.createdAt)}
                        </span>
                        {investigation.completedAt && (
                            <>
                                <span>•</span>
                                <span>
                                    Fullført {formatDate(investigation.completedAt)}
                                </span>
                            </>
                        )}
                    </div>
                </div>
                <div className={`rounded-full px-2 py-1 text-xs font-medium flex items-center space-x-1 ${statusConfig[status].className}`}>
                    <StatusIcon className="h-3 w-3" />
                    <span>{statusConfig[status].label}</span>
                </div>
            </div>
            
            {investigation.score !== null && (
                <div className="mt-2">
                    <div className="inline-flex items-center px-2 py-1 rounded-md bg-gray-100 text-xs font-medium text-gray-700">
                        Score: {investigation.score}
                    </div>
                </div>
            )}

            {investigation.findings && investigation.findings.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                    {investigation.findings.map((finding, idx) => (
                        <span
                            key={idx}
                            className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-indigo-50 text-indigo-700"
                        >
                            {finding}
                        </span>
                    ))}
                </div>
            )}

            {investigation.error && (
                <div className="mt-2 text-sm text-red-600">
                    {investigation.error}
                </div>
            )}
        </div>
    );
}

interface InvestigationListProps {
    investigations: Investigation[];
    title?: string;
    description?: string;
    onInvestigationClick?: (investigation: Investigation) => void;
}

export default function InvestigationList({
    investigations,
    title,
    description,
    onInvestigationClick,
}: InvestigationListProps) {
    return (
        <div className="bg-white shadow rounded-lg overflow-hidden">
            {(title || description) && (
                <div className="px-4 py-5 sm:px-6">
                    {title && (
                        <h3 className="text-lg font-medium leading-6 text-gray-900">
                            {title}
                        </h3>
                    )}
                    {description && (
                        <p className="mt-1 max-w-2xl text-sm text-gray-500">
                            {description}
                        </p>
                    )}
                </div>
            )}
            <div className="divide-y divide-gray-200">
                {investigations.map((investigation) => (
                    <InvestigationListItem
                        key={investigation.id}
                        investigation={investigation}
                        onClick={
                            onInvestigationClick
                                ? () => onInvestigationClick(investigation)
                                : undefined
                        }
                    />
                ))}
            </div>
        </div>
    );
}