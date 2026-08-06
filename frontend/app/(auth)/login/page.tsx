"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { authApi, getErrorMessage, type UserRole } from "@/lib/api";
import { ROLE_HOME } from "@/lib/permissions";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect");

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await authApi.login(username, password);

      // 存储 token 到 cookie（供 proxy.ts 与 api.ts 使用）
      document.cookie = `access_token=${encodeURIComponent(res.access_token)}; path=/; SameSite=Lax`;
      document.cookie = `refresh_token=${encodeURIComponent(res.refresh_token)}; path=/; SameSite=Lax`;

      // 获取用户信息以判断角色跳转
      const me = await authApi.me();
      const home = redirect ?? ROLE_HOME[me.role as UserRole];

      router.push(home);
    } catch (err) {
      // 显示后端返回的具体错误（如"用户名或密码错误"、手机号格式等）
      setError(getErrorMessage(err, "登录失败，请检查用户名和密码"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-neutral-900 mb-1">登录</h1>
      <p className="text-sm text-neutral-500 mb-6">
        登录以进入康复排课管理系统
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="username"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            用户名
          </label>
          <input
            id="username"
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            placeholder="请输入用户名"
          />
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            密码
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            placeholder="请输入密码"
          />
        </div>

        {error && (
          <p className="text-sm text-danger-500 bg-danger-500/10 rounded-md px-3 py-2">
            {error}
          </p>
        )}

        <div className="flex justify-end">
          <Link
            href="/forgot-password"
            className="text-xs text-primary-600 hover:text-primary-700"
          >
            忘记密码？
          </Link>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "登录中..." : "登录"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-neutral-500">
        还没有账号？
        <Link
          href="/register"
          className="text-primary-600 hover:text-primary-700 font-medium ml-1"
        >
          注册
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-12">
          <p className="text-sm text-neutral-500">加载中...</p>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
