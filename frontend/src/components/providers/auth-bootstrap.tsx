'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/store/auth';

export function AuthBootstrap() {
  const initialize = useAuthStore((state) => state.initialize);
  const login = useAuthStore((state) => state.login);
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

      const shouldAutoLogin = process.env.NEXT_PUBLIC_DEV_AUTO_LOGIN === 'true';
      const username = process.env.NEXT_PUBLIC_DEV_AUTO_LOGIN_USERNAME;
      const password = process.env.NEXT_PUBLIC_DEV_AUTO_LOGIN_PASSWORD;
      const host = window.location.hostname;
      const isLocalhost = host === '127.0.0.1' || host === 'localhost';
      const hasToken = Boolean(window.localStorage.getItem('accessToken'));
      const attempted = window.sessionStorage.getItem('dev-auto-login-attempted') === 'true';

      if (!shouldAutoLogin || !isLocalhost || !username || !password || hasToken || attempted) {
        return;
      }

      try {
        window.sessionStorage.setItem('dev-auto-login-attempted', 'true');
        await login(username, password);
        window.location.replace(getRedirectTarget());
      } catch (error) {
        console.error('Dev auto-login failed:', error);
      }
    };

    void bootstrapAuth();
  }, [initialize, login]);

  return null;
}