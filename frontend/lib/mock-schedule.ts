/**
 * Mock 数据 — 后端 API 未就绪时使用
 * TODO: 后端就绪后删除此文件，改用 lib/api.ts 实际调用
 */

import type {
  Course,
  CourseType,
  ResourceGroup,
  PoolPatient,
  TodayOverview,
  ScheduleTimelineItem,
  TherapistResource,
} from "./types";

// === 工具：生成 ISO 时间 ===

function dateAt(dayOffset: number, h: number, m: number): string {
  const d = new Date();
  d.setDate(d.getDate() + dayOffset);
  d.setHours(h, m, 0, 0);
  return d.toISOString();
}

// === 资源树 ===

export const mockResourceGroups: ResourceGroup[] = [
  {
    group: "PT",
    label: "物理治疗 (PT)",
    therapists: [
      { id: "t-pt-1", name: "王康", group: "PT", room_id: "r-pt-1", room_name: "PT-1室" },
      { id: "t-pt-2", name: "李复", group: "PT", room_id: "r-pt-2", room_name: "PT-2室" },
    ],
  },
  {
    group: "OT",
    label: "作业治疗 (OT)",
    therapists: [
      { id: "t-ot-1", name: "张疗", group: "OT", room_id: "r-ot-1", room_name: "OT-1室" },
    ],
  },
  {
    group: "ST",
    label: "言语治疗 (ST)",
    therapists: [
      { id: "t-st-1", name: "陈言", group: "ST", room_id: "r-st-1", room_name: "ST-1室" },
    ],
  },
];

export const mockAllTherapists: TherapistResource[] = mockResourceGroups.flatMap(
  (g) => g.therapists
);

// === 待排患者池 ===

export const mockPool: PoolPatient[] = [
  { id: "p-1", name: "赵小明", course_type: "PT", diagnosis: "脑卒中后偏瘫" },
  { id: "p-2", name: "钱大华", course_type: "PT", diagnosis: "骨折术后康复" },
  { id: "p-3", name: "孙丽", course_type: "OT", diagnosis: "手外伤后功能受限" },
  { id: "p-4", name: "周强", course_type: "ST", diagnosis: "失语症" },
  { id: "p-5", name: "吴敏", course_type: "PT", diagnosis: "脊髓损伤" },
  { id: "p-6", name: "郑好", course_type: "OT", diagnosis: "认知障碍" },
];

// === 课程列表（排课日历用，覆盖今日和未来几天）===

function makeCourse(
  id: string,
  patientName: string,
  therapistId: string,
  therapistName: string,
  roomId: string,
  roomName: string,
  type: CourseType,
  dayOffset: number,
  h: number,
  m: number,
  durationMin: number,
  status: Course["status"] = "scheduled"
): Course {
  const start = dateAt(dayOffset, h, m);
  const end = new Date(new Date(start).getTime() + durationMin * 60000).toISOString();
  return {
    id,
    patient_id: `p-${id}`,
    patient_name: patientName,
    therapist_id: therapistId,
    therapist_name: therapistName,
    room_id: roomId,
    room_name: roomName,
    course_type: type,
    status,
    start_at: start,
    end_at: end,
    actual_start_at: status === "completed" ? start : null,
    actual_end_at: status === "completed" ? end : null,
  };
}

export const mockCourses: Course[] = [
  // 今日
  makeCourse("c-1", "赵小明", "t-pt-1", "王康", "r-pt-1", "PT-1室", "PT", 0, 9, 0, 45, "completed"),
  makeCourse("c-2", "钱大华", "t-pt-1", "王康", "r-pt-1", "PT-1室", "PT", 0, 10, 0, 45),
  makeCourse("c-3", "吴敏", "t-pt-2", "李复", "r-pt-2", "PT-2室", "PT", 0, 9, 30, 60),
  makeCourse("c-4", "孙丽", "t-ot-1", "张疗", "r-ot-1", "OT-1室", "OT", 0, 14, 0, 45),
  makeCourse("c-5", "周强", "t-st-1", "陈言", "r-st-1", "ST-1室", "ST", 0, 11, 0, 30),
  // 明天
  makeCourse("c-6", "赵小明", "t-pt-1", "王康", "r-pt-1", "PT-1室", "PT", 1, 9, 0, 45),
  makeCourse("c-7", "郑好", "t-ot-1", "张疗", "r-ot-1", "OT-1室", "OT", 1, 10, 0, 45),
  makeCourse("c-8", "周强", "t-st-1", "陈言", "r-st-1", "ST-1室", "ST", 1, 14, 0, 30),
  // 后天
  makeCourse("c-9", "钱大华", "t-pt-2", "李复", "r-pt-2", "PT-2室", "PT", 2, 10, 30, 60),
  makeCourse("c-10", "孙丽", "t-ot-1", "张疗", "r-ot-1", "OT-1室", "OT", 2, 13, 0, 45),
];

// === 今日概览（康复师课表）===

export const mockTodayOverview: TodayOverview = {
  total_minutes: 270,
  completed_minutes: 45,
  remaining_minutes: 225,
  total_courses: 5,
  completed_courses: 1,
};

// === 康复师今日课表时间线 ===

export function mockTherapistSchedule(therapistId: string): ScheduleTimelineItem[] {
  // 模拟康复师 t-pt-1 的今日课程
  const todayCourses = mockCourses.filter(
    (c) =>
      c.therapist_id === therapistId &&
      new Date(c.start_at).toDateString() === new Date().toDateString()
  );

  if (todayCourses.length === 0) return [];

  const sorted = [...todayCourses].sort(
    (a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime()
  );

  const items: ScheduleTimelineItem[] = [];
  for (let i = 0; i < sorted.length; i++) {
    items.push({ kind: "course", course: sorted[i] });
    if (i < sorted.length - 1) {
      const gapStart = new Date(sorted[i].end_at);
      const gapEnd = new Date(sorted[i + 1].start_at);
      const gapMin = Math.round((gapEnd.getTime() - gapStart.getTime()) / 60000);
      if (gapMin >= 15) {
        items.push({
          kind: "free",
          free: {
            start_at: gapStart.toISOString(),
            end_at: gapEnd.toISOString(),
            duration_minutes: gapMin,
          },
        });
      }
    }
  }
  return items;
}

// === 模拟延迟 ===

export function mockDelay<T>(data: T, ms = 300): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
}
