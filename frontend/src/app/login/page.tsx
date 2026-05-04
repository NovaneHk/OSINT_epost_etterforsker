'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/auth';
import { getCookie, setCookie } from '@/utils/cookies';

export default function LoginPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [emailError, setEmailError] = useState('');
    const [passwordError, setPasswordError] = useState('');
    const [mfaRequired, setMfaRequired] = useState(false);
    const [mfaToken, setMfaToken] = useState('');
    const [mfaCode, setMfaCode] = useState('');
    const [mfaError, setMfaError] = useState('');
    const [mfaLoading, setMfaLoading] = useState(false);
    const { login, error, isLoading, isAuthenticated, initialize } = useAuthStore();
    const router = useRouter();

    const getRedirectTarget = () => {
        if (typeof window === 'undefined') {
            return '/dashboard';
        }

        return new URLSearchParams(window.location.search).get('redirect') || '/dashboard';
    };

    useEffect(() => {
        if (!isAuthenticated) {
            return;
        }

        router.replace(getRedirectTarget());
    }, [isAuthenticated, router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setMfaError('');
        setEmailError('');
        setPasswordError('');

        // Client-side validation
        let valid = true;
        if (!username.trim()) {
            setEmailError('Email is required');
            valid = false;
        }
        if (!password) {
            setPasswordError('Password is required');
            valid = false;
        }
        if (!valid) return;

        try {
            // POST JSON to backend auth endpoint (direct, browser-accessible URL)
            const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${apiBase}/api/auth/token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });
            const data = await res.json();
            if (!res.ok && !data.mfa_required) {
                throw new Error('Invalid credentials');
            }
            if (data.mfa_required) {
                setMfaToken(data.mfa_token);
                setMfaRequired(true);
                return;
            }
            // Normal login — store token and initialize session
            setCookie('token', data.access_token, { expires: 7 });
            window.localStorage.setItem('accessToken', data.access_token);
            await initialize();
            router.replace(getRedirectTarget());
        } catch (err) {
            useAuthStore.setState({
                error: err instanceof Error ? err.message : 'Invalid credentials',
                isLoading: false,
            });
        }
    };

    const handleMfaSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setMfaError('');
        setMfaLoading(true);
        try {
            const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${apiBase}/api/auth/mfa/verify-login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mfa_token: mfaToken, code: mfaCode }),
            });
            const data = await res.json();
            if (!res.ok) {
                setMfaError(data.detail || 'Ugyldig kode');
                return;
            }
            setCookie('token', data.access_token, { expires: 7 });
            window.localStorage.setItem('accessToken', data.access_token);
            await initialize();
            router.replace(getRedirectTarget());
        } catch {
            setMfaError('Noe gikk galt. Prøv igjen.');
        } finally {
            setMfaLoading(false);
        }
    };

    const Spinner = () => (
        <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
    );

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full space-y-8">
                <div>
                    <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
                        OSINT Email Investigator
                    </h2>
                    <p className="mt-2 text-center text-sm text-gray-600">
                        {mfaRequired ? 'To-faktor autentisering' : 'Logg inn for å fortsette'}
                    </p>
                </div>

                {!mfaRequired ? (
                    <form className="mt-8 space-y-6" onSubmit={handleSubmit} noValidate>
                        <div className="rounded-md shadow-sm -space-y-px">
                            <div>
                                <label htmlFor="username" className="sr-only">Email</label>
                                <input
                                    id="username"
                                    name="username"
                                    type="email"
                                    className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                                    placeholder="Email"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                />
                                {emailError && <p className="text-red-500 text-xs mt-1">{emailError}</p>}
                            </div>
                            <div>
                                <label htmlFor="password" className="sr-only">Passord</label>
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                                    placeholder="Passord"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                                {passwordError && <p className="text-red-500 text-xs mt-1">{passwordError}</p>}
                            </div>
                        </div>

                        {error && (
                            <div className="text-red-500 text-sm text-center">{error}</div>
                        )}

                        <div className="flex items-center justify-between text-sm">
                            <a href="/forgot-password" className="text-indigo-600 hover:text-indigo-500">
                                Forgot password?
                            </a>
                            <a href="/register" className="text-indigo-600 hover:text-indigo-500">
                                Create account
                            </a>
                        </div>

                        <div>
                            <button
                                type="submit"
                                disabled={isLoading}
                                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                            >
                                {isLoading ? <Spinner /> : 'Logg inn'}
                            </button>
                        </div>
                    </form>
                ) : (
                    <form className="mt-8 space-y-6" onSubmit={handleMfaSubmit}>
                        <div>
                            <p className="text-sm text-gray-600 mb-4">
                                Skriv inn 6-sifret kode fra autentiseringsappen din, eller bruk en reservekode.
                            </p>
                            <label htmlFor="mfaCode" className="sr-only">Autentiseringskode</label>
                            <input
                                id="mfaCode"
                                name="mfaCode"
                                type="text"
                                inputMode="numeric"
                                autoComplete="one-time-code"
                                required
                                maxLength={8}
                                className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md placeholder-gray-500 text-gray-900 text-center text-lg tracking-widest focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                                placeholder="000000"
                                value={mfaCode}
                                onChange={(e) => setMfaCode(e.target.value.replace(/[^0-9A-Fa-f]/g, ''))}
                                autoFocus
                            />
                        </div>

                        {mfaError && (
                            <div className="text-red-500 text-sm text-center">{mfaError}</div>
                        )}

                        <div className="flex space-x-3">
                            <button
                                type="button"
                                onClick={() => { setMfaRequired(false); setMfaCode(''); setMfaError(''); }}
                                className="flex-1 py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                            >
                                Tilbake
                            </button>
                            <button
                                type="submit"
                                disabled={mfaLoading || mfaCode.length < 6}
                                className="flex-1 flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                            >
                                {mfaLoading ? <Spinner /> : 'Bekreft'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}