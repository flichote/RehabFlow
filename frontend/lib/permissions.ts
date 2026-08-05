/**
 * 前端角色/权限工具
 * docs/pages.md 路由守卫规则参照
 */

import type { UserRole } from "./api";

/** 角色中文标签 */
export const ROLE_LABELS: Record<UserRole, string> = {
  patient: "患者",
  therapist: "康复师",
  doctor: "医生",
  admin: "管理员",
};

/** 角色默认落地页（登录后跳转） */
export const ROLE_HOME: Record<UserRole, string> = {
  patient: "/patient",
  therapist: "/therapist/schedule",
  doctor: "/doctor/patients",
  admin: "/admin/scheduler",
};

/** 角色路由前缀映射 */
export const ROLE_PREFIX: Record<UserRole, string> = {
  patient: "/patient",
  therapist: "/therapist",
  doctor: "/doctor",
  admin: "/admin",
};

/**
 * 校验用户角色是否可访问目标路径
 * @param role 用户角色
 * @param pathname 请求路径
 * @returns 是否允许访问
 */
export function canAccess(role: UserRole, pathname: string): boolean {
  const prefix = ROLE_PREFIX[role];
  // 精确匹配前缀或前缀 + /
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

/** 所有需要认证的路由前缀 */
export const PROTECTED_PREFIXES = ["/patient", "/therapist", "/doctor", "/admin"];

/** 判断路径是否需要认证 */
export function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
}

/**
 * 简易 JWT payload 解码（不验签，仅读 payload）
 * proxy.ts 中用于乐观校验，真实鉴权由后端完成
 */
export function decodeJwtPayload(token: string): { role?: string; exp?: number } | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}
