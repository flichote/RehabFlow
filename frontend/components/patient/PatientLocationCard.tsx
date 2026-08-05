"use client";

/**
 * PatientLocationCard — 实时位置大卡片
 * docs/design/components.md §4.1:
 * - 大号状态文字「当前位于：PT大厅2号床」+ 状态徽章
 * - 变更时 300ms fade
 * docs/design/design-system.md §5: 位置卡片数值切换时 300ms fade
 */

import { MapPin } from "lucide-react";
import type { PatientLocation } from "@/lib/types";
import { PatientStatusBadge } from "@/components/patient/PatientStatusBadge";

export function PatientLocationCard({
  location,
}: {
  location: PatientLocation;
}) {
  return (
    <div className="rounded-lg bg-white border border-neutral-200 shadow-card p-4">
      <div className="flex items-center gap-2 mb-3">
        <MapPin size={16} className="text-primary-500" />
        <span className="text-sm font-semibold text-neutral-900">实时位置</span>
      </div>
      <div
        key={`${location.current_location}-${location.updated_at}`}
        className="rounded-md bg-primary-50 p-3 transition-opacity duration-300"
        style={{ animation: "fadeIn 0.3s ease-out" }}
      >
        <p className="text-xs text-neutral-500 mb-1">当前位于</p>
        <p className="text-lg font-bold text-neutral-900">
          {location.current_location}
        </p>
        <div className="mt-2 flex items-center gap-2">
          <PatientStatusBadge status={location.status} />
          <span className="text-[11px] text-neutral-400 tabular-nums">
            更新于 {new Date(location.updated_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
      </div>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
