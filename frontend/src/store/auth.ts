import { create } from 'zustand';
import { api } from '@/lib/api';
import { AuthState, AuthStore } from '@/types/auth';
import { getCookie, setCookie, removeCookie } from '@/utils/cookies';

const initialState: AuthState = {
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
};

interface AuthenticatedUserResponse {
    id: string;
    email: string;
    username?: string;
    role: 'admin' | 'manager' | 'analyst' | 'viewer';
}

export const useAuthStore = create<AuthStore>((set) => ({
    ...initialState,

    initialize: async () => {
        if (typeof window === 'undefined') {
            return;
        }

        const token = getCookie('token') || window.localStorage.getItem('accessToken');
        if (!token) {
            set({ ...initialState, isLoading: false });
            return;
        }

        set({ isLoading: true, error: null });

        try {
            window.localStorage.setItem('accessToken', token);

            const data = await api.getCurrentUser() as unknown as AuthenticatedUserResponse;
            set({
                user: {
                    id: data.id,
                    email: data.email,
                    username: data.username || data.email,
                    role: data.role,
                    token,
                },
                isAuthenticated: true,
                isLoading: false,
                error: null,
            });
        } catch (error) {
            removeCookie('token');
            window.localStorage.removeItem('accessToken');
            set({
                ...initialState,
                isLoading: false,
                error: error instanceof Error ? error.message : 'Authentication restore failed',
            });
        }
    },

    login: async (username: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
            const data = await api.login(username, password);
            const user = {
                ...data.user,
                username: data.user.username || username,
                token: data.access_token,
            };

            // Set token in HTTP-only cookie with 7 days expiration
            setCookie('token', data.access_token, { expires: 7 });
            window.localStorage.setItem('accessToken', data.access_token);
            
            set({
                user,
                isAuthenticated: true,
                isLoading: false,
                error: null,
            });
        } catch (error) {
            set({
                user: null,
                isAuthenticated: false,
                isLoading: false,
                error: error instanceof Error ? error.message : 'An unknown error occurred',
            });
            throw error;
        }
    },

    logout: () => {
        api.logout().catch(() => undefined);
        removeCookie('token');
        if (typeof window !== 'undefined') {
            window.localStorage.removeItem('accessToken');
        }
        set(initialState);
    },

    setError: (error: string | null) => {
        set({ error });
    },
}));

if (typeof window !== 'undefined') {
    window.addEventListener('osint:auth-expired', () => {
        useAuthStore.setState(initialState);
    });
}