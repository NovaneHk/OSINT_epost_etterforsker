'use client';

import {
  Users,
  Play,
  Database,
  Download,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Wifi,
  WifiOff,
  FileDown,
  UserCheck,
  PhoneCall,
} from 'lucide-react';
import type { ActivityEvent, ActivityEventType } from '@/lib/types';
import { EmptyState } from '@/components/shared/empty-state';
import { formatRelative } from '@/lib/format';
import { cn } from '@/lib/utils';

const EVENT_ICONS: Record<ActivityEventType, React.ElementType> = {
  lead_found: Users,
  run_started: Play,
  run_completed: CheckCircle2,
  run_failed: XCircle,
  source_error: WifiOff,
  source_recovered: Wifi,
  export_ready: FileDown,
  lead_qualified: UserCheck,
  lead_contacted: PhoneCall,
};

const EVENT_COLORS: Record<ActivityEventType, string> = {
  lead_found: 'var(--nt-accent)',
  run_started: 'var(--nt-accent)',
  run_completed: 'var(--nt-success)',
  run_failed: 'var(--nt-danger)',
  source_error: 'var(--nt-danger)',
  source_recovered: 'var(--nt-success)',
  export_ready: 'var(--nt-ai)',
  lead_qualified: 'var(--nt-ai)',
  lead_contacted: 'var(--nt-warning)',
};

function ActivityIcon({ type }: { type: ActivityEventType }) {
  const Icon = EVENT_ICONS[type];
  const color = EVENT_COLORS[type];
  return (
    <div
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
      style={{ backgroundColor: `color-mix(in srgb, ${color} 15%, transparent)` }}
    >
      <Icon className="h-3.5 w-3.5" style={{ color }} aria-hidden="true" />
    </div>
  );
}

interface ActivityFeedProps {
  events: ActivityEvent[];
  /** max items to show; defaults to 10 */
  limit?: number;
}

export function ActivityFeed({ events, limit = 10 }: ActivityFeedProps) {
  const visible = events.slice(0, limit);

  return (
    <div className="rounded-lg border border-[var(--nt-border)] bg-[var(--nt-surface)]">
      <div className="border-b border-[var(--nt-border)] px-5 py-4">
        <h2 className="text-sm font-semibold text-[var(--nt-text-primary)]">
          Activity Feed
        </h2>
        <p className="text-xs text-[var(--nt-text-secondary)]">
          Recent system events
        </p>
      </div>

      {visible.length === 0 ? (
        <EmptyState
          icon={Database}
          title="No activity yet"
          description="System events will appear here as runs and leads are processed."
        />
      ) : (
        <ol className="divide-y divide-[var(--nt-border)]" aria-label="Activity events">
          {visible.map((event, idx) => (
            <li key={event.id} className="flex gap-3 px-5 py-3">
              {/* Timeline connector */}
              <div className="relative flex flex-col items-center">
                <ActivityIcon type={event.type} />
                {idx < visible.length - 1 && (
                  <div
                    className="mt-1 w-px flex-1 bg-[var(--nt-border)]"
                    aria-hidden="true"
                  />
                )}
              </div>

              {/* Content */}
              <div className="min-w-0 flex-1 pb-3">
                <p className="text-sm font-medium text-[var(--nt-text-primary)] leading-snug">
                  {event.title}
                </p>
                {event.description && (
                  <p className="mt-0.5 text-xs text-[var(--nt-text-secondary)]">
                    {event.description}
                  </p>
                )}
                <time
                  dateTime={event.timestamp}
                  className="mt-1 block text-[10px] text-[var(--nt-text-secondary)]"
                >
                  {formatRelative(event.timestamp)}
                </time>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
