"use client";

/**
 * 康复师课表 — 核心页面（日程清单式）★
 * docs/pages.md (therapist)/schedule
 * docs/design/components.md §3.1
 *
 * 今日概览卡 + 时间线列表 + 开始/结束上课
 * TODO: 后端就绪后将 mock 数据替换为 TanStack Query 实际 API 调用
 */

import { useState, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays } from "lucide-react";
import { TodayOverviewCard } from "@/components/schedule/TodayOverviewCard";
import { TimelineList } from "@/components/schedule/TimelineList";
import { todayStr, WEEKDAY_LABELS } from "@/lib/format";
import {
  mockTodayOverview,
  mockTherapistSchedule,
  mockDelay,
} from "@/lib/mock-schedule";
import type { FreeSlot } from "@/lib/types";

export default function TherapistSchedulePage() {
  const queryClient = useQueryClient();
  const [selectedDate, setSelectedDate] = useState(todayStr());
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);

  // TODO: 后端就绪后替换为真实 API
  // const { data } = useQuery({
  //   queryKey: queryKeys.schedule.therapist(selectedDate),
  //   queryFn: () => courseApi.schedule(selectedDate),
  // });

  const { data: overview = mockTodayOverview } = useQuery({
    queryKey: ["therapist", "overview", selectedDate],
    queryFn: () => mockDelay(mockTodayOverview),
  });

  // 模拟当前登录康复师 ID
  const mockTherapistId = "t-pt-1";

  const { data: timeline = [] } = useQuery({
    queryKey: ["therapist", "timeline", selectedDate],
    queryFn: () => mockDelay(mockTherapistSchedule(mockTherapistId)),
  });

  // === 开始上课 ===
  function handleStart(courseId: string) {
    // TODO: 后端就绪后调用 POST /courses/{id}/start
    showToast("已开始上课", "success");
    queryClient.invalidateQueries({ queryKey: ["therapist"] });
  }

  // === 结束上课 ===
  function handleFinish(courseId: string) {
    // TODO: 后端就绪后调用 POST /courses/{id}/finish
    showToast("已结束上课，课时已记录", "success");
    queryClient.invalidateQueries({ queryKey: ["therapist"] });
  }

  // === 提醒 ===
  function handleRemind(courseId: string) {
    // TODO: 后端就绪后调用 POST /courses/{id}/remind
    showToast("提醒已发送", "success");
  }

  // === 空闲时段点击 → 快速新建（TODO）===
  function handleFreeSlotClick(slot: FreeSlot) {
    // TODO: 打开新建课程抽屉，预填时间段
    showToast(`空闲 ${slot.duration_minutes} 分钟（快速新建待实现）`, "error");
  }

  function showToast(msg: string, type: "success" | "error") {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }

  const todayLabel = useMemo(() => {
    const d = new Date(selectedDate);
    return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${WEEKDAY_LABELS[d.getDay()]}`;
  }, [selectedDate]);

  return (
    <div className="max-w-[720px] mx-auto space-y-4">
      {/* 页头 */}
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-bold text-neutral-900">我的课表</h1>
        <span className="text-sm text-neutral-400">{todayLabel}</span>
        <div className="ml-auto flex items-center gap-2">
          <CalendarDays size={16} className="text-neutral-400" />
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="rounded-md border border-neutral-200 px-2 py-1 text-sm text-neutral-600 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      {/* 今日概览卡 */}
      <TodayOverviewCard overview={overview} />

      {/* 时间线列表 */}
      <div className="bg-white rounded-lg border border-neutral-200 shadow-card p-4">
        <h2 className="text-sm font-semibold text-neutral-700 mb-3">今日课程</h2>
        <TimelineList
          items={timeline}
          onStart={handleStart}
          onFinish={handleFinish}
          onRemind={handleRemind}
          onFreeSlotClick={handleFreeSlotClick}
        />
      </div>

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
