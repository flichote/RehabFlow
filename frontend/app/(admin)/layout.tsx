import type { ReactNode } from "react";

/**
 * 管理端布局 — AdminShell
 * docs/pages.md §4.2: 排课日历/主任看板/治疗室管理/康复师管理/异常预警/审计日志
 * docs/pages.md §2.3: 排课日历页全宽（无 max-width），其余 max-w-[1400px]
 */

const NAV_ITEMS = [
  { href: "/admin/scheduler", label: "排课日历" },
  { href: "/admin/dashboard", label: "主任看板" },
  { href: "/admin/rooms", label: "治疗室管理" },
  { href: "/admin/therapists", label: "康复师管理" },
  { href: "/admin/alerts", label: "异常预警" },
  { href: "/admin/audit", label: "审计日志" },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="h-16 bg-white border-b border-neutral-200 flex items-center px-6 sticky top-0 z-30">
        <span className="text-lg font-bold text-primary-800">RehabFlow</span>
        <span className="ml-3 text-sm text-neutral-500">管理端</span>
      </header>

      <div className="flex flex-1">
        <aside className="w-60 bg-white border-r border-neutral-200 p-4 hidden lg:block shrink-0">
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="block px-3 py-2 rounded-md text-sm text-neutral-700 hover:bg-primary-50 hover:text-primary-700"
              >
                {item.label}
              </a>
            ))}
          </nav>
        </aside>

        {/* 排课日历页全宽；其余 max-w-[1400px] */}
        <main className="flex-1 bg-neutral-50 w-full">
          {children}
        </main>
      </div>
    </div>
  );
}
