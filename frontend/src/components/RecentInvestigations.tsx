interface RecentInvestigation {
    id: string;
    email: string;
    status: 'completed' | 'in_progress' | 'pending';
    createdAt: string;
    completedAt?: string;
    score: number;
    findings: string[];
}

export default function RecentInvestigations({
    investigations,
}: {
    investigations: RecentInvestigation[];
}) {
    return (
        <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="px-4 py-5 sm:px-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900">
                    Nylige undersøkelser
                </h3>
                <p className="mt-1 max-w-2xl text-sm text-gray-500">
                    De 5 siste undersøkelsene som er fullført.
                </p>
            </div>
            <div className="border-t border-gray-200">
                <ul role="list" className="divide-y divide-gray-200">
                    {investigations.map((investigation) => (
                        <li key={investigation.id} className="px-4 py-4 sm:px-6">
                            <div className="flex items-center justify-between">
                                <div className="flex flex-col">
                                    <p className="text-sm font-medium text-indigo-600 truncate">
                                        {investigation.email}
                                    </p>
                                    <div className="mt-2 flex">
                                        <div className="flex items-center text-sm text-gray-500">
                                            <svg
                                                className="flex-shrink-0 mr-1.5 h-5 w-5 text-gray-400"
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24"
                                            >
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                                                />
                                            </svg>
                                            <span>
                                                {new Date(investigation.createdAt).toLocaleDateString('nb-NO')}
                                            </span>
                                        </div>
                                        <div className="ml-4 flex items-center text-sm text-gray-500">
                                            <svg
                                                className="flex-shrink-0 mr-1.5 h-5 w-5 text-gray-400"
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24"
                                            >
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                                                />
                                            </svg>
                                            Score: {investigation.score}
                                        </div>
                                    </div>
                                </div>
                                <div>
                                    {investigation.status === 'completed' && (
                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                            Fullført
                                        </span>
                                    )}
                                    {investigation.status === 'in_progress' && (
                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                            Pågår
                                        </span>
                                    )}
                                    {investigation.status === 'pending' && (
                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                            Venter
                                        </span>
                                    )}
                                </div>
                            </div>
                            {investigation.findings && investigation.findings.length > 0 && (
                                <div className="mt-2">
                                    <div className="flex flex-wrap gap-2">
                                        {investigation.findings.map((finding, idx) => (
                                            <span
                                                key={idx}
                                                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800"
                                            >
                                                {finding}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
}