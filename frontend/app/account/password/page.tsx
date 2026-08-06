"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { KeyRound } from "lucide-react";
import { authApi, getErrorMessage } from "@/lib/api";

/**
 * 修改密码页（登录后，/account/password，所有角色通用）
 * 流行方式：校验原密码 → 设置新密码 → 强制重新登录
 */
export default function ChangePasswordPage() {
  const router = useRouter();

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setError(null);
    setSuccess(null);
    if (newPassword.length < 6) {
      setError("新密码至少 6 位");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("两次输入的新密码不一致");
      return;
    }
    setLoading(true);
    try {
      await authApi.changePassword(oldPassword, newPassword);
      setSuccess("密码修改成功，请重新登录");
      // 清空 token cookie（后端已撤销 refresh token）
      ["access_token", "refresh_token"].forEach((name) => {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
      });
      setTimeout(() => router.push("/login"), 1200);
    } catch (err) {
      setError(getErrorMessage(err, "密码修改失败，请稍后重试"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary-100 text-primary-700">
            <KeyRound className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold text-neutral-900">修改密码</h1>
          <p className="mt-1 text-sm text-neutral-500">
            验证原密码后设置新密码，修改成功需重新登录
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label
              htmlFor="old-password"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              原密码
            </label>
            <input
              id="old-password"
              type="password"
              required
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="请输入当前密码"
            />
          </div>

          <div>
            <label
              htmlFor="new-password"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              新密码
            </label>
            <input
              id="new-password"
              type="password"
              required
              minLength={6}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="至少 6 位"
            />
          </div>

          <div>
            <label
              htmlFor="confirm-password"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              确认新密码
            </label>
            <input
              id="confirm-password"
              type="password"
              required
              minLength={6}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="再次输入新密码"
            />
          </div>

          {error && (
            <p className="text-sm text-danger-500 bg-danger-500/10 rounded-md px-3 py-2">
              {error}
            </p>
          )}
          {success && (
            <p className="text-sm text-success-600 bg-success-600/10 rounded-md px-3 py-2">
              {success}
            </p>
          )}

          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="w-full rounded-md bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "提交中..." : "确认修改"}
          </button>

          <p className="text-center text-sm text-neutral-500">
            <Link
              href="/"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              返回首页
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
