/**
 * Chart token-to-hex mapping
 * recharts SVG props (fill, stroke, dot) require hex strings, not Tailwind classes.
 * All hex values here are sourced from design-system.md tokens — single source of truth.
 */

export const CHART_COLORS = {
  // 课程类型三色 (design-system §2.2)
  pt: "#3B82F6",
  ot: "#22C55E",
  st: "#F97316",
  // 品牌主色 (design-system §2.1)
  primary: "#6366F1",
  // 中性色 (design-system §2.4)
  neutral200: "#E2E8F0",
  neutral400: "#94A3B8",
  neutral500: "#64748B",
} as const;

/** recharts Tooltip/contentStyle 共用样式 */
export const CHART_TOOLTIP_STYLE = {
  borderRadius: 8,
  border: `1px solid ${CHART_COLORS.neutral200}`,
  fontSize: 13,
} as const;

/** recharts Legend 共用样式 */
export const CHART_LEGEND_STYLE = {
  fontSize: 12,
  color: CHART_COLORS.neutral500,
} as const;

/** 轴 tick 样式 */
export const CHART_TICK_STYLE = {
  fontSize: 12,
  fill: CHART_COLORS.neutral500,
} as const;

/** 分布图颜色映射 */
export const DISTRIBUTION_COLORS: Record<string, string> = {
  pt: CHART_COLORS.pt,
  ot: CHART_COLORS.ot,
  st: CHART_COLORS.st,
  neutral: CHART_COLORS.neutral400,
};
