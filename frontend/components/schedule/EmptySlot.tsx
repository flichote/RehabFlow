"use client";

/**
 * EmptySlot — 空闲时段标签
 * docs/design/components.md §6 通用组件 / §3.1
 * 灰色虚线标签「空闲 45 分钟」，点击 → 快速新建
 */

import { Plus } from "lucide-react";
import type { FreeSlot } from "@/lib/types";

export function EmptySlot({
  slot,
  onClick,
}: {
  slot: FreeSlot;
  onClick?: (slot: FreeSlot) => void;
}) {
  return (
    <button
      onClick={() => onClick?.(slot)}
      className="flex items-center gap-2 w-full px-3 py-2 group"
    >
      <div className="flex-1 border-t border-dashed border-neutral-300" />
      <span className="flex items-center gap-1 text-xs text-neutral-400 group-hover:text-primary-600 transition-colors">
        <Plus size={12} />
        空闲 {slot.duration_minutes} 分钟
      </span>
      <div className="flex-1 border-t border-dashed border-neutral-300" />
    </button>
  );
}
