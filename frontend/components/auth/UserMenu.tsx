"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { KeyRound, LogOut, User } from "lucide-react";
import { authApi } from "@/lib/api";

/**
 * 顶栏用户菜单（4 个角色布局共用）
 * 显示当前用户名 + 退出登录按钮。
 * 退出：清空 token cookie → 跳转登录页（proxy.ts 守卫会自动拦截受保护路由）。
 */
export default function UserMenu() {
  const router = useRouter();
  const [username, setUsername] = useState<string>("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    authApi
      .me()
      .then((user) => setUsername(user.username))
      .catch(() => setUsername(""));
  }, []);

  const handleLogout = async () => {
    try {
      // 后端撤销 refresh token（尽力而为，失败不阻塞本地退出）
      const refreshToken = document.cookie
        .match(/(?:^|;\s*)refresh_token=([^;]+)/)?.[1];
      if (refreshToken) {
        await authApi.logout(refreshToken).catch(() => undefined);
      }
    } finally {
      // 清空 cookie（expires 过去时间）
      ["access_token", "refresh_token"].forEach((name) => {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
      });
      router.push("/login");
      router.refresh();
    }
  };

  return (
    <div className="relative ml-auto">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-md px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-100"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-100 text-primary-700">
          <User className="h-4 w-4" />
        </span>
        <span className="hidden sm:inline max-w-[120px] truncate">
          {username || "…"}
        </span>
      </button>

      {open && (
        <>
          {/* 点击外部关闭 */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <div
            role="menu"
            className="absolute right-0 z-50 mt-2 w-44 rounded-md border border-neutral-200 bg-white py-1 shadow-lg"
          >
            <div className="px-3 py-2 text-xs text-neutral-500 border-b border-neutral-100">
              {username || "未登录"}
            </div>
            <Link
              href="/account/password"
              role="menuitem"
              onClick={() => setOpen(false)}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50"
            >
              <KeyRound className="h-4 w-4" />
              修改密码
            </Link>
            <button
              type="button"
              role="menuitem"
              onClick={handleLogout}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              <LogOut className="h-4 w-4" />
              退出登录
            </button>
          </div>
        </>
      )}
    </div>
  );
}
