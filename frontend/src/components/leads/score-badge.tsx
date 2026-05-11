import { cn } from '@/lib/utils';
import type { ScoreBand } from '@/lib/types';
import { SCORE_BAND_TEXT, SCORE_BAND_BG } from '@/lib/constants';

interface ScoreBadgeProps {
  score: number;
  band: ScoreBand;
  className?: string;
}

export function ScoreBadge({ score, band, className }: ScoreBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded px-2 py-0.5 text-xs font-semibold tabular-nums',
        SCORE_BAND_BG[band],
        SCORE_BAND_TEXT[band],
        className
      )}
      aria-label={`Score: ${score}`}
    >
      {score}
    </span>
  );
}
