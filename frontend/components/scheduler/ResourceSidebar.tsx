"use client";

/**
 * ResourceSidebar — 左侧资源栏
 * docs/design/components.md §2.1
 * 康复师分组，可折叠
 */

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { CourseTypeBadge } from "@/components/common/CourseTypeBadge";
import type { ResourceGroup } from "@/lib/types";

export function ResourceSidebar({
  groups,
  onSelectTherapist,
  selectedTherapistId,
}: {
  groups: ResourceGroup[];
  onSelectTherapist?: (id: string) => void;
  selectedTherapistId?: string | null;
}) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  function toggle(group: string) {
    setCollapsed((p) => ({ ...p, [group]: !p[group] }));
  }

  return (
    <div className="w-60 bg-white border-r border-neutral-200 flex flex-col">
      <div className="px-4 py-2 border-b border-neutral-200">
        <span className="text-xs font-medium text-neutral-500">康复师资源</span>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {groups.map((g) => (
          <div key={g.group}>
            <button
              onClick={() => toggle(g.group)}
              className="flex items-center gap-1 w-full px-2 py-1.5 rounded hover:bg-neutral-50"
            >
              {collapsed[g.group] ? (
                <ChevronRight size={14} className="text-neutral-400" />
              ) : (
                <ChevronDown size={14} className="text-neutral-400" />
              )}
              <CourseTypeBadge type={g.group} />
              <span className="text-xs text-neutral-400 ml-auto">
                {g.therapists.length}人
              </span>
            </button>
            {!collapsed[g.group] && (
              <div className="ml-4 mt-0.5 space-y-0.5">
                {g.therapists.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => onSelectTherapist?.(t.id)}
                    className={`flex items-center gap-1 w-full px-2 py-1 rounded text-xs transition-colors ${
                      selectedTherapistId === t.id
                        ? "bg-primary-50 text-primary-700"
                        : "text-neutral-600 hover:bg-neutral-50"
                    }`}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-neutral-300" />
                    <span className="font-medium">{t.name}</span>
                    <span className="text-neutral-400 ml-auto">{t.room_name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
