"use client";

/**
 * PlanTimeline — 课程计划时间轴
 * docs/design/components.md §4.1:
 * - 课程记录时间倒序
 * - 圆点：绿=已完成 / 灰=待执行 / 红=缺席
 */

import type { PlanTimelineItem } from "@/lib/types";
import { formatTime } from "@/lib/format";
import { CourseTypeBadge } from "@/components/common/CourseTypeBadge";

const DOT_CONFIG: Record<string, string> = {
  completed: "bg-success-500",
  scheduled: "bg-neutral-400",
  reminded: "bg-neutral-400",
  absent: "bg-danger-500",
  ongoing: "bg-success-500",
  abnormal: "bg-danger-500",
};

export function PlanTimeline({
  items,
}: {
  items: PlanTimelineItem[];
}) {
  // 时间倒序
  const sorted = [...items].sort(
    (a, b) => new Date(b.start_at).getTime() - new Date(a.start_at).getTime()
  );

  if (sorted.length === 0) {
    return (
      <div className="rounded-lg bg-white border border-neutral-200 p-6 text-center">
        <p className="text-sm text-neutral-400">暂无课程记录</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-white border border-neutral-200 shadow-card p-4">
      <h3 className="text-base font-semibold text-neutral-900 mb-4">
        课程时间轴
      </h3>
      <div className="relative">
        {/* 竖线 */}
        <div className="absolute left-[5px] top-2 bottom-2 w-px bg-neutral-200" />
        <div className="space-y-4">
          {sorted.map((item) => (
            <div key={item.course_id} className="relative flex items-start gap-3 pl-6">
              {/* 圆点 */}
              <span
                className={`absolute left-0 top-1.5 w-2.5 h-2.5 rounded-full ring-2 ring-white ${DOT_CONFIG[item.status] ?? "bg-neutral-400"}`}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-medium text-neutral-500 tabular-nums">
                    {formatTime(item.start_at)}–{formatTime(item.end_at)}
                  </span>
                  <CourseTypeBadge type={item.type} />
                </div>
                <p className="text-sm text-neutral-700 mt-0.5">
                  {item.therapist_name} · {item.room_name}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
