"use client";

/**
 * 排课日历 — 核心排课引擎 ★
 * docs/pages.md (admin)/scheduler
 * docs/design/components.md §2.1
 * M2: 拖拽排课 + 冲突弹窗 + CourseDrawer + 周视图
 *
 * TODO: 后端就绪后将 mock 数据替换为 TanStack Query 实际 API 调用
 */

import { useState, useMemo, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ScheduleGrid, type GridDropData } from "@/components/scheduler/ScheduleGrid";
import { SchedulerToolbar, type ViewMode, type DateRange } from "@/components/scheduler/SchedulerToolbar";
import { ResourceSidebar } from "@/components/scheduler/ResourceSidebar";
import { PatientPool } from "@/components/scheduler/PatientPool";
import { CourseDrawer, type DrawerData } from "@/components/scheduler/CourseDrawer";
import { ConflictDialog } from "@/components/scheduler/ConflictDialog";
import { queryKeys } from "@/lib/query-keys";
import {
  mockResourceGroups,
  mockAllTherapists,
  mockPool,
  mockCourses,
  mockDelay,
} from "@/lib/mock-schedule";
import type {
  Course,
  CourseType,
  ConflictResponse,
  Room,
} from "@/lib/types";

// === 日期工具 ===

function getWeekStart(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day; // 周一起始
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

function getWeekDays(start: Date): Date[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    return d;
  });
}

function getDayRange(date: Date): Date[] {
  return [new Date(date)];
}

function getMonthDays(start: Date): Date[] {
  const d = new Date(start);
  d.setDate(1);
  const weekStart = getWeekStart(d);
  return Array.from({ length: 42 }, (_, i) => {
    const day = new Date(weekStart);
    day.setDate(day.getDate() + i);
    return day;
  });
}

