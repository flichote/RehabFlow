"use client";

/**
 * AlertFeed — 异常预警滚动列表
 * docs/design/components.md §5.1:
 * - 未处理项左侧 danger-500 3px 竖条 + 入场滑动动画
 * - 点击跳 /admin/alerts
 */

import Link from "next/link";
import {
  AlertTriangle,
  Clock,
  UserX,
  MapPin,
  Zap,
  type LucideIcon,
} from "lucide-react";
import type { AlertItem, AlertType } from "@/lib/types";
import { ChartCard } from "./ChartCard";

const ICON_MAP: Record<AlertType, LucideIcon> = {
  absent: UserX,
  overtime: Clock,
  conflict: Zap,
  abnormal: AlertTriangle,
  location: MapPin,
};

/** 相对时间 */
function relTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return "刚刚";
  if (min < 60) return `${min} 分钟前`;
  const h = Math.floor(min / 60);
  return `${h} 小时前`;
}

export function AlertFeed({
  alerts,
  isLoading = false,
}: {
  alerts: AlertItem[];
  isLoading?: boolean;
}) {
  return (
    <ChartCard title="异常预警" refreshLabel="实时">
      {isLoading ? (
        <div className="h-48 flex items-center justify-center text-sm text-neutral-400">
          加载中…
        </div>
      ) : alerts.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-sm text-neutral-400">
          暂无预警
        </div>
      ) : (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {alerts.map((alert, idx) => {
            const Icon = ICON_MAP[alert.type] ?? AlertTriangle;
            const isOpen = alert.status === "open";
            return (
              <Link
                key={alert.id}
                href="/admin/alerts"
                className={`flex items-start gap-2 rounded-md p-2 pr-3 transition-all hover:bg-neutral-50 ${
                  isOpen
                    ? "border-l-[3px] border-danger-500 bg-danger-500/5"
                    : "border-l-[3px] border-transparent opacity-60"
                }`}
                style={{
                  animation: isOpen
                    ? `slideIn 0.3s ease-out ${idx * 0.05}s both`
                    : undefined,
                }}
              >
                <Icon
                  size={16}
                  className={isOpen ? "text-danger-500 mt-0.5 shrink-0" : "text-neutral-400 mt-0.5 shrink-0"}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium text-neutral-900 truncate">
                      {alert.title}
                    </span>
                    <span className="text-[11px] text-neutral-400 shrink-0 tabular-nums">
                      {relTime(alert.created_at)}
                    </span>
                  </div>
                  <p className="text-xs text-neutral-500 mt-0.5 line-clamp-2">
                    {alert.summary}
                  </p>
                </div>
              </Link>
            );
          })}
        </div>
      )}
      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(-8px); }
          to { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </ChartCard>
  );
}
