"use client";

/**
 * DonutChart — 患者分布环形图
 * docs/design/components.md §5.1: 病房/PT/OT/ST 人数占比
 * 图表配色引用 token: pt/ot/st/neutral (via lib/chart-tokens.ts)
 */

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import type { PatientDistribution } from "@/lib/types";
import { ChartCard } from "./ChartCard";
import {
  DISTRIBUTION_COLORS,
  CHART_TOOLTIP_STYLE,
  CHART_LEGEND_STYLE,
} from "@/lib/chart-tokens";

export function DonutChart({
  data,
  isLoading = false,
}: {
  data: PatientDistribution[];
  isLoading?: boolean;
}) {
  return (
    <ChartCard title="患者分布" refreshLabel="实时">
      {isLoading ? (
        <div className="h-48 flex items-center justify-center text-sm text-neutral-400">
          加载中…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="label"
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={2}
            >
              {data.map((entry, idx) => (
                <Cell key={idx} fill={DISTRIBUTION_COLORS[entry.color] ?? DISTRIBUTION_COLORS.neutral} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name) => [
                `${value} 人`,
                name,
              ]}
              contentStyle={CHART_TOOLTIP_STYLE}
            />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={CHART_LEGEND_STYLE}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
