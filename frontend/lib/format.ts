/**
 * 时间格式化工具 — 15min 粒度辅助
 */

/** 将 ISO 时间格式化为 HH:mm 显示 */
export function formatTime(iso: string): string {
  const d = new Date(iso);
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  return `${h}:${m}`;
}

/** 将 ISO 日期格式化为 MM-DD 显示 */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${m}-${day}`;
}

/** 获取今日日期 YYYY-MM-DD */
export function todayStr(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** 校验时间是否 15min 对齐 */
export function is15MinAligned(date: Date): boolean {
  return date.getMinutes() % 15 === 0;
}

/** 周几中文标签 */
export const WEEKDAY_LABELS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
