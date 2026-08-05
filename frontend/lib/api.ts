/**
 * API fetch 封装 — JWT 注入 + 错误处理
 * docs/api.md 为接口契约，统一前缀 /api/v1
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

/** 读取 access token（浏览器端从 cookie 获取） */
function getAccessToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)access_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

/** API 错误类型 */
export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown, message?: string) {
    super(message ?? `API Error ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** 核心 fetch 封装 */
async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) ?? {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let detail: unknown;
    try {
      detail = await res.json();
    } catch {
      detail = res.statusText;
    }
    throw new ApiError(res.status, detail);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { ...init, method: "GET" }),

  post: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, {
      ...init,
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),

  put: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, {
      ...init,
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { ...init, method: "DELETE" }),
};

// === 类型定义（与后端 API 对齐，docs/api.md） ===

export type UserRole = "patient" | "therapist" | "doctor" | "admin";

export interface AuthUser {
  id: string;
  username: string;
  full_name: string;
  role: UserRole;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
  full_name: string;
  role: UserRole;
  phone?: string;
}

// === Auth API ===

export const authApi = {
  login: (username: string, password: string) =>
    api.post<LoginResponse>("/auth/login", { username, password }),

  register: (payload: RegisterPayload) =>
    api.post<{ id: string; username: string; role: UserRole }>(
      "/auth/register",
      payload
    ),

  me: () => api.get<AuthUser>("/auth/me"),

  refresh: (refreshToken: string) =>
    api.post<LoginResponse>("/auth/refresh", { refresh_token: refreshToken }),
};

// === 类型 re-export ===
export type {
  CourseType,
  CourseStatus,
  PatientStatus,
  Room,
  TherapistResource,
  ResourceGroup,
  Course,
  PoolPatient,
  ConflictDetail,
  ConflictResponse,
  TodayOverview,
  FreeSlot,
  ScheduleTimelineItem,
  CreateCoursePayload,
  UpdateCoursePayload,
  // 看板类型
  DashboardKpis,
  PatientDistribution,
  TherapistWorkload,
  CourseTrend,
  AlertType,
  AlertItem,
  // 患者概览类型
  PatientInfo,
  PatientLocation,
  PlanTimelineItem,
  WeekCalendarDay,
  PatientOverview,
  AssessmentRecord,
  AssessmentTrend,
} from "./types";

// === Schedule API ===
// TODO: 后端就绪后取消注释，切换到真实 API 调用

export const scheduleApi = {
  // GET /courses?from&to&therapist_id&group&room_id
  // list: (params: Record<string, string>) =>
  //   api.get<Course[]>("/courses?" + new URLSearchParams(params)),

  // POST /courses — 创建课程（冲突 → 409 + ConflictResponse）
  // create: (payload: CreateCoursePayload) =>
  //   api.post<Course>("/courses", payload),

  // GET /courses/{id}
  // detail: (id: string) => api.get<Course>(`/courses/${id}`),

  // PUT /courses/{id} — 修改时间
  // update: (id: string, payload: UpdateCoursePayload) =>
  //   api.put<Course>(`/courses/${id}`, payload),

  // DELETE /courses/{id} — 取消课程
  // cancel: (id: string) => api.delete<void>(`/courses/${id}`),

  // POST /courses/{id}/force — 强制替换
  // force: (id: string) => api.post<Course>(`/courses/${id}/force`),

  // GET /scheduler/resources — 资源树
  // resources: () => api.get<ResourceGroup[]>("/scheduler/resources"),

  // GET /scheduler/pool — 待排患者池
  // pool: () => api.get<PoolPatient[]>("/scheduler/pool"),
};

// === Course Execution API ===

export const courseApi = {
  // POST /courses/{id}/start — 开始上课
  // start: (id: string) => api.post<Course>(`/courses/${id}/start`),

  // POST /courses/{id}/finish — 结束上课
  // finish: (id: string) => api.post<Course>(`/courses/${id}/finish`),

  // POST /courses/{id}/remind — 一键提醒
  // remind: (id: string) => api.post<void>(`/courses/${id}/remind`),

  // GET /therapist/schedule?date= — 我的课表
  // schedule: (date: string) =>
  //   api.get<{ overview: TodayOverview; timeline: ScheduleTimelineItem[] }>(
  //     `/therapist/schedule?date=${date}`
  //   ),
};

// === Dashboard API (docs/api.md §8) ===
// TODO: 后端就绪后取消注释，切换到真实 API 调用

export const dashboardApi = {
  // GET /dashboard/kpis
  // kpis: () => api.get<DashboardKpis>("/dashboard/kpis"),

  // GET /dashboard/patient-distribution
  // distribution: () =>
  //   api.get<PatientDistribution[]>("/dashboard/patient-distribution"),

  // GET /dashboard/therapist-workload?date=
  // workload: (date: string) =>
  //   api.get<TherapistWorkload[]>(`/dashboard/therapist-workload?date=${date}`),

  // GET /dashboard/course-trend?days=7
  // trend: (days: number) =>
  //   api.get<CourseTrend[]>(`/dashboard/course-trend?days=${days}`),
};

// === Patient API (docs/api.md §2) ===
// TODO: 后端就绪后取消注释，切换到真实 API 调用

export const patientApi = {
  // GET /patients/{id}/overview — 患者 360° 聚合
  // overview: (id: string) =>
  //   api.get<PatientOverview>(`/patients/${id}/overview`),

  // GET /patients/{id}/assessments
  // assessments: (id: string) =>
  //   api.get<AssessmentRecord[]>(`/patients/${id}/assessments`),

  // GET /patients/{id}/assessments/trend?type=FM
  // assessmentTrend: (id: string, type: string) =>
  //   api.get<AssessmentTrend[]>(
  //     `/patients/${id}/assessments/trend?type=${type}`
  //   ),
};

// === Alerts API (docs/api.md §7) ===
// TODO: 后端就绪后取消注释，切换到真实 API 调用

export const alertsApi = {
  // GET /alerts?status=open
  // list: (status?: string) =>
  //   api.get<AlertItem[]>(`/alerts${status ? `?status=${status}` : ""}`),
};
