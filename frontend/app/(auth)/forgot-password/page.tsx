"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { KeyRound } from "lucide-react";
import { authApi, getErrorMessage } from "@/lib/api";

/**
 * 忘记密码页（公开，/forgot-password）
 * 流行方式：手机号 + 短信验证码 两步重置
 * ① 输入手机号 → 获取验证码（院内系统无短信通道：验证码显示在下方提示中）
 * ② 验证码 + 新密码 → 重置成功 → 跳转登录
 */
export default function ForgotPasswordPage() {
  const router = useRouter();

  const [step, setStep] = useState<1 | 2>(1);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);

  const sendCode = async () => {
    setError(null);
    if (!/^1\d{10}$/.test(phone)) {
      setError("请输入 11 位手机号（1 开头）");
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.requestPasswordReset(phone);
      setDevCode(res.dev_code ?? null);
      setStep(2);
      setCountdown(300);
      // 倒计时提示（纯展示，不阻塞）
      const t = setInterval(() => {
        setCountdown((c) => {
          if (c <= 1) {
            clearInterval(t);
            return 0;
          }
          return c - 1;
        });
      }, 1000);
    } catch (err) {
      setError(getErrorMessage(err, "验证码发送失败，请稍后重试"));
    } finally {
      setLoading(false);
    }
  };

  const resetPassword = async () => {
    setError(null);
    if (newPassword.length < 6) {
      setError("新密码至少 6 位");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }
    setLoading(true);
    try {
      await authApi.confirmPasswordReset(phone, code, newPassword);
      router.push("/login?reset=1");
    } catch (err) {
      setError(getErrorMessage(err, "密码重置失败，请稍后重试"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4">
      <div className="w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary-100 text-primary-700">
            <KeyRound className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold text-neutral-900">找回密码</h1>
          <p className="mt-1 text-sm text-neutral-500">
            {step === 1
              ? "输入注册手机号，获取验证码"
              : "输入验证码并设置新密码"}
          </p>
        </div>

        {step === 1 ? (
          <div className="space-y-4">
            <div>
              <label
                htmlFor="phone"
                className="block text-sm font-medium text-neutral-700 mb-1"
              >
                注册手机号
              </label>
              <input
                id="phone"
                type="tel"
                required
                pattern="1[0-9]{10}"
                title="请输入 11 位手机号（1 开头）"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="请输入 11 位手机号"
              />
            </div>

            {error && (
              <p className="text-sm text-danger-500 bg-danger-500/10 rounded-md px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="button"
              onClick={sendCode}
              disabled={loading}
              className="w-full rounded-md bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "发送中..." : "获取验证码"}
            </button>

            <p className="text-center text-sm text-neutral-500">
              想起密码了？
              <Link
                href="/login"
                className="text-primary-600 hover:text-primary-700 font-medium ml-1"
              >
                返回登录
              </Link>
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {devCode && (
              <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-700">
                📱 院内系统暂无短信通道，本次验证码：{" "}
                <span className="font-mono font-bold tracking-widest">{devCode}</span>
                <span className="block mt-1 text-xs text-amber-600">
                  （5 分钟内有效；生产环境将改为短信下发）
                </span>
              </div>
            )}

            <div>
              <label
                htmlFor="code"
                className="block text-sm font-medium text-neutral-700 mb-1"
              >
                验证码
              </label>
              <input
                id="code"
                type="text"
                required
                pattern="[0-9]{6}"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="6 位数字验证码"
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

            <button
              type="button"
              onClick={resetPassword}
              disabled={loading}
              className="w-full rounded-md bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "提交中..." : "重置密码"}
            </button>

            {countdown > 0 && (
              <p className="text-center text-xs text-neutral-400">
                验证码 {countdown} 秒内有效
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
