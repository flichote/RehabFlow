/**
 * Mock 数据 — 看板 & 患者360°
 * TODO: 后端就绪后删除此文件，改用 lib/api.ts 实际调用
 * 对接点: docs/api.md §8 看板 / §2 患者
 */

import type {
  DashboardKpis,
  PatientDistribution,
  TherapistWorkload,
  CourseTrend,
  AlertItem,
  PatientOverview,
  AssessmentRecord,
  AssessmentTrend,
} from "./types";

// === 看板 KPI ===

export const mockKpis: DashboardKpis = {
  in_hospital_patients: 48,
  today_courses: 32,
  treating_count: 6,
  therapist_attendance_rate: 0.875, // 87.5%
  // 趋势箭头: 与昨日比较
  patient_trend: "up",
  course_trend: "up",
  treating_trend: "down",
  attendance_trend: "up",
};

// === 患者分布（环形图）===

export const mockPatientDistribution: PatientDistribution[] = [
  { label: "病房", value: 22, color: "neutral" },
  { label: "PT", value: 12, color: "pt" },
  { label: "OT", value: 8, color: "ot" },
  { label: "ST", value: 6, color: "st" },
];

// === 治疗师今日课时（柱状图）===

export const mockTherapistWorkload: TherapistWorkload[] = [
  { therapist_id: "t-pt-1", therapist_name: "王康", course_count: 5, total_minutes: 225 },
  { therapist_id: "t-pt-2", therapist_name: "李复", course_count: 4, total_minutes: 180 },
  { therapist_id: "t-ot-1", therapist_name: "张疗", course_count: 3, total_minutes: 135 },
  { therapist_id: "t-st-1", therapist_name: "陈言", course_count: 2, total_minutes: 60 },
];

// === 近7天课程总量趋势（折线图）===

function daysAgoISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  d.setHours(0, 0, 0, 0);
  return d.toISOString().slice(0, 10);
}

export const mockCourseTrend: CourseTrend[] = [
  { date: daysAgoISO(6), label: "6天前", total: 28 },
  { date: daysAgoISO(5), label: "5天前", total: 31 },
  { date: daysAgoISO(4), label: "4天前", total: 25 },
  { date: daysAgoISO(3), label: "3天前", total: 30 },
  { date: daysAgoISO(2), label: "2天前", total: 35 },
  { date: daysAgoISO(1), label: "昨天", total: 29 },
  { date: daysAgoISO(0), label: "今天", total: 32 },
];

// === 异常预警 ===

export const mockAlerts: AlertItem[] = [
  {
    id: "a-1",
    type: "absent",
    title: "课程缺席",
    summary: "赵小明 未到 PT-1室（9:00 课程）",
    created_at: new Date(Date.now() - 5 * 60000).toISOString(),
    status: "open",
    patient_name: "赵小明",
  },
  {
    id: "a-2",
    type: "overtime",
    title: "治疗超时",
    summary: "钱大华 治疗中已超 30 分钟（PT-2室）",
    created_at: new Date(Date.now() - 15 * 60000).toISOString(),
    status: "open",
    patient_name: "钱大华",
  },
  {
    id: "a-3",
    type: "conflict",
    title: "排课冲突",
    summary: "孙丽 同时段被排入 OT-1室 和 ST-1室",
    created_at: new Date(Date.now() - 45 * 60000).toISOString(),
    status: "open",
    patient_name: "孙丽",
  },
  {
    id: "a-4",
    type: "abnormal",
    title: "课程异常",
    summary: "周强 11:00 课程超时未开始，已标记异常",
    created_at: new Date(Date.now() - 90 * 60000).toISOString(),
    status: "resolved",
    patient_name: "周强",
  },
  {
    id: "a-5",
    type: "location",
    title: "位置异常",
    summary: "吴敏 治疗中但位置显示在病房",
    created_at: new Date(Date.now() - 120 * 60000).toISOString(),
    status: "resolved",
    patient_name: "吴敏",
  },
];

// === 患者概览 360° ===

export const mockPatientOverview: PatientOverview = {
  patient: {
    id: "p-1",
    name: "赵小明",
    age: 62,
    gender: "男",
    diagnosis: "脑卒中后偏瘫",
    admission_date: "2026-07-20",
    attending_doctor: "刘主任",
    primary_therapist: "王康",
    bed_no: "302-3",
  },
  location: {
    current_location: "PT大厅2号床",
    status: "treating",
    updated_at: new Date(Date.now() - 3 * 60000).toISOString(),
  },
  plan_timeline: [
    { course_id: "c-1", type: "PT", start_at: todayAt(9, 0), end_at: todayAt(9, 45), status: "completed", therapist_name: "王康", room_name: "PT-1室" },
    { course_id: "c-6", type: "PT", start_at: todayAt(14, 0), end_at: todayAt(14, 45), status: "scheduled", therapist_name: "王康", room_name: "PT-1室" },
    { course_id: "c-y1", type: "OT", start_at: todayAt(16, 0), end_at: todayAt(16, 30), status: "absent", therapist_name: "张疗", room_name: "OT-1室" },
  ],
  week_calendar: [
    { date: daysAgoISO(6), weekday: "周一", courses: 2 },
    { date: daysAgoISO(5), weekday: "周二", courses: 3 },
    { date: daysAgoISO(4), weekday: "周三", courses: 2 },
    { date: daysAgoISO(3), weekday: "周四", courses: 1 },
    { date: daysAgoISO(2), weekday: "周五", courses: 3 },
    { date: daysAgoISO(1), weekday: "周六", courses: 0 },
    { date: daysAgoISO(0), weekday: "周日", courses: 3 },
  ],
};

// === 评估记录 ===

export const mockAssessments: AssessmentRecord[] = [
  { id: "as-1", type: "FM", type_label: "Fugl-Meyer", score: 45, max_score: 100, assessed_at: "2026-07-25", assessor: "王康" },
  { id: "as-2", type: "FM", type_label: "Fugl-Meyer", score: 52, max_score: 100, assessed_at: "2026-08-01", assessor: "王康" },
  { id: "as-3", type: "BI", type_label: "Barthel 指数", score: 40, max_score: 100, assessed_at: "2026-07-25", assessor: "张疗" },
  { id: "as-4", type: "BI", type_label: "Barthel 指数", score: 55, max_score: 100, assessed_at: "2026-08-01", assessor: "张疗" },
];

export const mockAssessmentTrend: AssessmentTrend[] = [
  { date: "2026-07-20", fm_score: 38, bi_score: 30 },
  { date: "2026-07-25", fm_score: 45, bi_score: 40 },
  { date: "2026-08-01", fm_score: 52, bi_score: 55 },
  { date: "2026-08-05", fm_score: 58, bi_score: 62 },
];

// === 工具 ===

function todayAt(h: number, m: number): string {
  const d = new Date();
  d.setHours(h, m, 0, 0);
  return d.toISOString();
}

// === 模拟延迟 ===

export function mockDelay<T>(data: T, ms = 300): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
}
