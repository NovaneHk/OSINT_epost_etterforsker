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

    const getApiBase = () => {
        if (typeof window !== 'undefined') {
            return window.location.origin;
        }

        return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    };

    useEffect(() => {
        if (!isAuthenticated) {
            return;
        }

        router.replace(getRedirectTarget());
    }, [isAuthenticated, router]);

    useEffect(() => {
        if (typeof window === 'undefined' || isAuthenticated || mfaRequired) {
            return;
        }

        const envAutoLogin = process.env.NEXT_PUBLIC_DEV_AUTO_LOGIN;
        const shouldAutoLogin = envAutoLogin
            ? envAutoLogin === 'true'
            : process.env.NODE_ENV !== 'production';
        const host = window.location.hostname;
        const isLocalhost = host === 'localhost' || host === '127.0.0.1';
        const username = process.env.NEXT_PUBLIC_DEV_AUTO_LOGIN_USERNAME || 'admin';
        const password = process.env.NEXT_PUBLIC_DEV_AUTO_LOGIN_PASSWORD || 'DevAuto123!';
        const hasToken = Boolean(getCookie('token') || window.localStorage.getItem('accessToken'));
        const attemptKey = `dev-auto-login-page-attempted:${username}`;
        const attemptedAt = Number(window.sessionStorage.getItem(attemptKey) || '0');
        const attemptedRecently = attemptedAt > 0 && Date.now() - attemptedAt < 15000;

        if (!shouldAutoLogin || !isLocalhost || hasToken || attemptedRecently) {
            return;
        }

        let cancelled = false;

        const runAutoLogin = async () => {
            try {
                window.sessionStorage.setItem(attemptKey, String(Date.now()));
                await login(username, password);
                if (!cancelled) {
                    router.replace(getRedirectTarget());
                }
            } catch {
                // Keep manual login path available if dev auto-login fails.
            }
        };

        void runAutoLogin();

        return () => {
            cancelled = true;
        };
    }, [isAuthenticated, login, mfaRequired, router]);

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
            const apiBase = getApiBase();
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
            const apiBase = getApiBase();
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
        <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f] px-4">
            {/* Subtle grid background */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:48px_48px] pointer-events-none" />

            <div className="relative w-full max-w-sm">
                {/* Logo / brand */}
                <div className="mb-8 text-center">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-indigo-600 mb-4 shadow-lg shadow-indigo-500/30">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                    </div>
                    <h1 className="text-2xl font-semibold text-white tracking-tight">Nova Trace</h1>
                    <p className="mt-1 text-sm text-zinc-500">
                        {mfaRequired ? 'To-faktor autentisering' : 'Logg inn på kontoen din'}
                    </p>
                </div>

                {/* Card */}
                <div className="bg-[#111118] border border-white/[0.06] rounded-2xl p-8 shadow-2xl shadow-black/60">
                    {!mfaRequired ? (
                        <form className="space-y-4" onSubmit={handleSubmit} noValidate>
                            <div className="space-y-3">
                                <div>
                                    <label htmlFor="username" className="block text-xs font-medium text-zinc-400 mb-1.5">
                                        E-postadresse
                                    </label>
                                    <input
                                        id="username"
                                        name="username"
                                        type="email"
                                        autoComplete="email"
                                        className="w-full px-3.5 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500/60 transition-all"
                                        placeholder="deg@domene.no"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                    />
                                    {emailError && <p className="text-red-400 text-xs mt-1.5">{emailError}</p>}
                                </div>
                                <div>
                                    <div className="flex items-center justify-between mb-1.5">
                                        <label htmlFor="password" className="block text-xs font-medium text-zinc-400">
                                            Passord
                                        </label>
                                        <a href="/forgot-password" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
                                            Glemt passord?
                                        </a>
                                    </div>
                                    <input
                                        id="password"
                                        name="password"
                                        type="password"
                                        autoComplete="current-password"
                                        className="w-full px-3.5 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-sm text-white placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500/60 transition-all"
                                        placeholder="••••••••"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                    />
                                    {passwordError && <p className="text-red-400 text-xs mt-1.5">{passwordError}</p>}
                                </div>
                            </div>

                            {error && (
                                <div className="flex items-center gap-2 px-3 py-2.5 bg-red-500/10 border border-red-500/20 rounded-lg">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-red-400 flex-shrink-0">
                                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                                        <path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                                    </svg>
                                    <span className="text-red-400 text-xs">{error}</span>
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={isLoading}
                                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 mt-2 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-[#111118] disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-500/20"
                            >
                                {isLoading ? <Spinner /> : 'Logg inn'}
                            </button>

                            <p className="text-center text-xs text-zinc-600 pt-1">
                                Ingen konto?{' '}
                                <a href="/register" className="text-indigo-400 hover:text-indigo-300 transition-colors">
                                    Opprett tilgang
                                </a>
                            </p>
                        </form>
                    ) : (
                        <form className="space-y-4" onSubmit={handleMfaSubmit}>
                            <div>
                                <p className="text-sm text-zinc-400 mb-4 leading-relaxed">
                                    Skriv inn 6-sifret kode fra autentiseringsappen din, eller bruk en reservekode.
                                </p>
                                <label htmlFor="mfaCode" className="block text-xs font-medium text-zinc-400 mb-1.5">
                                    Autentiseringskode
                                </label>
                                <input
                                    id="mfaCode"
                                    name="mfaCode"
                                    type="text"
                                    inputMode="numeric"
                                    autoComplete="one-time-code"
                                    required
                                    maxLength={8}
                                    className="w-full px-3.5 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-center text-xl tracking-[0.5em] font-mono placeholder-zinc-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500/60 transition-all"
                                    placeholder="000000"
                                    value={mfaCode}
                                    onChange={(e) => setMfaCode(e.target.value.replace(/[^0-9A-Fa-f]/g, ''))}
                                    autoFocus
                                />
                            </div>

                            {mfaError && (
                                <div className="flex items-center gap-2 px-3 py-2.5 bg-red-500/10 border border-red-500/20 rounded-lg">
                                    <span className="text-red-400 text-xs">{mfaError}</span>
                                </div>
                            )}

                            <div className="flex gap-3 pt-1">
                                <button
                                    type="button"
                                    onClick={() => { setMfaRequired(false); setMfaCode(''); setMfaError(''); }}
                                    className="flex-1 py-2.5 px-4 border border-white/[0.08] text-sm font-medium rounded-lg text-zinc-300 bg-white/[0.04] hover:bg-white/[0.08] transition-colors focus:outline-none focus:ring-2 focus:ring-white/20"
                                >
                                    Tilbake
                                </button>
                                <button
                                    type="submit"
                                    disabled={mfaLoading || mfaCode.length < 6}
                                    className="flex-1 flex justify-center py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-[#111118] disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {mfaLoading ? <Spinner /> : 'Bekreft'}
                                </button>
                            </div>
                        </form>
                    )}
                </div>

                <p className="mt-6 text-center text-xs text-zinc-700">
                    Nova Trace &mdash; B2B Intelligence Platform
                </p>
            </div>
        </div>
    );
}