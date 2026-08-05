import Link from "next/link";

/**
 * 落地页 — 品牌 + 登录入口
 */
export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-neutral-50">
      <div className="text-center max-w-md px-6">
        <h1 className="text-4xl font-bold text-primary-800 mb-3">RehabFlow</h1>
        <p className="text-neutral-500 mb-8">
          院内康复治疗排课与执行管理系统
        </p>

        <div className="flex flex-col gap-3">
          <Link
            href="/login"
            className="rounded-md bg-primary-600 px-6 py-3 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
          >
            登录
          </Link>
          <Link
            href="/register"
            className="rounded-md border border-primary-200 px-6 py-3 text-sm font-medium text-primary-700 hover:bg-primary-50 transition-colors"
          >
            注册新账号
          </Link>
        </div>
      </div>
    </div>
  );
}
