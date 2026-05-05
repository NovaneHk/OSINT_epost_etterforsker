export interface User {
    id: string;
    username: string;
    email: string;
    token: string;
    role: 'admin' | 'manager' | 'analyst' | 'viewer';
}

export interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
}

export interface AuthStore extends AuthState {
    initialize: () => Promise<void>;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
    setError: (error: string | null) => void;
}