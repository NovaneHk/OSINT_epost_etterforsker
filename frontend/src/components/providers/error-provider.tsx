"use client";

import React, { createContext, useContext, ReactNode } from 'react';
import { ErrorBoundary } from '@/components/error/error-boundary';
import { useErrorHandler } from '@/hooks/use-error-handler';

interface ErrorContextType {
  handleError: (error: Error, context?: string) => void;
  handleApiError: (error: any, endpoint?: string) => void;
  handleAsyncError: (asyncFn: () => Promise<any>, context?: string) => Promise<any>;
}

const ErrorContext = createContext<ErrorContextType | undefined>(undefined);

interface ErrorProviderProps {
  children: ReactNode;
}

export function ErrorProvider({ children }: ErrorProviderProps) {
  const { handleError, handleApiError, handleAsyncError } = useErrorHandler();

  const contextValue: ErrorContextType = {
    handleError: (error: Error, context?: string) => {
      handleError({ error, context });
    },
    handleApiError,
    handleAsyncError,
  };

  return (
    <ErrorContext.Provider value={contextValue}>
      <ErrorBoundary>
        {children}
      </ErrorBoundary>
    </ErrorContext.Provider>
  );
}

export function useError() {
  const context = useContext(ErrorContext);
  if (context === undefined) {
    throw new Error('useError must be used within an ErrorProvider');
  }
  return context;
}

// Higher-order component for wrapping pages with error handling
export function withErrorHandling<T extends object>(
  Component: React.ComponentType<T>
) {
  const WrappedComponent = (props: T) => {
    const { handleError } = useError();

    React.useEffect(() => {
      // Global unhandled promise rejection handler
      const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
        console.error('Unhandled promise rejection:', event.reason);
        handleError(
          event.reason instanceof Error ? event.reason : new Error(String(event.reason)),
          'Unhandled Promise Rejection'
        );
      };

      // Global error handler
      const handleGlobalError = (event: ErrorEvent) => {
        console.error('Global error:', event.error);
        handleError(
          event.error instanceof Error ? event.error : new Error(event.message),
          'Global Error'
        );
      };

      window.addEventListener('unhandledrejection', handleUnhandledRejection);
      window.addEventListener('error', handleGlobalError);

      return () => {
        window.removeEventListener('unhandledrejection', handleUnhandledRejection);
        window.removeEventListener('error', handleGlobalError);
      };
    }, [handleError]);

    return <Component {...props} />;
  };

  WrappedComponent.displayName = `withErrorHandling(${Component.displayName || Component.name})`;

  return WrappedComponent;
}