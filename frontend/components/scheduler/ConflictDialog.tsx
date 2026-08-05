"use client";

/**
 * ConflictDialog — 冲突弹窗
 * docs/design/components.md §2.3
 * 患者冲突 / 康复师冲突分别展示；查看详情 / 强制替换 / 取消
 */

import { AlertCircle, User, UserCog } from "lucide-react";
import { CourseTypeBadge } from "@/components/common/CourseTypeBadge";
import { formatTime } from "@/lib/format";
import type { ConflictDetail, ConflictResponse } from "@/lib/types";

export function ConflictDialog({
  conflict,
  onForce,
  onCancel,
}: {
  conflict: ConflictResponse;
  onForce: () => void;
  onCancel: () => void;
}) {
  if (!conflict) return null;

  const patientConflicts = conflict.conflicts.filter((c) => c.type === "patient");
  const therapistConflicts = conflict.conflicts.filter((c) => c.type === "therapist");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-neutral-900/40" onClick={onCancel} />
      <div
        className="relative bg-white rounded-lg shadow-pop p-6 w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto"
        role="dialog"
        aria-modal="true"
      >
        {/* 标题区 */}
        <div className="flex items-center gap-2 mb-4">
          <AlertCircle size={20} className="text-danger-500" />
          <h3 className="text-base font-semibold text-neutral-900">
            排课冲突
          </h3>
        </div>
        <p className="text-sm text-neutral-500 mb-4">
          {conflict.detail || "该时间段已被占用，请查看冲突详情"}
        </p>

        {/* 冲突明细 */}
        <div className="space-y-3 mb-6">
          {patientConflicts.length > 0 && (
            <ConflictSection
              title="患者同时段课程"
              icon={<User size={14} className="text-neutral-500" />}
              items={patientConflicts}
            />
          )}
          {therapistConflicts.length > 0 && (
            <ConflictSection
              title="康复师同时段课程"
              icon={<UserCog size={14} className="text-neutral-500" />}
              items={therapistConflicts}
            />
          )}
        </div>

        {/* 操作区 */}
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-md px-4 py-2 text-sm font-medium text-neutral-500 hover:bg-neutral-100 transition-colors"
          >
            取消
          </button>
          <button
            onClick={onForce}
            className="rounded-md px-4 py-2 text-sm font-medium text-white bg-danger-500 hover:bg-danger-500/90 transition-colors"
          >
            强制替换
          </button>
        </div>
      </div>
    </div>
  );
}

function ConflictSection({
  title,
  icon,
  items,
}: {
  title: string;
  icon: React.ReactNode;
  items: ConflictDetail[];
}) {
  return (
    <div className="rounded-md border border-neutral-200 overflow-hidden">
      <div className="flex items-center gap-1.5 bg-neutral-100 px-3 py-1.5 text-xs font-medium text-neutral-700">
        {icon}
        {title}
      </div>
      <div className="divide-y divide-neutral-100">
        {items.map((c, i) => (
          <div key={i} className="flex items-center gap-2 px-3 py-2 text-sm">
            <CourseTypeBadge type={c.course_type} />
            <span className="text-neutral-900 font-medium">{c.patient_name}</span>
            <span className="text-neutral-500">{c.therapist_name}</span>
            <span className="text-neutral-500 tabular-nums ml-auto">
              {formatTime(c.start_at)}–{formatTime(c.end_at)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
