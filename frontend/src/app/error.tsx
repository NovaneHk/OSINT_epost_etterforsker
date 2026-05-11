'use client';

import { useEffect } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.error('[Nova Trace] Page error:', error);
    }
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 px-4 text-center">
      <div
        className="flex h-14 w-14 items-center justify-center rounded-full"
        style={{ backgroundColor: 'color-mix(in srgb, var(--nt-danger) 12%, transparent)' }}
      >
        <AlertTriangle
          className="h-7 w-7"
          style={{ color: 'var(--nt-danger)' }}
          aria-hidden="true"
        />
      </div>

      <div className="space-y-2">
        <h2 className="text-lg font-semibold" style={{ color: 'var(--nt-text-primary)' }}>
          Something went wrong
        </h2>
        <p className="max-w-sm text-sm" style={{ color: 'var(--nt-text-secondary)' }}>
          {process.env.NODE_ENV === 'development'
            ? error.message || 'An unexpected error occurred.'
            : 'An unexpected error occurred. Please try again.'}
        </p>
        {error.digest && (
          <p className="text-xs font-mono" style={{ color: 'var(--nt-text-secondary)' }}>
            Digest: {error.digest}
          </p>
        )}
      </div>

      <button
        onClick={reset}
        className="inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2"
        style={{
          backgroundColor: 'var(--nt-accent)',
          color: 'var(--nt-text-primary)',
        }}
      >
        <RefreshCw className="h-4 w-4" aria-hidden="true" />
        Try again
      </button>
    </div>
  );
}
