'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/store/auth';

export function AuthBootstrap() {
  const initialize = useAuthStore((state) => state.initialize);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const getRedirectTarget = () => {
    if (typeof window === 'undefined') {
      return '/dashboard';
    }

    const redirectTarget = new URLSearchParams(window.location.search).get('redirect');
    return redirectTarget || '/dashboard';
  };

  const isLoginRoute = () => {
    if (typeof window === 'undefined') {
      return false;
    }

    const normalizedPath = window.location.pathname.replace(/^\/(nb|en)(?=\/|$)/, '') || '/';
    return normalizedPath === '/login';
  };

  useEffect(() => {
    if (!isAuthenticated || !isLoginRoute()) {
      return;
    }

    window.location.replace(getRedirectTarget());
  }, [isAuthenticated]);

  useEffect(() => {
    const bootstrapAuth = async () => {
      await initialize();

      if (typeof window === 'undefined') {
        return;
      }

      const envAutoLogin = process.env.NEXT_PUBLIC_DEV_AUTO_LOGIN;
      const shouldAutoLogin = envAutoLogin
        ? envAutoLogin === 'true'
        : process.env.NODE_ENV !== 'production';
      const username = process.env.NEXT_PUBLIC_DEV_AUTO_LOGIN_USERNAME || 'admin';
      const password = process.env.NEXT_PUBLIC_DEV_AUTO_LOGIN_PASSWORD || 'DevAuto123!';
      const host = window.location.hostname;
      const isLocalhost = host === '127.0.0.1' || host === 'localhost';
      const hasToken = Boolean(window.localStorage.getItem('accessToken'));
      const attemptKey = `dev-auto-login-attempted:${username || 'unknown'}`;
      const attemptedAt = Number(window.sessionStorage.getItem(attemptKey) || '0');
      const attemptedRecently = attemptedAt > 0 && Date.now() - attemptedAt < 15000;

      if (!shouldAutoLogin || !isLocalhost || hasToken || attemptedRecently) {
        return;
      }

      // Sprint 1 mock mode — no real backend running.
      // Inject a dev user directly into the store instead of calling api.login().
      // When the real backend is connected (Sprint 2), remove this block and
      // restore: await login(username, password); window.location.replace(getRedirectTarget());
      window.sessionStorage.setItem(attemptKey, String(Date.now()));
      useAuthStore.setState({
        user: {
          id: 'dev-user-1',
          email: `${username}@novatrace.io`,
          username,
          role: 'admin' as const,
          token: 'dev-mock-token',
        },
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    };

    void bootstrapAuth();
  }, [initialize]);

  return null;
}