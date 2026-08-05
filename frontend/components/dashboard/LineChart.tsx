"use client";

/**
 * LineChart — 近7天课程总量趋势
 * docs/design/components.md §5.1: 底部 col-span-12
 * 图表配色引用 token: primary (via lib/chart-tokens.ts)
 */

import {
  LineChart as RLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { CourseTrend } from "@/lib/types";
import { ChartCard } from "./ChartCard";
import {
  CHART_COLORS,
  CHART_TICK_STYLE,
  CHART_TOOLTIP_STYLE,
} from "@/lib/chart-tokens";

export function LineChart({
  data,
  isLoading = false,
}: {
  data: CourseTrend[];
  isLoading?: boolean;
}) {
  return (
    <ChartCard title="近 7 天课程总量趋势" refreshLabel="每日" className="col-span-12">
      {isLoading ? (
        <div className="h-56 flex items-center justify-center text-sm text-neutral-400">
          加载中…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <RLineChart data={data} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.neutral200} />
            <XAxis
              dataKey="label"
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
              formatter={(value) => [`${value} 节`, "课程总量"]}
              contentStyle={CHART_TOOLTIP_STYLE}
            />
            <Line
              type="monotone"
              dataKey="total"
              stroke={CHART_COLORS.primary}
              strokeWidth={2}
              dot={{ r: 4, fill: CHART_COLORS.primary }}
              activeDot={{ r: 6 }}
            />
          </RLineChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
