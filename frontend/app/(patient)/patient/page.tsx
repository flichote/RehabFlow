/**
 * 患者首页 — 今日课程概览 + 今日提醒
 * docs/pages.md (patient)
 */
export default function PatientHomePage() {
  return (
    <div>
      <h1 className="text-xl font-bold text-neutral-900 mb-4">今日课程</h1>
      <div className="rounded-lg bg-white border border-neutral-200 p-6 text-center">
        <p className="text-neutral-500 text-sm">暂无今日课程</p>
      </div>
    </div>
  );
}
