"use client";

/**
 * 主任数据看板 ★
 * docs/design/components.md §5.1 / docs/design/pages.md (admin)/dashboard
 * 12 栅格布局: KPI×4 + DonutChart + BarChart + AlertFeed + LineChart
 * 刷新策略: KPI/分布实时(30s), 工作量30min, 趋势每日
 * TODO: 后端就绪后切换到 dashboardApi/alertsApi 实际调用
 */

import { useQuery } from "@tanstack/react-query";
import { Users, CalendarCheck, Activity, UserCheck } from "lucide-react";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { DonutChart } from "@/components/dashboard/DonutChart";
import { BarChart } from "@/components/dashboard/BarChart";
import { LineChart } from "@/components/dashboard/LineChart";
import { AlertFeed } from "@/components/dashboard/AlertFeed";
import { queryKeys } from "@/lib/query-keys";
import { todayStr } from "@/lib/format";
import {
  mockKpis,
  mockPatientDistribution,
  mockTherapistWorkload,
  mockCourseTrend,
  mockAlerts,
  mockDelay,
} from "@/lib/mock-dashboard";
import type {
  DashboardKpis,
  PatientDistribution,
  TherapistWorkload,
  CourseTrend,
  AlertItem,
} from "@/lib/types";

export default function DashboardPage() {
  // KPI — 30s 轮询
  const { data: kpis, isLoading: kpiLoading } = useQuery({
    queryKey: queryKeys.dashboard.kpis,
    queryFn: () => mockDelay(mockKpis),
    refetchInterval: 30_000,
  });

  // 患者分布 — 30s 轮询
  const { data: distribution, isLoading: distLoading } = useQuery({
    queryKey: queryKeys.dashboard.distribution,
    queryFn: () => mockDelay(mockPatientDistribution),
    refetchInterval: 30_000,
  });

  // 治疗师课时 — 30min 轮询
  const { data: workload, isLoading: wlLoading } = useQuery({
    queryKey: queryKeys.dashboard.workload(todayStr()),
    queryFn: () => mockDelay(mockTherapistWorkload),
    refetchInterval: 30 * 60 * 1000,
  });

  // 课程趋势 — 每日刷新
  const { data: trend, isLoading: trendLoading } = useQuery({
    queryKey: queryKeys.dashboard.trend(7),
    queryFn: () => mockDelay(mockCourseTrend),
    refetchInterval: 24 * 60 * 60 * 1000,
  });

  // 预警 — 30s 轮询
  const { data: alerts, isLoading: alertLoading } = useQuery({
    queryKey: queryKeys.alerts.list("open"),
    queryFn: () => mockDelay(mockAlerts),
    refetchInterval: 30_000,
  });

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <h1 className="text-xl font-bold text-neutral-900 mb-4">主任看板</h1>

      <div className="grid grid-cols-12 gap-4">
        {/* 顶部 KPI 通栏 ×4 */}
        <div className="col-span-12 grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="今日在院患者"
            value={kpis?.in_hospital_patients ?? "--"}
            unit="人"
            trend={kpis?.patient_trend}
            icon={Users}
          />
          <KpiCard
            label="今日已排课程"
            value={kpis?.today_courses ?? "--"}
            unit="节"
            trend={kpis?.course_trend}
            icon={CalendarCheck}
          />
          <KpiCard
            label="当前治疗中"
            value={kpis?.treating_count ?? "--"}
            unit="人"
            trend={kpis?.treating_trend}
            icon={Activity}
          />
          <KpiCard
            label="康复师出勤率"
            value={
              kpis
                ? `${Math.round(kpis.therapist_attendance_rate * 100)}`
                : "--"
            }
            unit="%"
            trend={kpis?.attendance_trend}
            icon={UserCheck}
          />
        </div>

        {/* 左栏: 患者分布环形图 */}
        <div className="col-span-12 lg:col-span-4">
          <DonutChart
            data={distribution ?? ([] as PatientDistribution[])}
            isLoading={distLoading}
          />
        </div>

        {/* 中栏: 治疗师课时柱状图 */}
        <div className="col-span-12 lg:col-span-4">
          <BarChart
            data={workload ?? ([] as TherapistWorkload[])}
            isLoading={wlLoading}
          />
        </div>

        {/* 右栏: 异常预警 */}
        <div className="col-span-12 lg:col-span-4">
          <AlertFeed
            alerts={alerts ?? ([] as AlertItem[])}
            isLoading={alertLoading}
          />
        </div>

        {/* 底部: 近7天趋势折线图 */}
        <LineChart
          data={trend ?? ([] as CourseTrend[])}
          isLoading={trendLoading}
        />
      </div>

      {/* 加载态占位（首次加载时） */}
      {kpiLoading && !kpis && (
        <p className="text-xs text-neutral-400 mt-4 text-center">
          正在加载看板数据…
        </p>
      )}
    </div>
  );
}
