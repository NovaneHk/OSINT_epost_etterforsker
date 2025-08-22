"use client";

import { useCallback } from 'react';
import { useToast } from '@/components/ui/use-toast';

export interface ErrorInfo {
  error: Error;
  errorInfo?: any;
  context?: string;
}

export function useErrorHandler() {
  const { toast } = useToast();

  const handleError = useCallback((errorInfo: ErrorInfo) => {
    const { error, context } = errorInfo;

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error(`Error in ${context || 'unknown context'}:`, error);
    }

    // Send to analytics/monitoring service
    if (typeof window !== 'undefined' && window.gtag) {
      window.gtag('event', 'exception', {
        description: error.toString(),
        fatal: false,
        context: context || 'unknown',
      });
    }

    // Show user-friendly error message
    const message = getErrorMessage(error, context);
    toast({
      title: "Error",
      description: message,
      variant: "destructive",
    });

    // Send to error tracking service (e.g., Sentry)
    // if (window.Sentry) {
    //   window.Sentry.captureException(error, {
    //     tags: { context },
    //     extra: errorInfo,
    //   });
    // }
  }, [toast]);

  const handleApiError = useCallback((error: any, endpoint?: string) => {
    let message = 'An unexpected error occurred';

    if (error?.response?.status) {
      switch (error.response.status) {
        case 400:
          message = 'Invalid request. Please check your input.';
          break;
        case 401:
          message = 'You are not authorized. Please log in again.';
          break;
        case 403:
          message = 'You do not have permission to perform this action.';
          break;
        case 404:
          message = 'The requested resource was not found.';
          break;
        case 429:
          message = 'Too many requests. Please try again later.';
          break;
        case 500:
          message = 'Server error. Please try again later.';
          break;
        case 503:
          message = 'Service unavailable. Please try again later.';
          break;
        default:
          message = `Error ${error.response.status}: ${error.response.statusText || 'Unknown error'}`;
      }
    } else if (error?.message) {
      message = error.message;
    }

    handleError({
      error: error instanceof Error ? error : new Error(message),
      context: endpoint ? `API: ${endpoint}` : 'API',
    });
  }, [handleError]);

  const handleAsyncError = useCallback(async (asyncFn: () => Promise<any>, context?: string) => {
    try {
      return await asyncFn();
    } catch (error) {
      handleError({
        error: error instanceof Error ? error : new Error(String(error)),
        context,
      });
      throw error; // Re-throw to allow caller to handle if needed
    }
  }, [handleError]);

  return {
    handleError,
    handleApiError,
    handleAsyncError,
  };
}

function getErrorMessage(error: Error, context?: string): string {
  // Network errors
  if (error.message.includes('fetch')) {
    return 'Network error. Please check your connection and try again.';
  }

  // Validation errors
  if (error.message.includes('validation') || error.message.includes('invalid')) {
    return 'Please check your input and try again.';
  }

  // Permission errors
  if (error.message.includes('permission') || error.message.includes('unauthorized')) {
    return 'You do not have permission to perform this action.';
  }

  // API-specific errors
  if (context?.includes('API')) {
    return 'There was a problem communicating with the server. Please try again.';
  }

  // Generic error message
  return 'An unexpected error occurred. Please try again.';
}