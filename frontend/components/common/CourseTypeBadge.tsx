/**
 * CourseTypeBadge — 课程类型徽章（PT 蓝 / OT 绿 / ST 橙）
 * docs/design/components.md §6 通用组件
 * docs/design/design-system.md §2.2 课程类型三色
 */

import { Dumbbell, Hand, MessageCircle, type LucideIcon } from "lucide-react";
import type { CourseType } from "@/lib/types";

const CONFIG: Record<
  CourseType,
  { label: string; icon: LucideIcon; bg: string; text: string; border: string }
> = {
  PT: {
    label: "PT",
    icon: Dumbbell,
    bg: "bg-pt-50",
    text: "text-pt-500",
    border: "border-pt-500/20",
  },
  OT: {
    label: "OT",
    icon: Hand,
    bg: "bg-ot-50",
    text: "text-ot-500",
    border: "border-ot-500/20",
  },
  ST: {
    label: "ST",
    icon: MessageCircle,
    bg: "bg-st-50",
    text: "text-st-500",
    border: "border-st-500/20",
  },
};

export function CourseTypeBadge({
  type,
  size = "sm",
}: {
  type: CourseType;
  size?: "sm" | "md";
}) {
  const cfg = CONFIG[type];
  const Icon = cfg.icon;
  const sizing =
    size === "md"
      ? "px-2.5 py-1 text-xs gap-1"
      : "px-1.5 py-0.5 text-[11px] gap-0.5";

  return (
    <span
      className={`inline-flex items-center rounded ${cfg.bg} ${cfg.text} ${cfg.border} border font-medium ${sizing}`}
    >
      <Icon size={size === "md" ? 14 : 12} />
      {cfg.label}
    </span>
  );
}
