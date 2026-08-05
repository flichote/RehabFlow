/**
 * TanStack Query key 统一管理
 */

export const queryKeys = {
  auth: {
    me: ["auth", "me"] as const,
  },
  schedule: {
    therapist: (date: string) => ["schedule", "therapist", date] as const,
    calendar: (from: string, to: string) =>
      ["schedule", "calendar", from, to] as const,
  },
  patients: {
    list: ["patients"] as const,
    detail: (id: string) => ["patients", id] as const,
    overview: (id: string) => ["patients", id, "overview"] as const,
  },
  dashboard: {
    kpis: ["dashboard", "kpis"] as const,
    distribution: ["dashboard", "patient-distribution"] as const,
    workload: (date: string) => ["dashboard", "workload", date] as const,
    trend: (days: number) => ["dashboard", "trend", days] as const,
  },
  alerts: {
    list: (status?: string) => ["alerts", status ?? "all"] as const,
  },
  scheduler: {
    resources: ["scheduler", "resources"] as const,
    pool: ["scheduler", "pool"] as const,
    courses: (from: string, to: string, group?: string) =>
      ["scheduler", "courses", from, to, group ?? "all"] as const,
  },
  courses: {
    detail: (id: string) => ["courses", id] as const,
  },
} as const;
