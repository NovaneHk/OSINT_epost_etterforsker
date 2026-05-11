import { cn } from '@/lib/utils';

interface SkeletonBlockProps {
  className?: string;
}

export function SkeletonBlock({ className }: SkeletonBlockProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-[var(--nt-surface-elevated)]',
        className
      )}
      aria-hidden="true"
    />
  );
}
