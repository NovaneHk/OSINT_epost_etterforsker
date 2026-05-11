'use client';

import { useMemo } from 'react';
import { type LucideIcon } from 'lucide-react';
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { cn } from '@/lib/utils';
import { MetricDelta } from '@/components/shared/metric-delta';

interface KpiCardProps {
  label: string;
  value: string;
  delta?: number;
  icon: LucideIcon;
  sparklineData?: number[];
  accentColor?: string;
  className?: string;
}

export function KpiCard({
  label,
  value,
  delta,
  icon: Icon,
  sparklineData,
  accentColor = 'var(--nt-accent)',
  className,
}: KpiCardProps) {
  const chartData = useMemo(
    () => (sparklineData ?? []).map((v) => ({ v })),
    [sparklineData]
  );

  return (
    <div
      className={cn(
        'relative flex flex-col gap-3 overflow-hidden rounded-lg border border-[var(--nt-border)] bg-[var(--nt-surface)] p-5',
        className
      )}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--nt-text-secondary)]">
          {label}
        </span>
        <div
          className="flex h-8 w-8 items-center justify-center rounded-md"
          style={{ backgroundColor: `color-mix(in srgb, ${accentColor} 15%, transparent)` }}
        >
          <Icon
            className="h-4 w-4"
            style={{ color: accentColor }}
            aria-hidden="true"
          />
        </div>
      </div>

      {/* Value + delta */}
      <div className="flex items-end justify-between gap-2">
        <div className="flex flex-col gap-1">
          <span className="text-3xl font-bold leading-none tracking-tight text-[var(--nt-text-primary)]">
            {value}
          </span>
          {delta !== undefined && (
            <span className="text-[11px] text-[var(--nt-text-secondary)]">
              vs last period{' '}
              <MetricDelta delta={delta} />
            </span>
          )}
        </div>

        {/* Sparkline */}
        {chartData.length > 1 && (
          <div className="h-14 w-28 shrink-0" aria-hidden="true">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id={`spark-${label}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={accentColor} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={accentColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Tooltip
                  contentStyle={{
                    background: 'var(--nt-surface-elevated)',
                    border: '1px solid var(--nt-border)',
                    borderRadius: '6px',
                    color: 'var(--nt-text-primary)',
                    fontSize: '11px',
                    padding: '4px 8px',
                  }}
                  itemStyle={{ color: accentColor }}
                  cursor={false}
                  formatter={(v: number) => [v, label]}
                />
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke={accentColor}
                  strokeWidth={1.5}
                  fill={`url(#spark-${label})`}
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
