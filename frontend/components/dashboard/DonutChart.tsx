"use client";

/**
 * DonutChart — 患者分布环形图
 * docs/design/components.md §5.1: 病房/PT/OT/ST 人数占比
 * 图表配色引用 token: pt/ot/st/neutral
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

/** token 色值映射（引用 design-system.md §2.2/§2.4） */
const COLORS: Record<string, string> = {
  pt: "#3B82F6",
  ot: "#22C55E",
  st: "#F97316",
  neutral: "#94A3B8",
};

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
                <Cell key={idx} fill={COLORS[entry.color] ?? COLORS.neutral} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name) => [
                `${value} 人`,
                name,
              ]}
              contentStyle={{
                borderRadius: 8,
                border: "1px solid #E2E8F0",
                fontSize: 13,
              }}
            />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 12, color: "#64748B" }}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
