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
