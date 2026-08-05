"use client";

/**
 * TodayOverviewCard — 今日概览卡
 * docs/design/components.md §3.1
 * 今日总课时 / 已完成 / 剩余；大数字 tabular-nums
 */

import { Clock, CheckCircle, Hourglass } from "lucide-react";
import type { TodayOverview } from "@/lib/types";

export function TodayOverviewCard({ overview }: { overview: TodayOverview }) {
  const items = [
    {
      label: "今日总课时",
      value: formatMinutes(overview.total_minutes),
      sub: `${overview.total_courses} 节`,
      icon: <Clock size={16} />,
      color: "text-primary-600",
    },
    {
      label: "已完成",
      value: formatMinutes(overview.completed_minutes),
      sub: `${overview.completed_courses} 节`,
      icon: <CheckCircle size={16} />,
      color: "text-success-500",
    },
    {
      label: "剩余",
      value: formatMinutes(overview.remaining_minutes),
      sub: `${overview.total_courses - overview.completed_courses} 节`,
      icon: <Hourglass size={16} />,
      color: "text-warning-500",
    },
  ];

  return (
    <div className="bg-white rounded-lg border border-neutral-200 shadow-card p-4">
      <div className="grid grid-cols-3 gap-4">
        {items.map((item, i) => (
          <div key={i} className="text-center">
            <div className={`flex items-center justify-center gap-1 mb-1 ${item.color}`}>
              {item.icon}
              <span className="text-xs text-neutral-500">{item.label}</span>
            </div>
            <div className="text-2xl font-bold text-neutral-900 tabular-nums">
              {item.value}
            </div>
            <div className="text-xs text-neutral-400 mt-0.5 tabular-nums">
              {item.sub}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatMinutes(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  if (h === 0) return `${m}分`;
  if (m === 0) return `${h}时`;
  return `${h}时${m}分`;
}
