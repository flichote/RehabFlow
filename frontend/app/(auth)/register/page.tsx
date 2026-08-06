"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Activity, Stethoscope, HeartPulse, ShieldCheck } from "lucide-react";
import { authApi, ApiError, type UserRole } from "@/lib/api";
import { ROLE_LABELS, ROLE_HOME } from "@/lib/permissions";

const ROLE_OPTIONS: {
  value: UserRole;
  label: string;
  desc: string;
  icon: typeof Activity;
}[] = [
  {
    value: "patient",
    label: "患者",
    desc: "查看课程安排与提醒",
    icon: HeartPulse,
  },
  {
    value: "therapist",
    label: "康复师",
    desc: "管理课表与课程执行",
    icon: Activity,
  },
  {
    value: "doctor",
    label: "医生",
    desc: "查看患者与评估记录",
    icon: Stethoscope,
  },
  {
    value: "admin",
    label: "管理员",
    desc: "排课调度与系统管理",
    icon: ShieldCheck,
  },
];

export default function RegisterPage() {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState<UserRole>("patient");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await authApi.register({
        username,
        password,
        display_name: fullName,
        role,
        phone: phone || undefined,
      });

      // 注册成功后跳转登录页
      router.push("/login?registered=1");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError("用户名已存在");
        } else {
          setError(`注册失败：${err.status}`);
        }
      } else {
        // 后端未就绪时的降级提示
        setError("注册服务暂不可用，请稍后重试");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-neutral-900 mb-1">注册</h1>
      <p className="text-sm text-neutral-500 mb-6">创建康复排课管理系统账号</p>

      {/* 角色选择卡片 */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          选择角色
        </label>
        <div className="grid grid-cols-2 gap-3">
          {ROLE_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const selected = role === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setRole(opt.value)}
                className={`flex flex-col items-start rounded-md border p-3 text-left transition-colors ${
                  selected
                    ? "border-primary-600 bg-primary-50 ring-1 ring-primary-600"
                    : "border-neutral-200 hover:border-primary-200 hover:bg-primary-50/50"
                }`}
              >
                <Icon
                  className={`mb-2 h-5 w-5 ${selected ? "text-primary-600" : "text-neutral-500"}`}
                />
                <span
                  className={`text-sm font-medium ${selected ? "text-primary-700" : "text-neutral-700"}`}
                >
                  {opt.label}
                </span>
                <span className="text-xs text-neutral-500 mt-0.5">
                  {opt.desc}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="reg-username"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            用户名
          </label>
          <input
            id="reg-username"
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
            htmlFor="reg-fullname"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            姓名
          </label>
          <input
            id="reg-fullname"
            type="text"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            placeholder="请输入真实姓名"
          />
        </div>

        <div>
          <label
            htmlFor="reg-phone"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            手机号 <span className="text-neutral-400">（选填）</span>
          </label>
          <input
            id="reg-phone"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            placeholder="请输入手机号"
          />
        </div>

        <div>
          <label
            htmlFor="reg-password"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            密码
          </label>
          <input
            id="reg-password"
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

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "注册中..." : `注册为${ROLE_LABELS[role]}`}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-neutral-500">
        已有账号？
        <Link
          href="/login"
          className="text-primary-600 hover:text-primary-700 font-medium ml-1"
        >
          登录
        </Link>
      </p>

      <p className="mt-2 text-center text-xs text-neutral-400">
        注册成功后将跳转至{ROLE_HOME[role]}页
      </p>
    </div>
  );
}
