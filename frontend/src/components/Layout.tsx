import { ReactNode } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/store/auth';

interface LayoutProps {
    children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
    const { user, logout } = useAuthStore();

    return (
        <div className="min-h-screen bg-gray-100">
            <nav className="bg-white shadow-sm">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                        <div className="flex">
                            <div className="flex-shrink-0 flex items-center">
                                <Link href="/" className="text-xl font-bold text-gray-800">
                                    Nova Trace
                                </Link>
                            </div>
                            {user && (
                                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                                    <Link href="/dashboard" className="nav-link">
                                        Dashboard
                                    </Link>
                                    <Link href="/leads" className="nav-link">
                                        Leads
                                    </Link>
                                    <Link href="/exports" className="nav-link">
                                        Exports
                                    </Link>
                                    {user.role === 'admin' && (
                                        <Link href="/settings" className="nav-link">
                                            Settings
                                        </Link>
                                    )}
                                </div>
                            )}
                        </div>
                        <div className="flex items-center">
                            {user ? (
                                <div className="flex items-center space-x-4">
                                    <span className="text-gray-700">{user.username}</span>
                                    <button
                                        onClick={() => logout()}
                                        className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                                    >
                                        Logout
                                    </button>
                                </div>
                            ) : (
                                <Link
                                    href="/login"
                                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                                >
                                    Login
                                </Link>
                            )}
                        </div>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                {children}
            </main>
        </div>
    );
}