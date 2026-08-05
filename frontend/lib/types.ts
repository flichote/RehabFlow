/**
 * 共享类型定义 — 与后端 API 对齐（docs/api.md）
 */

/** 课程类型 */
export type CourseType = "PT" | "OT" | "ST";

/** 课程状态 — docs/flows.md 状态流转速查 */
export type CourseStatus =
  | "scheduled"   // 待执行
  | "reminded"    // 提醒已发
  | "ongoing"     // 进行中
  | "completed"   // 已完成
  | "absent"      // 缺席
  | "abnormal";   // 异常

/** 患者状态 */
export type PatientStatus =
  | "ward"       // 在病房
  | "en_route"   // 前往途中
  | "treating"   // 治疗中
  | "paused"     // 暂停
  | "absent";    // 缺席

/** 治疗室 */
export interface Room {
  id: string;
  name: string;
  group: CourseType;
}

/** 康复师资源 */
export interface TherapistResource {
  id: string;
  name: string;
  group: CourseType;
  room_id: string;
  room_name: string;
}

/** 资源树分组 */
export interface ResourceGroup {
  group: CourseType;
  label: string;
  therapists: TherapistResource[];
}

/** 课程 */
export interface Course {
  id: string;
  patient_id: string;
  patient_name: string;
  therapist_id: string;
  therapist_name: string;
  room_id: string;
  room_name: string;
  course_type: CourseType;
  status: CourseStatus;
  start_at: string;   // ISO8601
  end_at: string;     // ISO8601
  actual_start_at?: string | null;
  actual_end_at?: string | null;
  session_note?: string | null;
}

/** 待排患者池条目 */
export interface PoolPatient {
  id: string;
  name: string;
  course_type: CourseType;
  diagnosis: string;
}

/** 冲突明细 */
export interface ConflictDetail {
  type: "patient" | "therapist";
  course_id: string;
  patient_name: string;
  therapist_name: string;
  start_at: string;
  end_at: string;
  course_type: CourseType;
}

/** 409 冲突响应体 */
export interface ConflictResponse {
  detail: string;
  conflicts: ConflictDetail[];
}

/** 今日概览 */
export interface TodayOverview {
  total_minutes: number;
  completed_minutes: number;
  remaining_minutes: number;
  total_courses: number;
  completed_courses: number;
}

/** 空闲时段 */
export interface FreeSlot {
  start_at: string;
  end_at: string;
  duration_minutes: number;
}

/** 课表时间线索目（含空闲时段） */
export interface ScheduleTimelineItem {
  kind: "course" | "free";
  course?: Course;
  free?: FreeSlot;
}

/** 创建课程 payload */
export interface CreateCoursePayload {
  patient_id: string;
  therapist_id: string;
  room_id: string;
  course_type: CourseType;
  start_at: string;
  end_at: string;
}

/** 修改课程 payload */
export interface UpdateCoursePayload {
  start_at?: string;
  end_at?: string;
  room_id?: string;
  therapist_id?: string;
}

// === 看板类型 (docs/api.md §8) ===

/** KPI 趋势方向 */
export type TrendDirection = "up" | "down" | "flat";

/** 看板 KPI */
export interface DashboardKpis {
  in_hospital_patients: number;
  today_courses: number;
  treating_count: number;
  therapist_attendance_rate: number; // 0~1
  patient_trend: TrendDirection;
  course_trend: TrendDirection;
  treating_trend: TrendDirection;
  attendance_trend: TrendDirection;
}

/** 患者分布（环形图） */
export interface PatientDistribution {
  label: string;
  value: number;
  color: "pt" | "ot" | "st" | "neutral";
}

/** 治疗师今日课时（柱状图） */
export interface TherapistWorkload {
  therapist_id: string;
  therapist_name: string;
  course_count: number;
  total_minutes: number;
}

/** 近 N 天课程总量（折线图） */
export interface CourseTrend {
  date: string;
  label: string;
  total: number;
}

/** 预警类型 */
export type AlertType = "absent" | "overtime" | "conflict" | "abnormal" | "location";

/** 预警条目 */
export interface AlertItem {
  id: string;
  type: AlertType;
  title: string;
  summary: string;
  created_at: string;
  status: "open" | "resolved";
  patient_name?: string;
}

// === 患者概览 360° 类型 (docs/api.md §2) ===

/** 患者基本信息 */
export interface PatientInfo {
  id: string;
  name: string;
  age: number;
  gender: string;
  diagnosis: string;
  admission_date: string;
  attending_doctor: string;
  primary_therapist: string;
  bed_no: string;
}

/** 患者位置信息 */
export interface PatientLocation {
  current_location: string;
  status: PatientStatus;
  updated_at: string;
}

/** 课程计划时间轴条目 */
export interface PlanTimelineItem {
  course_id: string;
  type: CourseType;
  start_at: string;
  end_at: string;
  status: CourseStatus;
  therapist_name: string;
  room_name: string;
}

/** 周历每日统计 */
export interface WeekCalendarDay {
  date: string;
  weekday: string;
  courses: number;
}

/** 患者 360° 聚合 */
export interface PatientOverview {
  patient: PatientInfo;
  location: PatientLocation;
  plan_timeline: PlanTimelineItem[];
  week_calendar: WeekCalendarDay[];
}

/** 评估记录 */
export interface AssessmentRecord {
  id: string;
  type: string;
  type_label: string;
  score: number;
  max_score: number;
  assessed_at: string;
  assessor: string;
}

/** 评估趋势数据 */
export interface AssessmentTrend {
  date: string;
  fm_score: number;
  bi_score: number;
}
