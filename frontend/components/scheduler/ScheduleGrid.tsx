"use client";

/**
 * ScheduleGrid — 排课时间轴网格（核心组件）
 * docs/design/components.md §2.1 / §6
 * 行=资源（康复师），列=时间（15min 粒度），时间列 64px
 * 拖拽放置 + 双击新建 + 点击课程卡片 + 当前时间线
 */

import { useMemo } from "react";
import { CourseCard } from "./CourseCard";
import type { Course, CourseType, TherapistResource, PoolPatient } from "@/lib/types";

// 布局常量
const TIME_COL_WIDTH = 64;   // px — 时间列宽度
const ROW_HEIGHT = 56;       // px — 每个资源行高度
const HOUR_HEIGHT = ROW_HEIGHT; // 每小时高度
const SLOT_MINUTES = 15;     // 粒度
const SLOTS_PER_HOUR = 60 / SLOT_MINUTES;
const SLOT_HEIGHT = HOUR_HEIGHT / SLOTS_PER_HOUR; // 每个 15min 格子高度

const START_HOUR = 8;  // 网格起始时间 8:00
const END_HOUR = 20;   // 网格结束时间 20:00
const TOTAL_HOURS = END_HOUR - START_HOUR;

export interface GridDropData {
  therapistId: string;
  date: string;    // YYYY-MM-DD
  startHour: number;
  startMinute: number;
  patient?: PoolPatient;
}

