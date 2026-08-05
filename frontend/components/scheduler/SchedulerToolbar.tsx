"use client";

/**
 * SchedulerToolbar — 排课日历顶部工具条
 * docs/design/components.md §2.1
 * 组别筛选 + 日/周/月切换 + 今日按钮 + 患者池开关
 */

import { CalendarDays, ChevronLeft, ChevronRight, PanelRightClose, PanelRightOpen } from "lucide-react";
import { WEEKDAY_LABELS } from "@/lib/format";
import type { CourseType } from "@/lib/types";

export type ViewMode = "day" | "week" | "month";

export interface DateRange {
  start: Date;
  end: Date;
}

export function SchedulerToolbar({
  groupFilter,
  onGroupChange,
  viewMode,
  onViewModeChange,
  dateRange,
  onPrev,
  onNext,
  onToday,
  poolCollapsed,
  onTogglePool,
}: {
  groupFilter: CourseType | "all";
  onGroupChange: (g: CourseType | "all") => void;
  viewMode: ViewMode;
  onViewModeChange: (v: ViewMode) => void;
  dateRange: DateRange;
  onPrev: () => void;
  onNext: () => void;
  onToday: () => void;
  poolCollapsed: boolean;
  onTogglePool: () => void;
}) {
  const rangeLabel = formatRange(dateRange, viewMode);

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-white border-b border-neutral-200">
      {/* 组别筛选 */}
      <div className="flex items-center gap-0.5 bg-neutral-100 rounded-md p-0.5">
        {(["all", "PT", "OT", "ST"] as const).map((g) => (
          <button
            key={g}
            onClick={() => onGroupChange(g)}
            className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
              groupFilter === g
                ? "bg-white text-primary-700 shadow-sm"
                : "text-neutral-500 hover:text-neutral-700"
            }`}
          >
            {g === "all" ? "全部" : g}
          </button>
        ))}
      </div>

      {/* 日期导航 */}
      <div className="flex items-center gap-1">
        <button
          onClick={onPrev}
          className="rounded p-1 text-neutral-500 hover:bg-neutral-100"
        >
          <ChevronLeft size={18} />
        </button>
        <span className="text-sm font-medium text-neutral-700 min-w-[140px] text-center tabular-nums">
          {rangeLabel}
        </span>
        <button
          onClick={onNext}
          className="rounded p-1 text-neutral-500 hover:bg-neutral-100"
        >
          <ChevronRight size={18} />
        </button>
      </div>

      {/* 今日按钮 */}
      <button
        onClick={onToday}
        className="flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-100"
      >
        <CalendarDays size={14} />
        今日
      </button>

      {/* 日/周/月切换 */}
      <div className="flex items-center gap-0.5 bg-neutral-100 rounded-md p-0.5 ml-auto">
        {(["day", "week", "month"] as ViewMode[]).map((v) => (
          <button
            key={v}
            onClick={() => onViewModeChange(v)}
            className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
              viewMode === v
                ? "bg-white text-primary-700 shadow-sm"
                : "text-neutral-500 hover:text-neutral-700"
            }`}
          >
            {v === "day" ? "日" : v === "week" ? "周" : "月"}
          </button>
        ))}
      </div>

      {/* 患者池开关 */}
      <button
        onClick={onTogglePool}
        className="rounded p-1.5 text-neutral-500 hover:bg-neutral-100"
        title={poolCollapsed ? "展开患者池" : "收起患者池"}
      >
        {poolCollapsed ? <PanelRightOpen size={18} /> : <PanelRightClose size={18} />}
      </button>
    </div>
  );
}

function formatRange(range: DateRange, mode: ViewMode): string {
  const { start, end } = range;
  if (mode === "day") {
    return `${start.getFullYear()}-${pad(start.getMonth() + 1)}-${pad(start.getDate())} ${WEEKDAY_LABELS[start.getDay()]}`;
  }
  if (mode === "week") {
    return `${pad(start.getMonth() + 1)}/${pad(start.getDate())} – ${pad(end.getMonth() + 1)}/${pad(end.getDate())}`;
  }
  // month
  return `${start.getFullYear()}年${start.getMonth() + 1}月`;
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}
