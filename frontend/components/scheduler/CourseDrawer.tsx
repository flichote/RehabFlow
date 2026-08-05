"use client";

/**
 * CourseDrawer — 课程详情/新建抽屉
 * docs/design/components.md §2.2
 * 右滑出面板 480px；患者信息 + 类型徽章 + 时间选择 + 治疗室 + 康复师
 */

import { useEffect } from "react";
import { X, Bell, FileText, Trash2, Save } from "lucide-react";
import { CourseTypeBadge } from "@/components/common/CourseTypeBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { useState } from "react";
import { formatTime } from "@/lib/format";
import type { Course, CourseType, TherapistResource, Room } from "@/lib/types";

export interface DrawerData {
  mode: "create" | "view";
  course?: Course;
  // 新建模式预填
  prefillTherapistId?: string;
  prefillDate?: string;   // YYYY-MM-DD
  prefillStart?: string;  // HH:mm
}

export function CourseDrawer({
  data,
  therapists,
  rooms,
  onClose,
  onSave,
  onCancel,
  onRemind,
}: {
  data: DrawerData | null;
  therapists: TherapistResource[];
  rooms: Room[];
  onClose: () => void;
  onSave: (payload: {
    id?: string;
    patient_name: string;
    therapist_id: string;
    room_id: string;
    course_type: CourseType;
    start_at: string;
    end_at: string;
  }) => void;
  onCancel?: (id: string) => void;
  onRemind?: (id: string) => void;
}) {
  const [confirmCancel, setConfirmCancel] = useState(false);

  // 表单状态
  const [patientName, setPatientName] = useState("");
  const [therapistId, setTherapistId] = useState("");
  const [roomId, setRoomId] = useState("");
  const [courseType, setCourseType] = useState<CourseType>("PT");
  const [dateStr, setDateStr] = useState("");
  const [startTime, setStartTime] = useState("09:00");
  const [duration, setDuration] = useState(45);

  useEffect(() => {
    if (!data) return;
    if (data.mode === "view" && data.course) {
      const c = data.course;
      setPatientName(c.patient_name);
      setTherapistId(c.therapist_id);
      setRoomId(c.room_id);
      setCourseType(c.course_type);
      const d = new Date(c.start_at);
      setDateStr(d.toISOString().slice(0, 10));
      setStartTime(formatTime(c.start_at));
      const dur = Math.round(
        (new Date(c.end_at).getTime() - new Date(c.start_at).getTime()) / 60000
      );
      setDuration(dur);
    } else if (data.mode === "create") {
      setPatientName("");
      setTherapistId(data.prefillTherapistId ?? "");
      setRoomId("");
      setCourseType("PT");
      setDateStr(data.prefillDate ?? new Date().toISOString().slice(0, 10));
      setStartTime(data.prefillStart ?? "09:00");
      setDuration(45);
    }
  }, [data]);

  if (!data) return null;

  const isView = data.mode === "view";
  const status = data.course?.status;

  function buildPayload() {
    const [h, m] = startTime.split(":").map(Number);
    const d = new Date(dateStr);
    d.setHours(h, m, 0, 0);
    const start = d.toISOString();
    const end = new Date(d.getTime() + duration * 60000).toISOString();
    return {
      id: data?.course?.id,
      patient_name: patientName,
      therapist_id: therapistId,
      room_id: roomId,
      course_type: courseType,
      start_at: start,
      end_at: end,
    };
  }

  return (
    <>
      {/* 抽屉 */}
      <div className="fixed inset-0 z-40 flex justify-end">
        <div className="absolute inset-0 bg-neutral-900/30" onClick={onClose} />
        <div
          className="relative bg-white w-full max-w-[480px] h-full shadow-pop overflow-y-auto"
          style={{ animation: "slideInRight 300ms ease-out" }}
        >
          {/* 标题栏 */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 sticky top-0 bg-white z-10">
            <h2 className="text-base font-semibold text-neutral-900">
              {isView ? "课程详情" : "新建课程"}
            </h2>
            <button onClick={onClose} className="text-neutral-400 hover:text-neutral-700">
              <X size={20} />
            </button>
          </div>

          {/* 内容区 */}
          <div className="p-6 space-y-4">
            {/* 状态区（仅查看模式） */}
            {isView && status && (
              <div className="flex items-center gap-2 pb-3 border-b border-neutral-100">
                <span className="text-sm text-neutral-500">状态：</span>
                <StatusBadge status={status} />
                {data.course?.actual_start_at && (
                  <span className="text-xs text-neutral-500 ml-auto tabular-nums">
                    实际：{formatTime(data.course.actual_start_at)}
                    {data.course.actual_end_at && `–${formatTime(data.course.actual_end_at)}`}
                  </span>
                )}
              </div>
            )}

            {/* 患者姓名 */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                患者姓名
              </label>
              <input
                type="text"
                value={patientName}
                onChange={(e) => setPatientName(e.target.value)}
                disabled={isView}
                className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-50 disabled:text-neutral-500"
                placeholder="输入患者姓名"
              />
            </div>

            {/* 课程类型 */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                课程类型
              </label>
              <div className="flex gap-2">
                {(["PT", "OT", "ST"] as CourseType[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => !isView && setCourseType(t)}
                    disabled={isView}
                    className={`flex items-center gap-1 ${
                      courseType === t ? "" : "opacity-40"
                    } disabled:cursor-not-allowed`}
                  >
                    <CourseTypeBadge type={t} size="md" />
                  </button>
                ))}
              </div>
            </div>

            {/* 日期 + 时间 */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  日期
                </label>
                <input
                  type="date"
                  value={dateStr}
                  onChange={(e) => setDateStr(e.target.value)}
                  disabled={isView}
                  className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-50 disabled:text-neutral-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  开始时间
                </label>
                <select
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  disabled={isView}
                  className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-50 disabled:text-neutral-500"
                >
                  {Array.from({ length: 48 }, (_, i) => {
                    const h = Math.floor(i / 2) + 8; // 8:00 - 20:00
                    const m = (i % 2) * 30;
                    if (h > 20) return null;
                    const v = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
                    return (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    );
                  })}
                </select>
              </div>
            </div>

            {/* 时长 */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                时长（分钟）
              </label>
              <div className="flex gap-2">
                {[30, 45, 60, 90].map((d) => (
                  <button
                    key={d}
                    onClick={() => !isView && setDuration(d)}
                    disabled={isView}
                    className={`rounded-md px-3 py-1.5 text-sm border transition-colors disabled:cursor-not-allowed ${
                      duration === d
                        ? "border-primary-600 bg-primary-50 text-primary-700"
                        : "border-neutral-200 text-neutral-500"
                    }`}
                  >
                    {d}分钟
                  </button>
                ))}
              </div>
            </div>

            {/* 康复师 */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                康复师
              </label>
              <select
                value={therapistId}
                onChange={(e) => setTherapistId(e.target.value)}
                disabled={isView}
                className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-50 disabled:text-neutral-500"
              >
                <option value="">请选择</option>
                {therapists.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}（{t.group}）
                  </option>
                ))}
              </select>
            </div>

            {/* 治疗室 */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                治疗室
              </label>
              <select
                value={roomId}
                onChange={(e) => setRoomId(e.target.value)}
                disabled={isView}
                className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-neutral-50 disabled:text-neutral-500"
              >
                <option value="">请选择</option>
                {rooms.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* 底部操作区 */}
          <div className="sticky bottom-0 bg-white border-t border-neutral-200 px-6 py-4 flex items-center gap-2">
            {isView ? (
              <>
                {onRemind && data.course && (
                  <button
                    onClick={() => onRemind(data.course!.id)}
                    className="flex items-center gap-1 rounded-md px-3 py-2 text-sm text-neutral-600 hover:bg-neutral-100 transition-colors"
                  >
                    <Bell size={16} />
                    提醒
                  </button>
                )}
                {onCancel && data.course && (
                  <button
                    onClick={() => setConfirmCancel(true)}
                    className="flex items-center gap-1 rounded-md px-3 py-2 text-sm text-danger-500 hover:bg-danger-500/10 transition-colors ml-auto"
                  >
                    <Trash2 size={16} />
                    取消课程
                  </button>
                )}
              </>
            ) : (
              <>
                <button
                  onClick={onClose}
                  className="rounded-md px-4 py-2 text-sm text-neutral-500 hover:bg-neutral-100 transition-colors ml-auto"
                >
                  取消
                </button>
                <button
                  onClick={() => onSave(buildPayload())}
                  disabled={!patientName || !therapistId || !roomId}
                  className="flex items-center gap-1 rounded-md px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Save size={16} />
                  保存
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 取消课程确认弹窗 */}
      {isView && onCancel && data.course && (
        <ConfirmDialog
          open={confirmCancel}
          title="取消课程"
          message={`确定要取消 ${data.course.patient_name} 的课程吗？取消后将通知双方。`}
          confirmLabel="确认取消"
          danger
          onConfirm={() => {
            onCancel(data.course!.id);
            setConfirmCancel(false);
          }}
          onCancel={() => setConfirmCancel(false)}
        />
      )}

      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
      `}</style>
    </>
  );
}
