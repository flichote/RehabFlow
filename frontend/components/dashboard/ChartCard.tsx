/**
 * ChartCard — 图表容器
 * docs/design/components.md §5.1: 标题 + 刷新频率角标 + 图表区
 * docs/design/design-system.md §4: rounded-lg shadow-card
 */

import type { ReactNode } from "react";

export function ChartCard({
  title,
  refreshLabel,
  children,
  className = "",
}: {
  title: string;
  refreshLabel?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-lg bg-white border border-neutral-200 shadow-card flex flex-col ${className}`}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-100">
        <h3 className="text-base font-semibold text-neutral-900">{title}</h3>
        {refreshLabel && (
          <span className="text-[11px] font-medium text-neutral-400 bg-neutral-50 rounded px-1.5 py-0.5">
            {refreshLabel}
          </span>
        )}
      </div>
      <div className="flex-1 p-4">{children}</div>
    </div>
  );
}
