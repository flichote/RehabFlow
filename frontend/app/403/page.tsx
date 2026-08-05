import Link from "next/link";

export default function ForbiddenPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-neutral-50">
      <div className="text-center">
        <p className="text-6xl font-bold text-primary-600 mb-4">403</p>
        <h1 className="text-xl font-semibold text-neutral-900 mb-2">
          无权限访问
        </h1>
        <p className="text-sm text-neutral-500 mb-6">
          您的角色无权访问此页面
        </p>
        <Link
          href="/login"
          className="rounded-md bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
        >
          返回登录
        </Link>
      </div>
    </div>
  );
}
