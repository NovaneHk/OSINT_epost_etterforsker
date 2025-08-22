"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { config } from '@/lib/config';
import { authService } from '@/lib/auth/service';
import {
  User,
  AuthSession,
  AuthState,
  LoginCredentials,
  RegisterData,
  Permission,
  Role,
  ROLE_PERMISSIONS
} from '@/lib/auth/types';

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  updateProfile: (updates: Partial<User>) => Promise<void>;
  hasPermission: (permission: Permission) => boolean;
  hasRole: (role: Role) => boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    session: null,
    isLoading: true,
    isAuthenticated: false,
    error: null,
  });

  // Initialize auth state
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const session = authService.getSession();
        if (session) {
          // Validate session and get fresh user data
          await authService.ensureValidToken();
          const user = await authService.getProfile();

          setState({
            user,
            session: authService.getSession(),
            isLoading: false,
            isAuthenticated: true,
            error: null,
          });
        } else {
          setState(prev => ({
            ...prev,
            isLoading: false,
            isAuthenticated: false,
          }));
        }
      } catch (error) {
        console.error('Auth initialization failed:', error);
        setState({
          user: null,
          session: null,
          isLoading: false,
          isAuthenticated: false,
          error: error as any,
        });
      }
    };

    if (config.auth.enabled) {
      initializeAuth();
    } else {
      // Mock authenticated state for development
      setState({
        user: {
          id: 'dev-user',
          email: 'dev@example.com',
          name: 'Developer',
          role: 'admin',
          isVerified: true,
          createdAt: new Date().toISOString(),
          permissions: ROLE_PERMISSIONS.admin,
        },
        session: null,
        isLoading: false,
        isAuthenticated: true,
        error: null,
      });
    }
  }, []);

  // Login function
  const login = async (credentials: LoginCredentials) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const session = await authService.login(credentials);
      setState({
        user: session.user,
        session,
        isLoading: false,
        isAuthenticated: true,
        error: null,
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error as any,
      }));
      throw error;
    }
  };

  // Register function
  const register = async (data: RegisterData) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const session = await authService.register(data);
      setState({
        user: session.user,
        session,
        isLoading: false,
        isAuthenticated: true,
        error: null,
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error as any,
      }));
      throw error;
    }
  };

  // Logout function
  const logout = async () => {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      await authService.logout();
      setState({
        user: null,
        session: null,
        isLoading: false,
        isAuthenticated: false,
        error: null,
      });
    } catch (error) {
      console.error('Logout error:', error);
      // Clear state anyway
      setState({
        user: null,
        session: null,
        isLoading: false,
        isAuthenticated: false,
        error: null,
      });
    }
  };

  // Refresh token
  const refreshToken = async () => {
    try {
      const session = await authService.refreshToken();
      setState(prev => ({
        ...prev,
        session,
        user: session.user,
      }));
    } catch (error) {
      console.error('Token refresh failed:', error);
      await logout();
    }
  };

  // Update profile
  const updateProfile = async (updates: Partial<User>) => {
    try {
      const updatedUser = await authService.updateProfile(updates);
      setState(prev => ({
        ...prev,
        user: updatedUser,
      }));
    } catch (error) {
      console.error('Profile update failed:', error);
      throw error;
    }
  };

  // Check if user has specific permission
  const hasPermission = (permission: Permission): boolean => {
    if (!state.user) return false;
    return state.user.permissions.includes(permission);
  };

  // Check if user has specific role
  const hasRole = (role: Role): boolean => {
    if (!state.user) return false;
    return state.user.role === role;
  };

  // Context value
  const contextValue: AuthContextType = {
    ...state,
    login,
    register,
    logout,
    refreshToken,
    updateProfile,
    hasPermission,
    hasRole,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// Hook to use auth context
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Hook for current user
export function useUser(): User | null {
  const { user } = useAuth();
  return user;
}

// Hook for authentication status
export function useAuthStatus() {
  const { isAuthenticated, isLoading } = useAuth();
  return { isAuthenticated, isLoading };
}

// Hook for permissions
export function usePermissions() {
  const { hasPermission, hasRole, user } = useAuth();
  return { hasPermission, hasRole, permissions: user?.permissions || [] };
}

// Higher-order component for protected routes
export function withAuth<T extends object>(
  Component: React.ComponentType<T>,
  requiredPermission?: Permission
) {
  const WrappedComponent = (props: T) => {
    const { isAuthenticated, isLoading, hasPermission } = useAuth();

    if (isLoading) {
      return <div>Loading...</div>; // Or your loading component
    }

    if (!isAuthenticated) {
      // Redirect to login or show login form
      return <div>Please log in</div>; // Or your login component
    }

    if (requiredPermission && !hasPermission(requiredPermission)) {
      return <div>Access denied</div>; // Or your access denied component
    }

    return <Component {...props} />;
  };

  WrappedComponent.displayName = `withAuth(${Component.displayName || Component.name})`;

  return WrappedComponent;
}