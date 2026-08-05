"use client";

/**
 * PatientPool — 待排患者池
 * docs/design/components.md §2.1
 * 右侧可折叠面板，列出未排课患者；拖拽卡片到网格
 */

import { useState } from "react";
import { ChevronDown, ChevronRight, Users } from "lucide-react";
import { CourseTypeBadge } from "@/components/common/CourseTypeBadge";
import type { CourseType, PoolPatient } from "@/lib/types";

const GROUPS: { type: CourseType; label: string }[] = [
  { type: "PT", label: "物理治疗" },
  { type: "OT", label: "作业治疗" },
  { type: "ST", label: "言语治疗" },
];

export function PatientPool({
  patients,
  onDragStart,
  collapsed,
  onToggle,
}: {
  patients: PoolPatient[];
  onDragStart: (patient: PoolPatient) => void;
  collapsed: boolean;
  onToggle: () => void;
}) {
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    PT: true,
    OT: true,
    ST: true,
  });

  function toggleGroup(type: string) {
    setExpandedGroups((p) => ({ ...p, [type]: !p[type] }));
  }

  return (
    <div
      className={`bg-white border-l border-neutral-200 flex flex-col transition-all duration-300 ${
        collapsed ? "w-12" : "w-64"
      }`}
    >
      {/* 标题栏 */}
      <button
        onClick={onToggle}
        className="flex items-center gap-2 px-3 py-3 border-b border-neutral-200 hover:bg-neutral-50 transition-colors"
      >
        {!collapsed && (
          <>
            <Users size={16} className="text-neutral-500" />
            <span className="text-sm font-medium text-neutral-700">
              待排患者池
            </span>
            <span className="text-xs text-neutral-400 ml-auto">
              {patients.length}
            </span>
          </>
        )}
        {collapsed && <Users size={16} className="text-neutral-500 mx-auto" />}
      </button>

      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          {patients.length === 0 && (
            <p className="text-xs text-neutral-400 text-center py-4">
              暂无待排患者
            </p>
          )}
          {GROUPS.map(({ type, label }) => {
            const groupPatients = patients.filter((p) => p.course_type === type);
            if (groupPatients.length === 0) return null;
            const expanded = expandedGroups[type];
            return (
              <div key={type}>
                <button
                  onClick={() => toggleGroup(type)}
                  className="flex items-center gap-1 w-full px-2 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-50 rounded"
                >
                  {expanded ? (
                    <ChevronDown size={12} />
                  ) : (
                    <ChevronRight size={12} />
                  )}
                  <CourseTypeBadge type={type} />
                  <span className="ml-1">{label}</span>
                  <span className="ml-auto text-neutral-400">
                    {groupPatients.length}
                  </span>
                </button>
                {expanded && (
                  <div className="space-y-1 mt-1">
                    {groupPatients.map((p) => (
                      <div
                        key={p.id}
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.effectAllowed = "copy";
                          e.dataTransfer.setData(
                            "application/x-pool-patient",
                            JSON.stringify(p)
                          );
                          onDragStart(p);
                        }}
                        className="cursor-grab rounded-md border border-neutral-200 px-2 py-1.5 hover:shadow-card hover:border-primary-200 transition-all active:cursor-grabbing"
                      >
                        <div className="flex items-center gap-1 mb-0.5">
                          <CourseTypeBadge type={p.course_type} />
                        </div>
                        <div className="text-sm font-medium text-neutral-900">
                          {p.name}
                        </div>
                        <div className="text-xs text-neutral-400 truncate">
                          {p.diagnosis}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
