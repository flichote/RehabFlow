import type { ReactNode } from "react";

/**
 * 康复师端布局 — AppShell
 * docs/pages.md §4.1: 我的课表/我的患者/评估记录/消息/个人档案
 */

const NAV_ITEMS = [
  { href: "/therapist/schedule", label: "我的课表" },
  { href: "/therapist/patients", label: "我的患者" },
  { href: "/therapist/assessments", label: "评估记录" },
  { href: "/therapist/messages", label: "消息" },
  { href: "/therapist/profile", label: "个人档案" },
];

export default function TherapistLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="h-16 bg-white border-b border-neutral-200 flex items-center px-6 sticky top-0 z-30">
        <span className="text-lg font-bold text-primary-800">RehabFlow</span>
        <span className="ml-3 text-sm text-neutral-500">康复师端</span>
      </header>

      <div className="flex flex-1">
        <aside className="w-60 bg-white border-r border-neutral-200 p-4 hidden lg:block">
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

        <main className="flex-1 bg-neutral-50 p-6">{children}</main>
      </div>
    </div>
  );
}
