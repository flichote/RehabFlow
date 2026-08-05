"use client";

/**
 * 患者 360° 视图 ★
 * docs/design/components.md §4.1 / docs/design/pages.md (doctor)/patients/[id]
 * 布局: 左信息栏 320px + 右 Tab 区（概览 / 评估记录）
 * TODO: 后端就绪后切换到 patientApi 实际调用
 */

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  User,
  Cake,
  Stethoscope,
  CalendarDays,
  HeartPulse,
  BedSingle,
  Phone,
  ChevronLeft,
} from "lucide-react";
import { PatientLocationCard } from "@/components/patient/PatientLocationCard";
import { PlanTimeline } from "@/components/patient/PlanTimeline";
import { WeekCalendar } from "@/components/patient/WeekCalendar";
import { queryKeys } from "@/lib/query-keys";
import {
  mockPatientOverview,
  mockAssessments,
  mockAssessmentTrend,
  mockDelay,
} from "@/lib/mock-dashboard";
import type { PatientOverview, AssessmentRecord, AssessmentTrend } from "@/lib/types";
import {
  CHART_COLORS,
  CHART_TICK_STYLE,
  CHART_TOOLTIP_STYLE,
  CHART_LEGEND_STYLE,
} from "@/lib/chart-tokens";
import {
  LineChart as RLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

export default function PatientDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const [tab, setTab] = useState<"overview" | "assessment">("overview");
  const [patientId, setPatientId] = useState<string>("");

  // Next.js 16: params 是 Promise
  useState(() => {
    params.then((p) => setPatientId(p.id));
  });

  // 患者 360° 聚合
  const { data: overview, isLoading } = useQuery({
    queryKey: queryKeys.patients.overview(patientId || "loading"),
    queryFn: () => mockDelay(mockPatientOverview),
    enabled: !!patientId,
  });

  // 评估记录
  const { data: assessments } = useQuery({
    queryKey: ["patients", patientId, "assessments"] as const,
    queryFn: () => mockDelay(mockAssessments as AssessmentRecord[]),
    enabled: !!patientId && tab === "assessment",
  });

  // 评估趋势
  const { data: assessmentTrend } = useQuery({
    queryKey: ["patients", patientId, "assessment-trend"] as const,
    queryFn: () => mockDelay(mockAssessmentTrend as AssessmentTrend[]),
    enabled: !!patientId && tab === "assessment",
  });

  if (isLoading || !overview) {
    return (
      <div className="p-6">
        <p className="text-sm text-neutral-400">加载中…</p>
      </div>
    );
  }

  const { patient, location, plan_timeline, week_calendar } = overview;

  return (
    <div className="flex h-full">
      {/* 左信息栏 320px */}
      <aside className="w-80 shrink-0 border-r border-neutral-200 bg-white p-4 space-y-4 overflow-y-auto">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 text-sm text-neutral-500 hover:text-primary-600"
        >
          <ChevronLeft size={16} />
          返回
        </button>

        {/* 基本信息卡 */}
        <div className="rounded-lg border border-neutral-200 shadow-card p-4">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-full bg-primary-100 flex items-center justify-center">
              <User size={24} className="text-primary-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-neutral-900">{patient.name}</h2>
              <p className="text-xs text-neutral-400">床号: {patient.bed_no}</p>
            </div>
          </div>
          <dl className="space-y-2 text-sm">
            <InfoRow icon={Cake} label="年龄" value={`${patient.age} 岁 / ${patient.gender}`} />
            <InfoRow icon={Stethoscope} label="诊断" value={patient.diagnosis} />
            <InfoRow icon={CalendarDays} label="入院日期" value={patient.admission_date} />
            <InfoRow icon={HeartPulse} label="主管医生" value={patient.attending_doctor} />
            <InfoRow icon={BedSingle} label="责任康复师" value={patient.primary_therapist} />
          </dl>
        </div>

        {/* 实时位置卡 */}
        <PatientLocationCard location={location} />

        {/* 快捷操作 */}
        <div className="space-y-2">
          <button className="w-full flex items-center justify-center gap-2 rounded-md border border-neutral-200 px-3 py-2 text-sm text-neutral-700 hover:bg-primary-50 hover:text-primary-700 transition-colors">
            <Phone size={14} />
            联系康复师
          </button>
        </div>
      </aside>

      {/* 右 Tab 区 */}
      <main className="flex-1 bg-neutral-50 overflow-y-auto">
        {/* Tab 头 */}
        <div className="border-b border-neutral-200 bg-white px-6">
          <div className="flex gap-6">
            <TabButton active={tab === "overview"} onClick={() => setTab("overview")}>
              概览
            </TabButton>
            <TabButton active={tab === "assessment"} onClick={() => setTab("assessment")}>
              评估记录
            </TabButton>
          </div>
        </div>

        {/* Tab 内容 */}
        <div className="p-6 space-y-4">
          {tab === "overview" && (
            <>
              <PlanTimeline items={plan_timeline} />
              <WeekCalendar days={week_calendar} />
            </>
          )}

          {tab === "assessment" && (
            <>
              {/* 评估记录列表 */}
              <div className="rounded-lg bg-white border border-neutral-200 shadow-card p-4">
                <h3 className="text-base font-semibold text-neutral-900 mb-4">评估记录</h3>
                {assessments && assessments.length > 0 ? (
                  <div className="space-y-3">
                    {assessments.map((a) => (
                      <div
                        key={a.id}
                        className="flex items-center justify-between rounded-md border border-neutral-100 p-3"
                      >
                        <div>
                          <span className="text-sm font-medium text-neutral-900">
                            {a.type_label}
                          </span>
                          <span className="ml-2 text-xs text-neutral-400">
                            {a.assessed_at} · {a.assessor}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-lg font-bold tabular-nums text-primary-700">
                            {a.score}
                          </span>
                          <span className="text-xs text-neutral-400">/{a.max_score}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-neutral-400 text-center py-6">暂无评估记录</p>
                )}
              </div>

              {/* 评估趋势折线图 */}
              {assessmentTrend && assessmentTrend.length > 0 && (
                <div className="rounded-lg bg-white border border-neutral-200 shadow-card p-4">
                  <h3 className="text-base font-semibold text-neutral-900 mb-4">评估趋势</h3>
                  <ResponsiveContainer width="100%" height={240}>
                    <RLineChart data={assessmentTrend} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.neutral200} />
                      <XAxis
                        dataKey="date"
                        tick={CHART_TICK_STYLE}
                        axisLine={{ stroke: CHART_COLORS.neutral200 }}
                        tickLine={false}
                      />
                      <YAxis
                        tick={CHART_TICK_STYLE}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                      <Legend
                        iconType="line"
                        iconSize={12}
                        wrapperStyle={CHART_LEGEND_STYLE}
                      />
                      <Line
                        type="monotone"
                        dataKey="fm_score"
                        name="Fugl-Meyer"
                        stroke={CHART_COLORS.pt}
                        strokeWidth={2}
                        dot={{ r: 4, fill: CHART_COLORS.pt }}
                      />
                      <Line
                        type="monotone"
                        dataKey="bi_score"
                        name="Barthel 指数"
                        stroke={CHART_COLORS.ot}
                        strokeWidth={2}
                        dot={{ r: 4, fill: CHART_COLORS.ot }}
                      />
                    </RLineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}

/** 信息行 */
function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof User;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-2">
      <Icon size={14} className="text-neutral-400 mt-0.5 shrink-0" />
      <span className="text-neutral-500 shrink-0">{label}</span>
      <span className="text-neutral-900 text-right ml-auto">{value}</span>
    </div>
  );
}

/** Tab 按钮 */
function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`py-3 text-sm font-medium border-b-2 transition-colors ${
        active
          ? "text-primary-600 border-primary-600"
          : "text-neutral-500 border-transparent hover:text-neutral-700"
      }`}
    >
      {children}
    </button>
  );
}
