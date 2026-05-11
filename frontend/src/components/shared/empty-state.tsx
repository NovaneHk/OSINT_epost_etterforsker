import { type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 py-12 text-center',
        className
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--nt-surface-elevated)]">
        <Icon
          className="h-6 w-6 text-[var(--nt-text-secondary)]"
          aria-hidden="true"
        />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-[var(--nt-text-primary)]">
          {title}
        </p>
        {description && (
          <p className="text-xs text-[var(--nt-text-secondary)]">
            {description}
          </p>
        )}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