export default function SchedulerPage() {
  const queryClient = useQueryClient();

  // 视图状态
  const [viewMode, setViewMode] = useState<ViewMode>("week");
  const [groupFilter, setGroupFilter] = useState<CourseType | "all">("all");
  const [currentDate, setCurrentDate] = useState(new Date());
  const [poolCollapsed, setPoolCollapsed] = useState(false);

  // 抽屉 / 冲突状态
  const [drawerData, setDrawerData] = useState<DrawerData | null>(null);
  const [conflictData, setConflictData] = useState<ConflictResponse | null>(null);
  const [pendingDrop, setPendingDrop] = useState<GridDropData | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);

  // === 数据查询（mock）===
  // TODO: 后端就绪后替换为 api.get("/scheduler/resources") 等
  const { data: resourceGroups = [] } = useQuery({
    queryKey: queryKeys.scheduler.resources,
    queryFn: () => mockDelay(mockResourceGroups),
  });

  const { data: pool = [] } = useQuery({
    queryKey: queryKeys.scheduler.pool,
    queryFn: () => mockDelay(mockPool),
  });

  // 日期范围
  const days = useMemo(() => {
    if (viewMode === "day") return getDayRange(currentDate);
    if (viewMode === "week") return getWeekDays(getWeekStart(currentDate));
    return getMonthDays(currentDate);
  }, [viewMode, currentDate]);

  const dateRange: DateRange = useMemo(() => ({
    start: days[0],
    end: days[days.length - 1],
  }), [days]);

  const fromStr = days[0].toISOString().slice(0, 10);
  const toStr = days[days.length - 1].toISOString().slice(0, 10);

  const { data: courses = [] } = useQuery({
    queryKey: queryKeys.scheduler.courses(fromStr, toStr, groupFilter),
    queryFn: () => mockDelay(mockCourses),
  });

  // 所有治疗室
  const rooms: Room[] = useMemo(() => {
    const seen = new Map<string, Room>();
    mockAllTherapists.forEach((t) => {
      if (!seen.has(t.room_id)) {
        seen.set(t.room_id, { id: t.room_id, name: t.room_name, group: t.group });
      }
    });
    return Array.from(seen.values());
  }, []);

  // === 导航 ===
  const onPrev = useCallback(() => {
    const d = new Date(currentDate);
    if (viewMode === "day") d.setDate(d.getDate() - 1);
    else if (viewMode === "week") d.setDate(d.getDate() - 7);
    else d.setMonth(d.getMonth() - 1);
    setCurrentDate(d);
  }, [currentDate, viewMode]);

  const onNext = useCallback(() => {
    const d = new Date(currentDate);
    if (viewMode === "day") d.setDate(d.getDate() + 1);
    else if (viewMode === "week") d.setDate(d.getDate() + 7);
    else d.setMonth(d.getMonth() + 1);
    setCurrentDate(d);
  }, [currentDate, viewMode]);

  const onToday = useCallback(() => setCurrentDate(new Date()), []);

  // === 拖拽排课 ===
  const handleDrop = useCallback((data: GridDropData) => {
    if (!data.patient) return;
    setPendingDrop(data);
    // TODO: 后端就绪后调用 POST /courses
    // 模拟冲突检测：检查同康复师同时段是否已有课程
    const startISO = new Date(`${data.date}T${String(data.startHour).padStart(2, "0")}:${String(data.startMinute).padStart(2, "0")}:00`).toISOString();
    const endISO = new Date(new Date(startISO).getTime() + 45 * 60000).toISOString();

    const hasConflict = mockCourses.some(
      (c) =>
        c.therapist_id === data.therapistId &&
        new Date(c.start_at) < new Date(endISO) &&
        new Date(c.end_at) > new Date(startISO)
    );

    if (hasConflict) {
      // 模拟 409 冲突响应
      const conflictCourse = mockCourses.find(
        (c) =>
          c.therapist_id === data.therapistId &&
          new Date(c.start_at) < new Date(endISO) &&
          new Date(c.end_at) > new Date(startISO)
      )!;
      setConflictData({
        detail: "该时间段已被占用，是否查看详情？",
        conflicts: [
          {
            type: "therapist",
            course_id: conflictCourse.id,
            patient_name: conflictCourse.patient_name,
            therapist_name: conflictCourse.therapist_name,
            start_at: conflictCourse.start_at,
            end_at: conflictCourse.end_at,
            course_type: conflictCourse.course_type,
          },
        ],
      });
    } else {
      // 无冲突 → 排课成功
      showToast("排课成功", "success");
      setPendingDrop(null);
    }
  }, []);

  // === 冲突弹窗操作 ===
  const handleForce = useCallback(() => {
    // TODO: 后端就绪后调用 POST /courses/{id}/force
    showToast("已强制替换冲突课程", "success");
    setConflictData(null);
    setPendingDrop(null);
  }, []);

  const handleConflictCancel = useCallback(() => {
    setConflictData(null);
    setPendingDrop(null);
  }, []);

  // === 课程卡片点击 → 详情抽屉 ===
  const handleCourseClick = useCallback((course: Course) => {
    setDrawerData({ mode: "view", course });
  }, []);

  // === 双击空白格 → 新建抽屉 ===
  const handleCellDoubleClick = useCallback((data: {
    therapistId: string;
    date: string;
    hour: number;
    minute: number;
  }) => {
    setDrawerData({
      mode: "create",
      prefillTherapistId: data.therapistId,
      prefillDate: data.date,
      prefillStart: `${String(data.hour).padStart(2, "0")}:${String(data.minute).padStart(2, "0")}`,
    });
  }, []);

  // === 抽屉保存 ===
  const handleSave = useCallback((payload: {
    id?: string;
    patient_name: string;
    therapist_id: string;
    room_id: string;
    course_type: CourseType;
    start_at: string;
    end_at: string;
  }) => {
    // TODO: 后端就绪后调用 POST /courses 或 PUT /courses/{id}
    showToast(payload.id ? "课程已修改" : "排课成功", "success");
    setDrawerData(null);
    // 刷新课程列表
    queryClient.invalidateQueries({ queryKey: ["scheduler", "courses"] });
  }, [queryClient]);

  // === 取消课程 ===
  const handleCancelCourse = useCallback((id: string) => {
    // TODO: 后端就绪后调用 DELETE /courses/{id}
    showToast("课程已取消", "success");
    setDrawerData(null);
    queryClient.invalidateQueries({ queryKey: ["scheduler", "courses"] });
  }, [queryClient]);

  // === 提醒 ===
  const handleRemind = useCallback((id: string) => {
    // TODO: 后端就绪后调用 POST /courses/{id}/remind
    showToast("提醒已发送", "success");
  }, []);

  // === Toast ===
  function showToast(msg: string, type: "success" | "error") {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* 顶部工具条 */}
      <SchedulerToolbar
        groupFilter={groupFilter}
        onGroupChange={setGroupFilter}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        dateRange={dateRange}
        onPrev={onPrev}
        onNext={onNext}
        onToday={onToday}
        poolCollapsed={poolCollapsed}
        onTogglePool={() => setPoolCollapsed(!poolCollapsed)}
      />

      {/* 主体区域 */}
      <div className="flex flex-1 overflow-hidden">
        {/* 左资源栏 */}
        <ResourceSidebar groups={resourceGroups} />

        {/* 时间网格 */}
        <div className="flex-1 overflow-hidden">
          <ScheduleGrid
            days={days}
            therapists={mockAllTherapists}
            courses={courses}
            groupFilter={groupFilter}
            onCourseClick={handleCourseClick}
            onCellDoubleClick={handleCellDoubleClick}
            onDrop={handleDrop}
          />
        </div>

        {/* 右侧待排患者池 */}
        <PatientPool
          patients={pool}
          onDragStart={() => {}}
          collapsed={poolCollapsed}
          onToggle={() => setPoolCollapsed(!poolCollapsed)}
        />
      </div>

      {/* 课程抽屉 */}
      <CourseDrawer
        data={drawerData}
        therapists={mockAllTherapists}
        rooms={rooms}
        onClose={() => setDrawerData(null)}
        onSave={handleSave}
        onCancel={handleCancelCourse}
        onRemind={handleRemind}
      />

      {/* 冲突弹窗 */}
      {conflictData && (
        <ConflictDialog
          conflict={conflictData}
          onForce={handleForce}
          onCancel={handleConflictCancel}
        />
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 animate-in">
          <div
            className={`rounded-md shadow-pop px-4 py-2.5 text-sm font-medium ${
              toast.type === "success"
                ? "bg-success-500 text-white"
                : "bg-danger-500 text-white"
            }`}
          >
            {toast.msg}
          </div>
        </div>
      )}

      <style>{`
        @keyframes animate-in {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-in { animation: animate-in 200ms ease-out; }
      `}</style>
    </div>
  );
}
