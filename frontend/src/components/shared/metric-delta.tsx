import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDelta } from '@/lib/format';

interface MetricDeltaProps {
  delta: number;
  /** Show as absolute value instead of formatted percentage */
  absolute?: boolean;
  className?: string;
}

export function MetricDelta({ delta, absolute, className }: MetricDeltaProps) {
  const isPositive = delta > 0;
  const isNeutral = delta === 0;

  const label = absolute
    ? `${isPositive ? '+' : ''}${delta.toFixed(0)}`
    : formatDelta(delta);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 text-xs font-medium',
        isNeutral && 'text-[var(--nt-text-secondary)]',
        isPositive && 'text-[var(--nt-success)]',
        !isPositive && !isNeutral && 'text-[var(--nt-danger)]',
        className
      )}
      aria-label={`${label} compared to previous period`}
    >
      {isNeutral ? (
        <Minus className="h-3 w-3" aria-hidden="true" />
      ) : isPositive ? (
        <TrendingUp className="h-3 w-3" aria-hidden="true" />
      ) : (
        <TrendingDown className="h-3 w-3" aria-hidden="true" />
      )}
      {label}
    </span>
  );
}
