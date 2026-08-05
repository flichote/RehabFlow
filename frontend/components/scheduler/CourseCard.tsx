"use client";

/**
 * CourseCard — 课程卡片（排课网格内）
 * docs/design/components.md §6 通用组件
 * 患者名 + 类型徽章 + 时长；颜色=类型色浅底
 */

import { Clock, AlertTriangle } from "lucide-react";
import { CourseTypeBadge } from "@/components/common/CourseTypeBadge";
import { formatTime } from "@/lib/format";
import type { Course } from "@/lib/types";

const TYPE_BG: Record<Course["course_type"], string> = {
  PT: "bg-pt-50 border-l-pt-500",
  OT: "bg-ot-50 border-l-ot-500",
  ST: "bg-st-50 border-l-st-500",
};

export function CourseCard({
  course,
  onClick,
  onDragStart,
  onDragEnd,
  dragging,
  dimmed = false,
}: {
  course: Course;
  onClick?: () => void;
  onDragStart?: (e: React.DragEvent) => void;
  onDragEnd?: (e: React.DragEvent) => void;
  dragging?: boolean;
  dimmed?: boolean;
}) {
  const isAbnormal = course.status === "abnormal";

  return (
    <div
      draggable={!!onDragStart}
      onClick={onClick}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className={[
        "cursor-pointer rounded-md border border-neutral-200 border-l-2 px-1.5 py-1 text-xs shadow-card transition-all",
        TYPE_BG[course.course_type],
        dragging ? "opacity-50 scale-105 shadow-pop" : "",
        dimmed ? "opacity-40 grayscale" : "",
        isAbnormal ? "ring-1 ring-danger-500" : "",
      ].join(" ")}
    >
      <div className="flex items-center gap-1 mb-0.5">
        <CourseTypeBadge type={course.course_type} />
        {isAbnormal && (
          <AlertTriangle size={12} className="text-danger-500 ml-auto" />
        )}
      </div>
      <div className="font-medium text-neutral-900 truncate">
        {course.patient_name}
      </div>
      <div className="flex items-center gap-0.5 text-neutral-500 tabular-nums">
        <Clock size={10} />
        <span>
          {formatTime(course.start_at)}–{formatTime(course.end_at)}
        </span>
      </div>
    </div>
  );
}
