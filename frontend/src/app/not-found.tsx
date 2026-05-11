import Link from 'next/link';
import { Search } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 px-4 text-center">
      <div
        className="flex h-14 w-14 items-center justify-center rounded-full"
        style={{ backgroundColor: 'var(--nt-surface-elevated)' }}
      >
        <Search
          className="h-7 w-7"
          style={{ color: 'var(--nt-text-secondary)' }}
          aria-hidden="true"
        />
      </div>

      <div className="space-y-2">
        <h2 className="text-lg font-semibold" style={{ color: 'var(--nt-text-primary)' }}>
          Page not found
        </h2>
        <p className="max-w-sm text-sm" style={{ color: 'var(--nt-text-secondary)' }}>
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
      </div>

      <Link
        href="/dashboard"
        className="inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2"
        style={{
          backgroundColor: 'var(--nt-surface-elevated)',
          color: 'var(--nt-text-primary)',
          border: '1px solid var(--nt-border)',
        }}
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
