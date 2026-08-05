"use client";

/**
 * ScheduleItem — 课表时间线条目
 * docs/design/components.md §3.1 ScheduleItem
 * 时间段 + 患者名 + 类型徽章 + 治疗室 + 开始/结束上课 + 铃铛提醒
 */

import { useState } from "react";
import { Bell, Play, Square, FileText, MapPin } from "lucide-react";
import { CourseTypeBadge } from "@/components/common/CourseTypeBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { formatTime } from "@/lib/format";
import type { Course } from "@/lib/types";

export function ScheduleItem({
  course,
  onStart,
  onFinish,
  onRemind,
}: {
  course: Course;
  onStart?: (id: string) => void;
  onFinish?: (id: string) => void;
  onRemind?: (id: string) => void;
}) {
  const [loading, setLoading] = useState(false);

  const isOngoing = course.status === "ongoing";
  const isCompleted = course.status === "completed";
  const isPast = ["completed", "absent", "abnormal"].includes(course.status);

  async function handleAction(fn: ((id: string) => void) | undefined) {
    if (!fn) return;
    setLoading(true);
    try {
      fn(course.id);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className={[
        "flex items-center gap-3 rounded-md border bg-white px-3 py-2.5 shadow-card transition-all",
        isOngoing
          ? "ring-2 ring-primary-500 animate-pulse border-primary-200"
          : "border-neutral-200",
        isPast && !isOngoing ? "opacity-60" : "",
      ].join(" ")}
    >
      {/* 时间段 */}
      <div className="flex flex-col items-center min-w-[64px]">
        <span className="text-sm font-medium text-neutral-900 tabular-nums">
          {formatTime(course.start_at)}
        </span>
        <span className="text-[10px] text-neutral-400 tabular-nums">|</span>
        <span className="text-xs text-neutral-500 tabular-nums">
          {formatTime(course.end_at)}
        </span>
      </div>

      {/* 分隔线 */}
      <div className={`w-1 h-10 rounded-full ${
        course.course_type === "PT" ? "bg-pt-500" :
        course.course_type === "OT" ? "bg-ot-500" : "bg-st-500"
      }`} />

      {/* 患者信息 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-medium text-neutral-900 truncate">
            {course.patient_name}
          </span>
          <CourseTypeBadge type={course.course_type} />
          <StatusBadge status={course.status} />
        </div>
        <div className="flex items-center gap-1 text-xs text-neutral-400 mt-0.5">
          <MapPin size={11} />
          {course.room_name}
          {course.actual_start_at && course.actual_end_at && (
            <span className="ml-2 tabular-nums">
              实际：{formatTime(course.actual_start_at)}–{formatTime(course.actual_end_at)}
            </span>
          )}
        </div>
      </div>

      {/* 操作区 */}
      <div className="flex items-center gap-1.5 shrink-0">
        {/* 铃铛提醒 */}
        {!isPast && onRemind && (
          <button
            onClick={() => onRemind(course.id)}
            className="rounded-md p-1.5 text-neutral-400 hover:text-primary-600 hover:bg-primary-50 transition-colors"
            title="一键提醒"
          >
            <Bell size={16} />
          </button>
        )}

        {/* 填写记录（已完成才显示入口） */}
        {isCompleted && (
          <button
            className="flex items-center gap-1 rounded-md px-2 py-1.5 text-xs text-neutral-500 hover:bg-neutral-100 transition-colors"
            title="填写治疗记录"
          >
            <FileText size={14} />
            记录
          </button>
        )}

        {/* 开始/结束上课 */}
        {!isPast && !isOngoing && onStart && (
          <button
            onClick={() => handleAction(onStart)}
            disabled={loading}
            className="flex items-center gap-1 rounded-md bg-primary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            <Play size={14} />
            开始上课
          </button>
        )}

        {isOngoing && onFinish && (
          <button
            onClick={() => handleAction(onFinish)}
            disabled={loading}
            className="flex items-center gap-1 rounded-md bg-primary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            <Square size={14} />
            结束上课
          </button>
        )}
      </div>
    </div>
  );
}