export function ScheduleGrid({
  days,
  therapists,
  courses,
  groupFilter,
  onCourseClick,
  onCellDoubleClick,
  onDrop,
  draggingCourseId,
}: {
  days: Date[];
  therapists: TherapistResource[];
  courses: Course[];
  groupFilter: CourseType | "all";
  onCourseClick: (course: Course) => void;
  onCellDoubleClick: (data: { therapistId: string; date: string; hour: number; minute: number }) => void;
  onDrop: (data: GridDropData) => void;
  draggingCourseId?: string | null;
}) {
  const timeSlots = useMemo(() => {
    const slots: { hour: number; minute: number; label: string }[] = [];
    for (let h = START_HOUR; h < END_HOUR; h++) {
      for (let m = 0; m < 60; m += SLOT_MINUTES) {
        slots.push({
          hour: h,
          minute: m,
          label: m === 0 ? `${String(h).padStart(2, "0")}:00` : "",
        });
      }
    }
    return slots;
  }, []);

  const filteredTherapists = useMemo(() => {
    if (groupFilter === "all") return therapists;
    return therapists.filter((t) => t.group === groupFilter);
  }, [therapists, groupFilter]);

  // 当前时间线
  const now = new Date();
  const nowOffset = useMemo(() => {
    const h = now.getHours() + now.getMinutes() / 60;
    if (h < START_HOUR || h > END_HOUR) return null;
    return (h - START_HOUR) * HOUR_HEIGHT;
  }, [now]);

  // 检查某天是否是今天
  function isToday(date: Date): boolean {
    const n = new Date();
    return (
      date.getFullYear() === n.getFullYear() &&
      date.getMonth() === n.getMonth() &&
      date.getDate() === n.getDate()
    );
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }

  function handleDrop(
    e: React.DragEvent,
    therapistId: string,
    day: Date
  ) {
    e.preventDefault();
    const raw = e.dataTransfer.getData("application/x-pool-patient");
    if (!raw) return;
    let patient: PoolPatient | undefined;
    try {
      patient = JSON.parse(raw) as PoolPatient;
    } catch {
      return;
    }

    // 计算松手位置对应的时间槽
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const totalSlots = Math.floor(y / SLOT_HEIGHT);
    const totalMinutes = totalSlots * SLOT_MINUTES;
    const hour = START_HOUR + Math.floor(totalMinutes / 60);
    const minute = totalMinutes % 60;

    onDrop({
      therapistId,
      date: day.toISOString().slice(0, 10),
      startHour: hour,
      startMinute: minute,
      patient,
    });
  }

  function handleDoubleClick(
    e: React.MouseEvent,
    therapistId: string,
    day: Date
  ) {
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const totalSlots = Math.floor(y / SLOT_HEIGHT);
    const totalMinutes = totalSlots * SLOT_MINUTES;
    const hour = START_HOUR + Math.floor(totalMinutes / 60);
    const minute = totalMinutes % 60;
    onCellDoubleClick({
      therapistId,
      date: day.toISOString().slice(0, 10),
      hour,
      minute,
    });
  }

  // 获取某天某康复师的课程
  function getCoursesForCell(therapistId: string, day: Date): Course[] {
    return courses.filter((c) => {
      if (c.therapist_id !== therapistId) return false;
      const cDate = new Date(c.start_at);
      return (
        cDate.getFullYear() === day.getFullYear() &&
        cDate.getMonth() === day.getMonth() &&
        cDate.getDate() === day.getDate()
      );
    });
  }

  // 计算课程在网格中的位置
  function courseStyle(course: Course): { top: number; height: number } {
    const start = new Date(course.start_at);
    const end = new Date(course.end_at);
    const startMinutes = (start.getHours() - START_HOUR) * 60 + start.getMinutes();
    const endMinutes = (end.getHours() - START_HOUR) * 60 + end.getMinutes();
    const top = (startMinutes / SLOT_MINUTES) * SLOT_HEIGHT;
    const height = Math.max(((endMinutes - startMinutes) / SLOT_MINUTES) * SLOT_HEIGHT, SLOT_HEIGHT);
    return { top: top + 2, height: height - 4 };
  }

  const gridWidth = `calc(100% - ${TIME_COL_WIDTH}px)`;
  const dayColWidth = days.length > 0 ? `calc(${gridWidth} / ${days.length})` : "100%";

  return (
    <div className="flex flex-col h-full overflow-auto bg-white">
      {/* 日期表头 */}
      <div className="flex sticky top-0 z-20 bg-white border-b border-neutral-200">
        {/* 左上角 */}
        <div
          className="border-r border-neutral-200 flex items-center justify-center text-xs text-neutral-400"
          style={{ width: TIME_COL_WIDTH, minWidth: TIME_COL_WIDTH }}
        >
          时间
        </div>
        {/* 每天的列头 */}
        {days.map((day, i) => (
          <div
            key={i}
            className={`border-r border-neutral-200 flex flex-col items-center justify-center py-1.5 ${
              isToday(day) ? "bg-primary-50" : ""
            }`}
            style={{ width: dayColWidth, minWidth: 120 }}
          >
            <span className="text-xs text-neutral-400">
              {["日", "一", "二", "三", "四", "五", "六"][day.getDay()]}
            </span>
            <span
              className={`text-sm font-medium tabular-nums ${
                isToday(day) ? "text-primary-700" : "text-neutral-700"
              }`}
            >
              {day.getMonth() + 1}/{day.getDate()}
            </span>
          </div>
        ))}
      </div>

      {/* 资源行 */}
      {filteredTherapists.map((therapist) => (
        <div key={therapist.id} className="flex border-b border-neutral-200">
          {/* 资源标签列 */}
          <div
            className="border-r border-neutral-200 px-2 py-1.5 flex flex-col justify-center"
            style={{ width: TIME_COL_WIDTH, minWidth: TIME_COL_WIDTH }}
          >
            <span className="text-xs font-medium text-neutral-900 truncate">
              {therapist.name}
            </span>
            <span className="text-[10px] text-neutral-400 truncate">
              {therapist.room_name}
            </span>
          </div>

          {/* 每天的格子 */}
          {days.map((day, dayIdx) => (
            <div
              key={dayIdx}
              className="relative border-r border-neutral-200"
              style={{ width: dayColWidth, minWidth: 120, height: TOTAL_HOURS * HOUR_HEIGHT }}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, therapist.id, day)}
              onDoubleClick={(e) => handleDoubleClick(e, therapist.id, day)}
            >
              {/* 时间槽分隔线 */}
              {timeSlots.map((slot, slotIdx) => (
                <div
                  key={slotIdx}
                  className={`absolute left-0 right-0 border-t ${
                    slot.minute === 0
                      ? "border-neutral-200"
                      : "border-neutral-100 border-dashed"
                  }`}
                  style={{ top: slotIdx * SLOT_HEIGHT }}
                >
                  {slot.label && (
                    <span className="absolute -top-1.5 left-1 text-[10px] text-neutral-300 tabular-nums">
                      {slot.label}
                    </span>
                  )}
                </div>
              ))}

              {/* 当前时间线 */}
              {isToday(day) && nowOffset !== null && (
                <div
                  className="absolute left-0 right-0 z-10 flex items-center pointer-events-none"
                  style={{ top: nowOffset }}
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-danger-500 -ml-0.5" />
                  <div className="flex-1 h-px bg-danger-500" />
                </div>
              )}

              {/* 课程卡片 */}
              {getCoursesForCell(therapist.id, day).map((course) => {
                const { top, height } = courseStyle(course);
                return (
                  <div
                    key={course.id}
                    className="absolute left-0.5 right-0.5 z-5"
                    style={{ top, height }}
                  >
                    <CourseCard
                      course={course}
                      onClick={() => onCourseClick(course)}
                      dragging={draggingCourseId === course.id}
                    />
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      ))}

      {/* 空状态 */}
      {filteredTherapists.length === 0 && (
        <div className="flex items-center justify-center py-12 text-sm text-neutral-400">
          该组别暂无康复师资源
        </div>
      )}
    </div>
  );
}
