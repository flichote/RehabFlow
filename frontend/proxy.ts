import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { decodeJwtPayload, isProtectedPath, canAccess } from "@/lib/permissions";
import type { UserRole } from "@/lib/api";

/**
 * RehabFlow 路由守卫 — proxy.ts (Next.js 16 middleware 正式名)
 * docs/pages.md: 校验 JWT + 角色；未登录 → /login；角色不匹配 → /403
 *
 * 注意：proxy 是乐观检查（optimistic check），真实鉴权由后端 API 完成。
 * proxy 读取 cookie 中的 access_token，解码 JWT payload 获取角色。
 */

// 角色首页映射（与 lib/permissions.ts ROLE_HOME 一致）
const ROLE_HOME: Record<string, string> = {
  patient: "/patient",
  therapist: "/therapist/schedule",
  doctor: "/doctor/patients",
  admin: "/admin/scheduler",
};

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 静态资源 / API 路由跳过
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // 登录/注册/忘记密码/错误页不需要守卫
  const publicPaths = [
    "/login",
    "/register",
    "/forgot-password",
    "/403",
    "/404",
    "/500",
  ];
  if (publicPaths.includes(pathname) || pathname === "/") {
    return NextResponse.next();
  }

  // 检查是否需要认证
  if (!isProtectedPath(pathname)) {
    return NextResponse.next();
  }

  // 读取 access_token cookie
  const token = request.cookies.get("access_token")?.value;

  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // 解码 JWT payload（乐观校验，不验签）
  const payload = decodeJwtPayload(token);

  // token 过期检查
  if (payload?.exp && Date.now() >= payload.exp * 1000) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    const res = NextResponse.redirect(loginUrl);
    res.cookies.delete("access_token");
    res.cookies.delete("refresh_token");
    return res;
  }

  const role = payload?.role as string | undefined;

  if (!role) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  // 角色与路径匹配校验
  if (!canAccess(role as UserRole, pathname)) {
    const forbiddenUrl = new URL("/403", request.url);
    return NextResponse.redirect(forbiddenUrl);
  }

  // ROLE_HOME 保留用于未来扩展（登录后跳转已在 login page 处理）
  void ROLE_HOME;

  return NextResponse.next();
}

export const config = {
  /**
   * 匹配所有路径，排除静态资源与 API。
   * proxy 内部再做细粒度判断。
   */
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
