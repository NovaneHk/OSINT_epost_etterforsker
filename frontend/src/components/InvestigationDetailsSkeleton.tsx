export default function InvestigationDetailsSkeleton() {
    return (
        <div className="bg-white shadow sm:rounded-lg animate-pulse">
            <div className="px-4 py-5 sm:p-6">
                <div className="space-y-6">
                    {/* Header */}
                    <div>
                        <div className="h-6 w-48 bg-gray-200 rounded"></div>
                        <div className="mt-1 h-4 w-64 bg-gray-200 rounded"></div>
                    </div>

                    {/* Status and Score */}
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div>
                            <div className="h-4 w-16 bg-gray-200 rounded"></div>
                            <div className="mt-1 flex items-center space-x-2">
                                <div className="h-5 w-5 bg-gray-200 rounded-full"></div>
                                <div className="h-5 w-24 bg-gray-200 rounded"></div>
                            </div>
                        </div>

                        <div>
                            <div className="h-4 w-16 bg-gray-200 rounded"></div>
                            <div className="mt-1">
                                <div className="h-6 w-20 bg-gray-200 rounded-full"></div>
                            </div>
                        </div>
                    </div>

                    {/* Timestamps */}
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div>
                            <div className="h-4 w-20 bg-gray-200 rounded"></div>
                            <div className="mt-1 h-5 w-40 bg-gray-200 rounded"></div>
                        </div>

                        <div>
                            <div className="h-4 w-20 bg-gray-200 rounded"></div>
                            <div className="mt-1 h-5 w-40 bg-gray-200 rounded"></div>
                        </div>
                    </div>

                    {/* Findings */}
                    <div>
                        <div className="h-4 w-16 bg-gray-200 rounded"></div>
                        <div className="mt-2 flex flex-wrap gap-2">
                            {[...Array(3)].map((_, i) => (
                                <div key={i} className="h-6 w-32 bg-gray-200 rounded-full"></div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}