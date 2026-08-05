/**
 * 医生患者列表
 * docs/pages.md (doctor)/patients
 */
export default function DoctorPatientsPage() {
  return (
    <div>
      <h1 className="text-xl font-bold text-neutral-900 mb-4">我的患者</h1>
      <div className="rounded-lg bg-white border border-neutral-200 p-6 text-center">
        <p className="text-neutral-500 text-sm">暂无患者</p>
      </div>
    </div>
  );
}
