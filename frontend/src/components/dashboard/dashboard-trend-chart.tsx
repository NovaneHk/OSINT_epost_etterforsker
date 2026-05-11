'use client';

import { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { TrendDataPoint } from '@/lib/types';
import { formatDateShort } from '@/lib/format';

interface DashboardTrendChartProps {
  data: TrendDataPoint[];
}

export function DashboardTrendChart({ data }: DashboardTrendChartProps) {
  const chartData = useMemo(
    () =>
      data.map((d) => ({
        ...d,
        label: formatDateShort(d.date),
      })),
    [data]
  );

  return (
    <div className="rounded-lg border border-[var(--nt-border)] bg-[var(--nt-surface)] p-5">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[var(--nt-text-primary)]">
            Lead Discovery
          </h2>
          <p className="text-xs text-[var(--nt-text-secondary)]">
            Leads &amp; searches over 30 days
          </p>
        </div>
      </div>

      <div className="h-56" aria-label="Lead discovery trend chart">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
          >
            <defs>
              <linearGradient id="grad-leads" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--nt-accent)" stopOpacity={0.25} />
                <stop offset="95%" stopColor="var(--nt-accent)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="grad-searches" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--nt-ai)" stopOpacity={0.2} />
                <stop offset="95%" stopColor="var(--nt-ai)" stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--nt-border)"
              vertical={false}
            />

            <XAxis
              dataKey="label"
              tick={{ fill: 'var(--nt-text-secondary)', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              interval={4}
            />

            <YAxis
              tick={{ fill: 'var(--nt-text-secondary)', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={30}
            />

            <Tooltip
              contentStyle={{
                background: 'var(--nt-surface-elevated)',
                border: '1px solid var(--nt-border)',
                borderRadius: '6px',
                color: 'var(--nt-text-primary)',
                fontSize: '12px',
              }}
              labelStyle={{ color: 'var(--nt-text-secondary)', marginBottom: 4 }}
              cursor={{ stroke: 'var(--nt-border)', strokeWidth: 1 }}
            />

            <Legend
              verticalAlign="top"
              align="right"
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 11, color: 'var(--nt-text-secondary)', paddingBottom: 8 }}
            />

            <Area
              type="monotone"
              dataKey="leads"
              name="Leads"
              stroke="var(--nt-accent)"
              strokeWidth={1.5}
              fill="url(#grad-leads)"
              dot={false}
            />

            <Area
              type="monotone"
              dataKey="searches"
              name="Searches"
              stroke="var(--nt-ai)"
              strokeWidth={1.5}
              fill="url(#grad-searches)"
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
