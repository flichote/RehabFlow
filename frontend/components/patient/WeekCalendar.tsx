"use client";

/**
 * WeekCalendar — 本周小周历
 * docs/design/components.md §4.1:
 * - 7 天课程分布
 * - 点击某天展开当日详细时间表
 */

import { useState } from "react";
import type { WeekCalendarDay } from "@/lib/types";

export function WeekCalendar({
  days,
}: {
  days: WeekCalendarDay[];
}) {
  const [selectedIdx, setSelectedIdx] = useState(days.length - 1); // 默认选今天
  const selected = days[selectedIdx];

  return (
    <div className="rounded-lg bg-white border border-neutral-200 shadow-card p-4">
      <h3 className="text-base font-semibold text-neutral-900 mb-4">本周课历</h3>
      <div className="grid grid-cols-7 gap-1.5">
        {days.map((day, idx) => {
          const isActive = idx === selectedIdx;
          return (
            <button
              key={day.date}
              onClick={() => setSelectedIdx(idx)}
              className={`flex flex-col items-center gap-1 rounded-md py-2 transition-colors ${
                isActive
                  ? "bg-primary-600 text-white"
                  : "bg-neutral-50 text-neutral-700 hover:bg-primary-50"
              }`}
            >
              <span className={`text-[11px] ${isActive ? "text-primary-100" : "text-neutral-400"}`}>
                {day.weekday}
              </span>
              <span className="text-sm font-bold tabular-nums">
                {day.courses}
              </span>
              <span className={`text-[10px] ${isActive ? "text-primary-100" : "text-neutral-400"}`}>
                节
              </span>
            </button>
          );
        })}
      </div>
      {selected && (
        <div className="mt-3 pt-3 border-t border-neutral-100 text-center">
          <p className="text-xs text-neutral-500">
            {selected.date}（{selected.weekday}）· {selected.courses} 节课程
          </p>
        </div>
      )}
    </div>
  );
}
