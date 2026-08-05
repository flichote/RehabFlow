/**
 * StatusBadge — 课程状态徽章
 * docs/design/components.md §6 通用组件
 * docs/design/design-system.md §2.3 状态色
 * docs/design/flows.md 状态流转速查
 */

import type { CourseStatus } from "@/lib/types";

const CONFIG: Record<
  CourseStatus,
  { label: string; bg: string; text: string }
> = {
  scheduled:  { label: "待执行",   bg: "bg-neutral-100",   text: "text-neutral-500" },
  reminded:   { label: "提醒已发", bg: "bg-warning-500/10", text: "text-warning-500" },
  ongoing:    { label: "进行中",   bg: "bg-success-500/10", text: "text-success-500" },
  completed:  { label: "已完成",   bg: "bg-success-500/10", text: "text-success-500" },
  absent:     { label: "缺席",     bg: "bg-danger-500/10",  text: "text-danger-500" },
  abnormal:   { label: "异常",     bg: "bg-danger-500/10",  text: "text-danger-500" },
};

export function StatusBadge({ status }: { status: CourseStatus }) {
  const cfg = CONFIG[status];
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium ${cfg.bg} ${cfg.text}`}
    >
      {cfg.label}
    </span>
  );
}
