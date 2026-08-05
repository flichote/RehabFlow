/**
 * PatientStatusBadge — 患者状态徽章
 * docs/design/design-system.md §2.3 状态色
 * docs/design/components.md §6 StatusBadge
 */

import type { PatientStatus } from "@/lib/types";

const CONFIG: Record<
  PatientStatus,
  { label: string; bg: string; text: string }
> = {
  ward:     { label: "在病房",   bg: "bg-neutral-100",   text: "text-neutral-500" },
  en_route: { label: "前往途中", bg: "bg-warning-500/10", text: "text-warning-500" },
  treating: { label: "治疗中",   bg: "bg-success-500/10", text: "text-success-500" },
  paused:   { label: "暂停",     bg: "bg-warning-500/10", text: "text-warning-500" },
  absent:   { label: "缺席",     bg: "bg-danger-500/10",  text: "text-danger-500" },
};

export function PatientStatusBadge({ status }: { status: PatientStatus }) {
  const cfg = CONFIG[status];
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium ${cfg.bg} ${cfg.text}`}
    >
      {cfg.label}
    </span>
  );
}
