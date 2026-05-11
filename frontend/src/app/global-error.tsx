'use client';

// global-error.tsx catches errors thrown by the root layout itself.
// It MUST import its own styles because layout.tsx will NOT render.
import './globals.css';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  return (
    <html lang="nb" className="dark">
      <body
        style={{
          margin: 0,
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#0F1117',
          color: '#F0F6FC',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1.5rem',
            padding: '2rem',
            textAlign: 'center',
            maxWidth: '28rem',
          }}
        >
          <div
            style={{
              display: 'flex',
              height: '3.5rem',
              width: '3.5rem',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '9999px',
              backgroundColor: 'rgba(248,81,73,0.12)',
            }}
          >
            <AlertTriangle
              style={{ height: '1.75rem', width: '1.75rem', color: '#F85149' }}
              aria-hidden="true"
            />
          </div>

          <div>
            <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.5rem' }}>
              Application error
            </h2>
            <p style={{ fontSize: '0.875rem', color: '#8B949E', lineHeight: 1.6 }}>
              {process.env.NODE_ENV === 'development'
                ? error.message || 'A critical error occurred in the application.'
                : 'A critical error occurred. Please refresh the page.'}
            </p>
          </div>

          <button
            onClick={reset}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              borderRadius: '0.375rem',
              padding: '0.5rem 1rem',
              fontSize: '0.875rem',
              fontWeight: 500,
              backgroundColor: '#0A84FF',
              color: '#F0F6FC',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            <RefreshCw style={{ height: '1rem', width: '1rem' }} aria-hidden="true" />
            Reload
          </button>
        </div>
      </body>
    </html>
  );
}
