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
