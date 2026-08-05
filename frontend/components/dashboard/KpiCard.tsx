/**
 * KpiCard — 看板 KPI 卡片
 * docs/design/components.md §5.1: display 字号大数字 + 标签 + 可选趋势箭头
 * docs/design/design-system.md §3: display 30px/700
 */

import { TrendingUp, TrendingDown, Minus, type LucideIcon } from "lucide-react";
import type { TrendDirection } from "@/lib/types";

const TREND_CONFIG: Record<
  TrendDirection,
  { icon: LucideIcon; className: string }
> = {
  up: { icon: TrendingUp, className: "text-success-500" },
  down: { icon: TrendingDown, className: "text-danger-500" },
  flat: { icon: Minus, className: "text-neutral-400" },
};

export function KpiCard({
  label,
  value,
  unit,
  trend,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  unit?: string;
  trend?: TrendDirection;
  icon?: LucideIcon;
}) {
  const trendCfg = trend ? TREND_CONFIG[trend] : null;
  const TrendIcon = trendCfg?.icon;

  return (
    <div className="rounded-lg bg-white border border-neutral-200 p-4 shadow-card flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-neutral-500">{label}</span>
        {Icon && <Icon size={18} className="text-neutral-400" />}
      </div>
      <div className="flex items-end gap-1">
        <span className="text-[30px] font-bold tabular-nums text-neutral-900 leading-none">
          {value}
        </span>
        {unit && (
          <span className="text-sm text-neutral-500 mb-1">{unit}</span>
        )}
        {TrendIcon && (
          <span className={`mb-1 ml-1 ${trendCfg!.className}`}>
            <TrendIcon size={16} />
          </span>
        )}
      </div>
    </div>
  );
}
