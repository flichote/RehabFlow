import type { ReactNode } from "react";

/**
 * 认证布局 — 居中卡片布局
 * docs/pages.md §2.1: 左半品牌区（桌面端）/ 顶部品牌（移动端），右半表单区
 */

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex">
      {/* 品牌区 — 桌面端左半 */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary-600 items-center justify-center">
        <div className="text-center text-white px-12">
          <h1 className="text-4xl font-bold mb-4">RehabFlow</h1>
          <p className="text-primary-100 text-lg">
            院内康复治疗排课与执行管理系统
          </p>
          <div className="mt-8 flex justify-center gap-6 text-sm text-primary-200">
            <span>排课调度</span>
            <span>·</span>
            <span>课程执行</span>
            <span>·</span>
            <span>实时看板</span>
          </div>
        </div>
      </div>

      {/* 表单区 */}
      <div className="flex-1 flex items-center justify-center bg-neutral-50 px-4 py-12">
        <div className="w-full max-w-[440px] rounded-lg shadow-lg bg-white p-8">
          {children}
        </div>
      </div>
    </div>
  );
}
