interface StatsCardProps {
    title: string;
    value: number | string;
    description?: string;
    trend?: {
        value: number;
        label: string;
        isPositive: boolean;
    };
}

function StatsCard({ title, value, description, trend }: StatsCardProps) {
    return (
        <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
                <div className="flex items-center">
                    <div className="flex-1">
                        <div className="text-sm font-medium text-gray-500 truncate">
                            {title}
                        </div>
                        <div className="mt-1 text-3xl font-semibold text-gray-900">
                            {value}
                        </div>
                    </div>
                </div>
                {trend && (
                    <div className="mt-3">
                        <div className="flex items-center text-sm">
                            {trend.isPositive ? (
                                <svg
                                    className="flex-shrink-0 h-5 w-5 text-green-500"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                                    />
                                </svg>
                            ) : (
                                <svg
                                    className="flex-shrink-0 h-5 w-5 text-red-500"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M13 17h8m0 0v-8m0 8l-8-8-4 4-6-6"
                                    />
                                </svg>
                            )}
                            <span
                                className={`ml-2 ${
                                    trend.isPositive ? 'text-green-600' : 'text-red-600'
                                }`}
                            >
                                {trend.value}% {trend.label}
                            </span>
                        </div>
                    </div>
                )}
                {description && (
                    <div className="mt-3">
                        <div className="text-sm text-gray-500">{description}</div>
                    </div>
                )}
            </div>
        </div>
    );
}

interface DashboardStats {
    totalInvestigations: number;
    activeInvestigations: number;
    averageScore: number;
    completionRate: number;
}

export default function DashboardStats({ stats }: { stats: DashboardStats }) {
    return (
        <div>
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Statistikk
            </h3>
            <dl className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                <StatsCard
                    title="Totalt antall undersøkelser"
                    value={stats.totalInvestigations}
                    description="Alle undersøkelser utført i systemet"
                />
                <StatsCard
                    title="Aktive undersøkelser"
                    value={stats.activeInvestigations}
                    description="Undersøkelser som pågår nå"
                />
                <StatsCard
                    title="Gjennomsnittlig score"
                    value={stats.averageScore.toFixed(1)}
                    description="Basert på alle fullførte undersøkelser"
                />
                <StatsCard
                    title="Fullføringsrate"
                    value={`${stats.completionRate}%`}
                    description="Prosent av undersøkelser som er fullført"
                />
            </dl>
        </div>
    );
}