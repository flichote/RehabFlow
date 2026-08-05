"use client";

/**
 * BarChart — 治疗师今日课时柱状图
 * docs/design/components.md §5.1: 横轴康复师姓名
 * 图表配色引用 token: primary (via lib/chart-tokens.ts)
 */

import {
  BarChart as RBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TherapistWorkload } from "@/lib/types";
import { ChartCard } from "./ChartCard";
import {
  CHART_COLORS,
  CHART_TICK_STYLE,
  CHART_TOOLTIP_STYLE,
} from "@/lib/chart-tokens";

export function BarChart({
  data,
  isLoading = false,
}: {
  data: TherapistWorkload[];
  isLoading?: boolean;
}) {
  return (
    <ChartCard title="治疗师今日课时" refreshLabel="30min">
      {isLoading ? (
        <div className="h-48 flex items-center justify-center text-sm text-neutral-400">
          加载中…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <RBarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.neutral200} vertical={false} />
            <XAxis
              dataKey="therapist_name"
              tick={CHART_TICK_STYLE}
              axisLine={{ stroke: CHART_COLORS.neutral200 }}
              tickLine={false}
            />
            <YAxis
              tick={CHART_TICK_STYLE}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              formatter={(value) => [`${value} 分钟`, "课时"]}
              contentStyle={CHART_TOOLTIP_STYLE}
            />
            <Bar
              dataKey="total_minutes"
              fill={CHART_COLORS.primary}
              radius={[4, 4, 0, 0]}
              maxBarSize={48}
            />
          </RBarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
