import type { ReactNode } from "react";

/**
 * 患者端布局 — AppShell（侧边栏 + 顶栏）
 * docs/pages.md §2.2: 桌面端左侧 Sidebar 240px + 右侧主内容区
 */

export default function PatientLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Topbar */}
      <header className="h-16 bg-white border-b border-neutral-200 flex items-center px-6 sticky top-0 z-30">
        <span className="text-lg font-bold text-primary-800">RehabFlow</span>
        <span className="ml-3 text-sm text-neutral-500">患者端</span>
      </header>

      <div className="flex flex-1">
        {/* Sidebar */}
        <aside className="w-60 bg-white border-r border-neutral-200 p-4 hidden lg:block">
          <nav className="space-y-1">
            <a
              href="/patient"
              className="block px-3 py-2 rounded-md text-sm text-neutral-700 hover:bg-primary-50 hover:text-primary-700"
            >
              首页
            </a>
            <a
              href="/patient/schedule"
              className="block px-3 py-2 rounded-md text-sm text-neutral-700 hover:bg-primary-50 hover:text-primary-700"
            >
              我的课程
            </a>
            <a
              href="/patient/profile"
              className="block px-3 py-2 rounded-md text-sm text-neutral-700 hover:bg-primary-50 hover:text-primary-700"
            >
              个人档案
            </a>
          </nav>
        </aside>

        {/* 主内容区 */}
        <main className="flex-1 bg-neutral-50 p-6">{children}</main>
      </div>
    </div>
  );
}
